from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from threading import Lock

from app.config import config


POLICIES = {"simple", "exponential", "sigmoid", "sigmoid_derivative", "utility_per_byte"}


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sigmoid(dwell_ms: int, *, k: float = 0.9, midpoint_ms: int = 4_000) -> float:
    seconds_from_midpoint = (dwell_ms - midpoint_ms) / 1_000
    exponent = clamp(-k * seconds_from_midpoint, -60.0, 60.0)
    return 1.0 / (1.0 + math.exp(exponent))


@dataclass(frozen=True)
class PlayerViewport:
    user_id: str
    scene_id: str
    cx0: int
    cy0: int
    cx1: int
    cy1: int
    observed_at_ms: int


@dataclass(frozen=True)
class GmPrefetchHint:
    player_id: str
    scene_id: str
    cx0: int
    cy0: int
    cx1: int
    cy1: int
    score: float
    confidence: float
    momentum: float
    utility: float
    policy: str
    dwell_ms: int
    distance_chunks: int
    expires_at_ms: int
    revisit_count: int
    interaction_count: int
    camera_speed: float
    camera_deceleration: float
    recency_score: float
    state: str = "candidate"


@dataclass
class _PlayerSignal:
    confidence_ema: float = 0.0
    previous_confidence_ema: float = 0.0
    distance_ema: float | None = None
    previous_distance_ema: float | None = None
    sampled_at_ms: int | None = None
    active: bool = False


@dataclass
class _Observation:
    first_seen_at_ms: int
    last_seen_at_ms: int
    last_emitted_at_by_player: dict[str, int] = field(default_factory=dict)
    player_signals: dict[str, _PlayerSignal] = field(default_factory=dict)
    revisit_count: int = 0
    interaction_count: int = 0
    camera_speed: float = 0.0
    camera_velocity_ema: float = 0.0
    camera_deceleration: float = 0.0


