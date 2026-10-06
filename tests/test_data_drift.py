from datetime import date, timedelta
import pytest
from features.feature_artifact import FeatureArtifact
from features.feature_schema import FeatureSchema
from features.feature_versioning import FeatureVersionIdentity
from analytics.data_drift import (
    DATA_DRIFT_VERSION, DEFAULT_BINS, DataDriftRule,
    build_data_drift_report, data_drift_observations, data_drift_summary,
    validate_data_drift_report,
)

def make_source(first=(1.0,1.1,0.9,1.0), second=(1.0,1.1,0.9,1.0), name="f1"):
    values=list(first)+list(second)
    schema=FeatureSchema(name,"50-test","lag","test","col1",1,1,"test","result_date < target_date","float")
    identity=FeatureVersionIdentity("50-test","feature-test","sha256","test")
    result=[]
    for i,value in enumerate(values):
        day=i if i<len(first) else 14+i-len(first)
        result.append(FeatureArtifact(date(2026,1,1)+timedelta(days=day),"50-test",(name,),{name:value},(schema,),identity,"VALID","CLEAN"))
    return tuple(result)

def test_default_report_valid_and_deterministic():
    source=make_source()
    first=build_data_drift_report(source); second=build_data_drift_report(source)
    assert first.version==DATA_DRIFT_VERSION and first.bin_count==DEFAULT_BINS
    assert first.report_identity==second.report_identity
    assert validate_data_drift_report(first).is_valid

def test_stable_distribution_not_drifted():
    report=build_data_drift_report(make_source())
    assert report.drifted is False and report.drifted_features==()

def test_shifted_distribution_detected():
    report=build_data_drift_report(make_source(second=(9.0,9.1,8.9,9.0)))
    assert report.drifted is True and report.drifted_features==("f1",)

def test_custom_threshold_changes_detection():
    report=build_data_drift_report(make_source(second=(9.0,9.1,8.9,9.0)),rules=(DataDriftRule("f1",100.0),))
    assert report.drifted is False

def test_accessor_and_summary():
    report=build_data_drift_report(make_source(),rules=(DataDriftRule("f1"),))
    assert len(data_drift_observations(report,"f1"))==1
    assert data_drift_summary(report)["status"]=="VALID"

def test_unknown_feature_rejected():
    with pytest.raises(ValueError): build_data_drift_report(make_source(),rules=(DataDriftRule("missing"),))

def test_duplicate_rules_rejected():
    with pytest.raises(ValueError): build_data_drift_report(make_source(),rules=(DataDriftRule("f1"),DataDriftRule("f1")))

def test_invalid_threshold_rejected():
    with pytest.raises(ValueError): build_data_drift_report(make_source(),rules=(DataDriftRule("f1",0.0),))

def test_invalid_period_rejected():
    with pytest.raises(ValueError): build_data_drift_report(make_source(),period_days=0)

def test_invalid_bins_rejected():
    with pytest.raises(ValueError): build_data_drift_report(make_source(),bin_count=1)

def test_requires_two_periods():
    with pytest.raises(ValueError): build_data_drift_report(make_source(first=(1.0,1.1,0.9,1.0),second=()))

def test_duplicate_dates_rejected():
    source=list(make_source())
    x=source[1]
    source[1]=FeatureArtifact(source[0].target_date,x.feature_version,x.feature_names,x.feature_values,x.schemas,x.version_identity,"VALID","CLEAN")
    with pytest.raises(ValueError): build_data_drift_report(source)

def test_mismatched_version_rejected():
    source=list(make_source()); x=source[1]
    source[1]=FeatureArtifact(x.target_date,"other",x.feature_names,x.feature_values,x.schemas,x.version_identity,"VALID","CLEAN")
    with pytest.raises(ValueError): build_data_drift_report(source)

def test_mismatched_feature_names_rejected():
    source=list(make_source()); x=source[1]
    schema=FeatureSchema("other","50-test","lag","test","col1",1,1,"other","result_date < target_date","float")
    source[1]=FeatureArtifact(x.target_date,"50-test",("other",),{"other":1.0},(schema,),x.version_identity,"VALID","CLEAN")
    with pytest.raises(ValueError): build_data_drift_report(source)

