from app.engine.rolls.roll_reroll_service import _critical_failure


def test_savage_critical_failure_cannot_be_rerolled():
    assert _critical_failure({"rendered": {"chatCard": {"tone": "critical-failure"}}})


def test_normal_savage_roll_can_reach_reroll_policy():
    assert not _critical_failure({"rendered": {"chatCard": {"tone": "failure"}}})
