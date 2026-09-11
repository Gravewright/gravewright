"""Original algorithm regression cases, adapted to Django unittest."""

from django.test import SimpleTestCase

from gravewright.realtime.gm_guided_prefetch import GmGuidedPrefetchBroker, sigmoid


class OriginalAlgorithmTests(SimpleTestCase):
    def test_gm_hint_requires_dwell_and_nearby_player(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(clock_ms=lambda: now)
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
        )
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
            )
            == ()
        )
        now += 2000
        hints = broker.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
        )
        assert len(hints) == 1
        assert hints[0].player_id == "player"
        assert hints[0].distance_chunks == 1
        assert hints[0].dwell_ms == 2000

    def test_gm_hint_is_not_disclosed_to_distant_or_stale_players(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(clock_ms=lambda: now, viewport_ttl_ms=3000)
        broker.record_player_viewport(
            user_id="far", scene_id="scene", cx0=0, cy0=0, cx1=1, cy1=1
        )
        broker.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=8, cy0=8, cx1=9, cy1=9
        )
        now += 4000
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=8, cy0=8, cx1=9, cy1=9
            )
            == ()
        )

    def test_gm_hint_repeat_is_rate_limited(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(clock_ms=lambda: now)
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
        )
        broker.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
        )
        now += 2000
        assert (
            len(
                broker.observe_gm_viewport(
                    gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
                )
            )
            == 1
        )
        now += 1000
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
            )
            == ()
        )

    def test_interaction_and_deceleration_raise_explainable_score(self) -> None:
        now = 1000
        quiet = GmGuidedPrefetchBroker(clock_ms=lambda: now)
        intent = GmGuidedPrefetchBroker(clock_ms=lambda: now)
        for broker in (quiet, intent):
            broker.record_player_viewport(
                user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
            )
            broker.observe_gm_viewport(
                gm_user_id="gm",
                scene_id="scene",
                cx0=6,
                cy0=4,
                cx1=6,
                cy1=5,
                camera_speed=2.0,
            )
        now += 2000
        quiet_hint = quiet.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
        )[0]
        intent_hint = intent.observe_gm_viewport(
            gm_user_id="gm",
            scene_id="scene",
            cx0=6,
            cy0=4,
            cx1=6,
            cy1=5,
            camera_speed=0.0,
            camera_deceleration=2.0,
            interaction_count=2,
        )[0]
        assert intent_hint.score > quiet_hint.score
        assert intent_hint.interaction_count == 2
        assert intent_hint.camera_deceleration == 2.0

    def test_fast_camera_motion_suppresses_hint(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(clock_ms=lambda: now)
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
        )
        broker.observe_gm_viewport(
            gm_user_id="gm",
            scene_id="scene",
            cx0=6,
            cy0=4,
            cx1=6,
            cy1=5,
            camera_speed=20.0,
        )
        now += 2000
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm",
                scene_id="scene",
                cx0=6,
                cy0=4,
                cx1=6,
                cy1=5,
                camera_speed=20.0,
            )
            == ()
        )

    def test_sigmoid_midpoint_and_saturation_are_interpretable(self) -> None:
        self.assertAlmostEqual(sigmoid(4000), 0.5)
        assert sigmoid(0) < 0.05
        assert sigmoid(10000) > 0.99

    def test_derivative_is_clamped_and_cannot_trigger_without_confidence(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(
            policy="sigmoid_derivative", min_dwell_ms=0, clock_ms=lambda: now
        )
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
        )
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
            )
            == ()
        )
        now += 1
        assert (
            broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
            )
            == ()
        )

    def test_sigmoid_derivative_emits_supported_bounded_telemetry(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(
            policy="sigmoid_derivative", repeat_after_ms=0, clock_ms=lambda: now
        )
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=4, cy0=4, cx1=5, cy1=5
        )
        hints = ()
        for _ in range(10):
            hints = broker.observe_gm_viewport(
                gm_user_id="gm", scene_id="scene", cx0=6, cy0=4, cx1=6, cy1=5
            )
            now += 1000
        assert hints
        hint = hints[0]
        assert hint.policy == "sigmoid_derivative"
        assert 0 <= hint.confidence <= 1
        assert abs(hint.momentum) <= 0.5
        assert 0 <= hint.utility <= 1

    def test_bad_derivative_interval_is_ignored(self) -> None:
        now = 1000
        broker = GmGuidedPrefetchBroker(
            policy="sigmoid_derivative", min_dwell_ms=0, clock_ms=lambda: now
        )
        broker.record_player_viewport(
            user_id="player", scene_id="scene", cx0=0, cy0=0, cx1=1, cy1=1
        )
        broker.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=1, cy0=0, cx1=2, cy1=1
        )
        now += 6000
        broker.observe_gm_viewport(
            gm_user_id="gm", scene_id="scene", cx0=1, cy0=0, cx1=2, cy1=1
        )
        observation = next(iter(broker._observations.values()))
        assert next(iter(observation.player_signals.values())).sampled_at_ms == now
