# KPI Catalog

This catalog documents the KPI names currently exported by the tool. It is aligned with the feature registry in `src/pipeline/registry.py`, which is now the single place used by the CLI entrypoints and the GUI runner to discover supported features.

## AEB

Event KPIs:
`logTime`, `aebIntvStartTime`, `aebIntvEndTime`, `intvDur`, `isVehStopped`, `aebSuspDur`, `vehSpd`, `steerAngTh`, `steerAngRateTh`, `pedalPosIncTh`, `yawRateSuspTh`, `latAccelTh`, `firstDetDist`, `stableDetDist`, `aebIntvDist`, `aebStopGap`, `pedalPosAtStart`, `pedalPosMax`, `pedalPosInc`, `isPedalPosIncHigh`, `isPedalOnAtStrt`, `absSteerMaxDeg`, `isSteerHigh`, `absSteerRateMaxDeg`, `isSteerAngRateHigh`, `absYawRateMaxDeg`, `isYawRateHigh`, `absLatAccelMax`, `isLatAccelHigh`, `pbDur`, `fbDur`, `isPBOn`, `isFBOn`, `aebSysRespTime`, `aebDeadTime`, `commLatency`, `ImpactRelSpdKph`, `aebAverageAccel`

Cycle KPIs:
`AvailDistPct`, `ROVAvail`, `VALAvail`, `NoDegradation`, `PedalPosProSuppression`, `SteeringWheelAngle`, `SteeringWheelAngleRate`, `YawRate`, `LatAccel`, `LowSpeed`

## FCW

Event KPIs:
`logTime`, `vehSpd`, `brakeJerkStart`, `brakeJerkEnd`, `brakeJerkDur`, `brakeJerkMax`, `brakeAccelMin`, `fcwSensitivityLvl`, `fcwWarningTTC`

Cycle KPIs:
`AvailDistPct`, `ROVAvail`, `VALAvail`, `NoDegradation`, `PedalPosProSuppression`, `SteeringWheelAngle`, `SteeringWheelAngleRate`, `YawRate`, `LatAccel`, `LowSpeed`

## LSAEB

Event KPIs:
`logTime`, `vehSpd`, `lsaebIntvLongDist`, `lsaebIntvLatDist`, `lsaebStopLongDist`, `lsaebStopLatDist`, `lsaebAverageAccel`

Cycle KPIs:
None currently exported.

## LKA

Event KPIs:
`logTime`, `MinDTLEDelta`, `TrigDTLE`, `isWhlTrqHigh`, `TrigRateOfDeparture`, `TrigVehCurv`, `TrigLaneCurv`, `vehSpd`, `UseCase`

Cycle KPIs:
`AvailDistPctLeft`, `AvailDistPctRight`

## Extension Notes

- Add a new feature by creating the segmenter/extractor/visualizer classes, then registering the pipeline once in `src/pipeline/registry.py`.
- Reuse `RuleBasedCycleKpiExtractor` when the feature’s cycle KPIs are distance-weighted masks over signals.
- Keep this document and the registry in sync when KPI names change.
