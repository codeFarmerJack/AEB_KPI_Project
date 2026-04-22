from dataclasses import dataclass

from src.pipeline.as_lat.lka.lka_pipeline import LkaPipeline
from src.pipeline.as_long.aeb.aeb_pipeline import AebPipeline
from src.pipeline.as_long.fcw.fcw_pipeline import FcwPipeline
from src.pipeline.as_long.lsaeb.lsaeb_pipeline import LsaebPipeline


@dataclass(frozen=True)
class FeatureCatalogEntry:
    key: str
    domain: str
    config_name: str
    pipeline_cls: type
    summary: str
    event_kpis: tuple[str, ...]
    cycle_kpis: tuple[str, ...] = ()


LONG_FEATURES = (
    FeatureCatalogEntry(
        key="AEB",
        domain="as_long",
        config_name="config_as_long.json",
        pipeline_cls=AebPipeline,
        summary="Automatic Emergency Braking event extraction, KPI export, and dashboards.",
        event_kpis=(
            "logTime",
            "aebIntvStartTime",
            "aebIntvEndTime",
            "intvDur",
            "isVehStopped",
            "aebSuspDur",
            "vehSpd",
            "steerAngTh",
            "steerAngRateTh",
            "pedalPosIncTh",
            "yawRateSuspTh",
            "latAccelTh",
            "firstDetDist",
            "stableDetDist",
            "aebIntvDist",
            "aebStopGap",
            "pedalPosAtStart",
            "pedalPosMax",
            "pedalPosInc",
            "isPedalPosIncHigh",
            "isPedalOnAtStrt",
            "absSteerMaxDeg",
            "isSteerHigh",
            "absSteerRateMaxDeg",
            "isSteerAngRateHigh",
            "absYawRateMaxDeg",
            "isYawRateHigh",
            "absLatAccelMax",
            "isLatAccelHigh",
            "pbDur",
            "fbDur",
            "isPBOn",
            "isFBOn",
            "aebSysRespTime",
            "aebDeadTime",
            "commLatency",
            "ImpactRelSpdKph",
            "aebAverageAccel",
        ),
        cycle_kpis=(
            "AvailDistPct",
            "ROVAvail",
            "VALAvail",
            "NoDegradation",
            "PedalPosProSuppression",
            "SteeringWheelAngle",
            "SteeringWheelAngleRate",
            "YawRate",
            "LatAccel",
            "LowSpeed",
        ),
    ),
    FeatureCatalogEntry(
        key="FCW",
        domain="as_long",
        config_name="config_as_long.json",
        pipeline_cls=FcwPipeline,
        summary="Forward Collision Warning event extraction, KPI export, and dashboards.",
        event_kpis=(
            "logTime",
            "vehSpd",
            "brakeJerkStart",
            "brakeJerkEnd",
            "brakeJerkDur",
            "brakeJerkMax",
            "brakeAccelMin",
            "fcwSensitivityLvl",
            "fcwWarningTTC",
        ),
        cycle_kpis=(
            "AvailDistPct",
            "ROVAvail",
            "VALAvail",
            "NoDegradation",
            "PedalPosProSuppression",
            "SteeringWheelAngle",
            "SteeringWheelAngleRate",
            "YawRate",
            "LatAccel",
            "LowSpeed",
        ),
    ),
    FeatureCatalogEntry(
        key="LSAEB",
        domain="as_long",
        config_name="config_as_long.json",
        pipeline_cls=LsaebPipeline,
        summary="Low-speed AEB event extraction and KPI export.",
        event_kpis=(
            "logTime",
            "vehSpd",
            "lsaebIntvLongDist",
            "lsaebIntvLatDist",
            "lsaebStopLongDist",
            "lsaebStopLatDist",
            "lsaebAverageAccel",
        ),
    ),
)

LAT_FEATURES = (
    FeatureCatalogEntry(
        key="LKA",
        domain="as_lat",
        config_name="config_as_lat.json",
        pipeline_cls=LkaPipeline,
        summary="Lane Keep Assist event extraction, KPI export, and cycle availability dashboards.",
        event_kpis=(
            "logTime",
            "MinDTLEDelta",
            "TrigDTLE",
            "isWhlTrqHigh",
            "TrigRateOfDeparture",
            "TrigVehCurv",
            "TrigLaneCurv",
            "vehSpd",
            "UseCase",
        ),
        cycle_kpis=(
            "AvailDistPctLeft",
            "AvailDistPctRight",
        ),
    ),
)

ALL_FEATURES = {entry.key: entry for entry in (*LONG_FEATURES, *LAT_FEATURES)}


def get_domain_catalog(domain: str):
    normalized = str(domain).strip().lower()
    if normalized == "as_long":
        return LONG_FEATURES
    if normalized == "as_lat":
        return LAT_FEATURES
    raise ValueError(f"Unsupported domain '{domain}'")


def get_feature_map(domain: str):
    return {entry.key: entry.pipeline_cls for entry in get_domain_catalog(domain)}


def get_config_name(domain: str):
    catalog = get_domain_catalog(domain)
    if not catalog:
        raise ValueError(f"No features configured for domain '{domain}'")
    return catalog[0].config_name


def iter_catalog():
    return (*LONG_FEATURES, *LAT_FEATURES)
