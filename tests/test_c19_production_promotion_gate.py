from analytics.production_promotion_gate import run_gate


def valid17():
    return {"status": "VALID", "temporal_safe": True}


def valid18():
    return {
        "status": "VALID",
        "temporal_order_valid": True,
        "artifact_integrity_valid": True,
        "stage1_reproducible": True,
        "stage2_reproducible": True,
    }


def test_all_integrity_gates_pass_but_auto_promotion_stays_disabled():
    result = run_gate(valid17(), valid18(), True, True)
    assert result.status == "VALID"
    assert result.promotion_allowed is False
    assert all(result.gates.values())


def test_failed_regression_invalidates_gate():
    result = run_gate(valid17(), valid18(), False, True)
    assert result.status == "INVALID"
    assert result.promotion_allowed is False


def test_missing_production_path_invalidates_gate():
    result = run_gate(valid17(), valid18(), True, False)
    assert result.status == "INVALID"
    assert result.promotion_allowed is False