class GmGuidedPrefetchBroker:
    """Bounded, per-recipient predictor. It emits coordinates, never assets."""

    def __init__(
        self,
        *,
        policy: str = "simple",
        max_distance_chunks: int = 1,
        dwell_tau_ms: int = 5_000,
        min_dwell_ms: int = 1_500,
        score_threshold: float = 0.12,
        enter_threshold: float = 0.65,
        keep_threshold: float = 0.50,
        sigmoid_k: float = 0.9,
        sigmoid_midpoint_ms: int = 4_000,
        confidence_alpha: float = 0.85,
        momentum_beta: float = 0.15,
        ewma_rho: float = 0.35,
        max_momentum_per_second: float = 0.50,
        max_derivative_interval_ms: int = 5_000,
        viewport_ttl_ms: int = 15_000,
        hint_ttl_ms: int = 60_000,
        repeat_after_ms: int = 15_000,
        recency_tau_ms: int = 30_000,
        clock_ms=None,
    ) -> None:
        if policy not in POLICIES:
            raise ValueError(f"Unsupported GM hint policy: {policy}")
        self.policy = policy
        self.max_distance_chunks = max_distance_chunks
        self.dwell_tau_ms = dwell_tau_ms
        self.min_dwell_ms = min_dwell_ms
        self.score_threshold = score_threshold
        self.enter_threshold = enter_threshold
        self.keep_threshold = keep_threshold
        self.sigmoid_k = sigmoid_k
        self.sigmoid_midpoint_ms = sigmoid_midpoint_ms
        self.confidence_alpha = confidence_alpha
        self.momentum_beta = momentum_beta
        self.ewma_rho = ewma_rho
        self.max_momentum_per_second = max_momentum_per_second
        self.max_derivative_interval_ms = max_derivative_interval_ms
        self.viewport_ttl_ms = viewport_ttl_ms
        self.hint_ttl_ms = hint_ttl_ms
        self.repeat_after_ms = repeat_after_ms
        self.recency_tau_ms = recency_tau_ms
        self._last_region_by_gm: dict[tuple[str, str], tuple[int, int, int, int]] = {}
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self._players: dict[tuple[str, str], PlayerViewport] = {}
        self._observations: dict[tuple[str, str, int, int, int, int], _Observation] = {}
        self._lock = Lock()

    def record_player_viewport(self, *, user_id: str, scene_id: str, cx0: int, cy0: int, cx1: int, cy1: int) -> None:
        now_ms = self._clock_ms()
        with self._lock:
            self._players[(scene_id, user_id)] = PlayerViewport(user_id, scene_id, cx0, cy0, cx1, cy1, now_ms)
            self._prune(now_ms)

    def observe_gm_viewport(
        self, *, gm_user_id: str, scene_id: str, cx0: int, cy0: int, cx1: int, cy1: int,
        camera_speed: float = 0.0, camera_deceleration: float = 0.0, interaction_count: int = 0,
    ) -> tuple[GmPrefetchHint, ...]:
        now_ms = self._clock_ms()
        key = (gm_user_id, scene_id, cx0, cy0, cx1, cy1)
        with self._lock:
            self._prune(now_ms)
            observation = self._observations.get(key)
            region = (cx0, cy0, cx1, cy1)
            gm_key = (gm_user_id, scene_id)
            previous_region = self._last_region_by_gm.get(gm_key)
            if observation is None:
                observation = _Observation(now_ms, now_ms)
                self._observations[key] = observation
            elif previous_region is not None and previous_region != region:
                observation.revisit_count += 1
                observation.first_seen_at_ms = now_ms
            self._last_region_by_gm[gm_key] = region
            previous_seen_at = observation.last_seen_at_ms
            observation.last_seen_at_ms = now_ms
            speed = max(0.0, float(camera_speed))
            observation.camera_deceleration = max(0.0, float(camera_deceleration), observation.camera_speed - speed)
            observation.camera_speed = speed
            observation.camera_velocity_ema = self._ewma(speed, observation.camera_velocity_ema)
            observation.interaction_count = min(3, observation.interaction_count + max(0, int(interaction_count)))
            dwell_ms = now_ms - observation.first_seen_at_ms
            if dwell_ms < self.min_dwell_ms:
                return ()

            dwell_confidence = self._dwell_confidence(dwell_ms)
            recency_score = math.exp(-(now_ms - previous_seen_at) / self.recency_tau_ms)
            hints: list[GmPrefetchHint] = []
            for (player_scene_id, player_id), viewport in self._players.items():
                if player_scene_id != scene_id or player_id == gm_user_id:
                    continue
                distance = self._rect_distance(viewport, cx0, cy0, cx1, cy1)
                if distance > self.max_distance_chunks:
                    continue
                signal = observation.player_signals.setdefault(player_id, _PlayerSignal())
                distance_score = 1.0 / (1.0 + distance) if self.policy == "simple" else 1.0
                revisit_boost = min(1.25, 1.0 + 0.10 * observation.revisit_count)
                interaction_boost = 1.0 + 0.08 * observation.interaction_count
                deceleration_boost = 1.0 + 0.08 * min(observation.camera_deceleration, 2.0)
                motion_gate = 1.0 / (1.0 + observation.camera_velocity_ema)
                raw_confidence = clamp(
                    dwell_confidence * recency_score * distance_score * revisit_boost * interaction_boost * deceleration_boost * motion_gate,
                    0.0, 1.0,
                )
                previous_ema = signal.confidence_ema
                signal.previous_confidence_ema = previous_ema
                signal.confidence_ema = raw_confidence if self.policy == "simple" else self._ewma(raw_confidence, previous_ema)
                signal.previous_distance_ema = signal.distance_ema
                signal.distance_ema = float(distance) if signal.distance_ema is None else self._ewma(float(distance), signal.distance_ema)
                momentum = self._momentum(signal, now_ms)
                signal.sampled_at_ms = now_ms
                score = self._intent_score(signal.confidence_ema, momentum)
                threshold = self._threshold(signal)
                # Momentum may anticipate supported evidence, but can never trigger alone.
                foundation = signal.confidence_ema >= min(self.keep_threshold, threshold * self.confidence_alpha)
                if score < threshold or not foundation:
                    if score < self.keep_threshold:
                        signal.active = False
                    continue
                signal.active = True
                last_emitted = observation.last_emitted_at_by_player.get(player_id)
                if last_emitted is not None and now_ms - last_emitted < self.repeat_after_ms:
                    continue
                observation.last_emitted_at_by_player[player_id] = now_ms
                hints.append(GmPrefetchHint(
                    player_id=player_id, scene_id=scene_id, cx0=cx0, cy0=cy0, cx1=cx1, cy1=cy1,
                    score=score, confidence=signal.confidence_ema, momentum=momentum,
                    utility=score, policy=self.policy, dwell_ms=dwell_ms, distance_chunks=distance,
                    expires_at_ms=now_ms + self.hint_ttl_ms, revisit_count=observation.revisit_count,
                    interaction_count=observation.interaction_count, camera_speed=observation.camera_velocity_ema,
                    camera_deceleration=observation.camera_deceleration, recency_score=recency_score,
                ))
            return tuple(hints)

    def _dwell_confidence(self, dwell_ms: int) -> float:
        if self.policy == "simple":
            return 1.0 - math.exp(-dwell_ms / self.dwell_tau_ms)
        if self.policy == "exponential":
            return 1.0 - math.exp(-dwell_ms / self.dwell_tau_ms)
        return sigmoid(dwell_ms, k=self.sigmoid_k, midpoint_ms=self.sigmoid_midpoint_ms)

    def _intent_score(self, confidence: float, momentum: float) -> float:
        if self.policy in {"sigmoid_derivative", "utility_per_byte"}:
            normalized_momentum = max(0.0, momentum) / self.max_momentum_per_second
            return clamp(self.confidence_alpha * confidence + self.momentum_beta * normalized_momentum, 0.0, 1.0)
        return confidence

    def _threshold(self, signal: _PlayerSignal) -> float:
        if self.policy in {"simple", "exponential"}:
            return self.score_threshold
        return self.keep_threshold if signal.active else self.enter_threshold

    def _momentum(self, signal: _PlayerSignal, now_ms: int) -> float:
        if signal.sampled_at_ms is None:
            return 0.0
        dt_ms = now_ms - signal.sampled_at_ms
        if dt_ms <= 0 or dt_ms > self.max_derivative_interval_ms:
            return 0.0
        derivative = (signal.confidence_ema - signal.previous_confidence_ema) / (dt_ms / 1_000)
        return clamp(derivative, -self.max_momentum_per_second, self.max_momentum_per_second)

    def _ewma(self, value: float, previous: float) -> float:
        return self.ewma_rho * value + (1.0 - self.ewma_rho) * previous

    @staticmethod
    def _rect_distance(viewport: PlayerViewport, cx0: int, cy0: int, cx1: int, cy1: int) -> int:
        dx = max(viewport.cx0 - cx1, cx0 - viewport.cx1, 0)
        dy = max(viewport.cy0 - cy1, cy0 - viewport.cy1, 0)
        return max(dx, dy)

    def _prune(self, now_ms: int) -> None:
        self._players = {key: value for key, value in self._players.items() if now_ms - value.observed_at_ms <= self.viewport_ttl_ms}
        observation_ttl = max(self.hint_ttl_ms, self.repeat_after_ms)
        self._observations = {key: value for key, value in self._observations.items() if now_ms - value.last_seen_at_ms <= observation_ttl}


gm_guided_prefetch_broker = GmGuidedPrefetchBroker(
    policy=config.gm_hint_policy,
    max_distance_chunks=config.gm_hint_max_distance_chunks,
    viewport_ttl_ms=120_000,
    hint_ttl_ms=config.gm_hint_ttl_seconds * 1000,
)