def test_invalid_artifact_rejected():
    source=list(make_source()); x=source[0]
    source[0]=FeatureArtifact(x.target_date,x.feature_version,x.feature_names,x.feature_values,x.schemas,x.version_identity,"INVALID","CLEAN")
    with pytest.raises(ValueError): build_data_drift_report(source)

def test_non_numeric_selected_values_rejected():
    source=list(make_source()); x=source[-1]
    source[-1]=FeatureArtifact(x.target_date,x.feature_version,x.feature_names,{"f1":"bad"},x.schemas,x.version_identity,"VALID","CLEAN")
    with pytest.raises(ValueError): build_data_drift_report(source)

def test_none_values_are_excluded_from_distribution():
    source=list(make_source()); x=source[-1]
    source[-1]=FeatureArtifact(x.target_date,x.feature_version,x.feature_names,{"f1":None},x.schemas,x.version_identity,"VALID","CLEAN")
    report=build_data_drift_report(source)
    assert data_drift_observations(report,"f1")[0].comparison_count==3

def test_zero_values_supported():
    report=build_data_drift_report(make_source(first=(0.0,0.0,0.0,0.0),second=(0.0,0.0,0.0,0.0)))
    assert validate_data_drift_report(report).is_valid

def test_multiple_features_supported():
    base=make_source()
    schema=FeatureSchema("f2","50-test","lag","test","col2",1,1,"second","result_date < target_date","float")
    source=tuple(FeatureArtifact(x.target_date,x.feature_version,("f1","f2"),{"f1":x.feature_values["f1"],"f2":x.feature_values["f1"]*2},(x.schemas[0],schema),x.version_identity,"VALID","CLEAN") for x in base)
    report=build_data_drift_report(source)
    assert len(report.rules)==2 and report.drifted is False

def test_identity_changes_with_configuration():
    source=make_source(second=(9.0,9.1,8.9,9.0))
    a=build_data_drift_report(source,rules=(DataDriftRule("f1",0.2),))
    b=build_data_drift_report(source,rules=(DataDriftRule("f1",0.3),))
    c=build_data_drift_report(source,bin_count=5)
    assert a.report_identity!=b.report_identity and a.report_identity!=c.report_identity

def test_multiple_comparison_periods():
    schema=FeatureSchema("f1","50-test","lag","test","col1",1,1,"test","result_date < target_date","float")
    identity=FeatureVersionIdentity("50-test","feature-test","sha256","test")
    values=(1.0,1.1,0.9,1.0,1.0,1.1,0.9,1.0,9.0,9.1,8.9,9.0)
    source=tuple(FeatureArtifact(date(2026,1,1)+timedelta(days=i),"50-test",("f1",),{"f1":v},(schema,),identity,"VALID","CLEAN") for i,v in enumerate(values))
    report=build_data_drift_report(source,period_days=4)
    assert len(report.observations)==2 and report.drifted is True

def test_validation_bad_identity():
    report=build_data_drift_report(make_source())
    broken=report.__class__(report.version,report.feature_version,report.source_artifact_count,report.source_feature_names,report.period_days,report.rules,report.bin_count,report.observations,report.drifted_features,report.drifted_periods,report.drifted,"wrong")
    result=validate_data_drift_report(broken)
    assert result.status=="INVALID" and "INVALID_REPORT_IDENTITY" in result.issues

def test_validation_drift_flag_mismatch():
    report=build_data_drift_report(make_source())
    broken=report.__class__(report.version,report.feature_version,report.source_artifact_count,report.source_feature_names,report.period_days,report.rules,report.bin_count,report.observations,report.drifted_features,report.drifted_periods,True,report.report_identity)
    result=validate_data_drift_report(broken)
    assert result.status=="INVALID" and "OVERALL_DRIFT_MISMATCH" in result.issues

def test_source_type_must_be_artifacts():
    with pytest.raises(TypeError): build_data_drift_report([object(),object()])
