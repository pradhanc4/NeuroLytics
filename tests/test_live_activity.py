from analytics.live_activity import LiveActivity


def test_live_activity_emits_and_snapshots():
    activity = LiveActivity(max_events=10)
    event = activity.emit(
        "Prediction generated",
        status="RUNNING",
        current_date="2026-10-04",
        stage="STAGE_2",
        prediction={"status": "VALID"},
    )

    snapshot = activity.snapshot()

    assert snapshot["status"] == "VALID"
    assert snapshot["last_sequence"] == event["sequence"]
    assert snapshot["state"]["current_date"] == "2026-10-04"
    assert snapshot["state"]["stage"] == "STAGE_2"
    assert snapshot["state"]["prediction"]["status"] == "VALID"
    assert snapshot["events"][-1]["message"] == "Prediction generated"


def test_live_activity_events_since_returns_only_new_events():
    activity = LiveActivity(max_events=10)
    first = activity.emit("First")
    activity.emit("Second")

    result = activity.events_since(first["sequence"])

    assert [item["message"] for item in result["events"]] == ["Second"]
    assert result["last_sequence"] == 2


def test_live_activity_rejects_invalid_sequence():
    activity = LiveActivity()
    try:
        activity.events_since(-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("expected ValueError")
