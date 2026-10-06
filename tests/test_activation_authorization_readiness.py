from analytics.activation_authorization_readiness import *

def test_record_pending():
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    assert r.approval_state==AUTHORIZATION_PENDING

def test_record_valid():
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    assert validate_authorization_record(r)[0]==VALID

def test_empty_rejected():
    import pytest
    with pytest.raises(ValueError):
        build_authorization_record("","","","", "m","v","a","r")

def test_binding_pending():
    class P:
        artifact_identity="art"; model_identity="m"; model_version="v"
        rollout_id="roll"; authorization_id="a"
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    assert validate_activation_plan_binding(r,P())[0]==INVALID

def test_binding_authorized():
    class P:
        artifact_identity="art"; model_identity="m"; model_version="v"
        rollout_id="roll"; authorization_id="a"
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    r=type(r)(r.authorization_id,r.authorized_by,r.purpose,r.scope,
              r.artifact_identity,r.model_identity,r.model_version,r.rollout_id,
              "AUTHORIZED",r.record_identity)
    assert validate_activation_plan_binding(r,P())[0]==VALID

def test_binding_mismatch_is_blocked():
    class P:
        artifact_identity="different"; model_identity="m"; model_version="v"
        rollout_id="roll"; authorization_id="a"
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    assert validate_activation_plan_binding(r,P())[0]==INVALID

def test_record_identity_detects_tampering():
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    tampered=type(r)(r.authorization_id,r.authorized_by,"tampered",r.scope,
                     r.artifact_identity,r.model_identity,r.model_version,r.rollout_id,
                     r.approval_state,r.record_identity)
    status,issues=validate_authorization_record(tampered)
    assert status==INVALID
    assert "INVALID_RECORD_IDENTITY" in issues

def test_record_identity_is_required():
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    bad=type(r)(r.authorization_id,r.authorized_by,r.purpose,r.scope,
                r.artifact_identity,r.model_identity,r.model_version,r.rollout_id,
                r.approval_state,"bad")
    status,issues=validate_authorization_record(bad)
    assert status==INVALID
    assert "INVALID_RECORD_IDENTITY" in issues

def test_pending_authorization_never_ready():
    class P:
        artifact_identity="art"; model_identity="m"; model_version="v"
        rollout_id="roll"; authorization_id="a"
    r=build_authorization_record("a","eng","release","production","m","v","art","roll")
    status,issues=validate_activation_plan_binding(r,P())
    assert status==INVALID
    assert "EXPLICIT_AUTHORIZATION_PENDING" in issues
