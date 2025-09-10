originpath = pwd;  % Store current folder (tool location)
seldatapath = uigetdir(originpath);  % Select folder containing log files
cd(seldatapath);  % Navigate to selected folder

files = dir('*.mat');  % Get all .mat files in the folder
N = length(files);     % Total number of files

%% Create kpiTable
kpiTable = utils.createKpiTableFromJson(pathToKpiSchema, N);

%% Post-Processing Constants
cutoffFreq = 10;  % Frequency used for filtering acceleration
timeSampleOffset = 3000 / cutoffFreq;  % Offset in ms

% Load calibration thresholds
SteeringWheelAngle_Th = cfg.Calibratables.SteeringWheelAngle_Th;
AEB_SteeringAngleRate_Override = cfg.Calibratables.AEB_SteeringAngleRate_Override;
PedalPosProIncrease_Th = cfg.Calibratables.PedalPosProIncrease_Th;
PedalPosProIncrease_Th{2, :} = PedalPosProIncrease_Th{2, :} * 100;
YawrateSuspension_Th = cfg.Calibratables.YawrateSuspension_Th;
LateralAcceleration_th = cfg.Calibratables.LateralAcceleration_th;

%% Load and Process each AEB Data
for i = 1:N
    filename = files(i).name;
    load(filename);     % Loads signalMatChunk

    % --- Preprocess signals ---
    signalMatChunk.VehicleSpeed = round(signalMatChunk.VehicleSpeed * 3.6, 1);
    signalMatChunk.A2_Filt = utils.accelFilter(signalMatChunk.Time, signalMatChunk.A2, cutoffFreq);
    signalMatChunk.A1_Filt = utils.accelFilter(signalMatChunk.Time, signalMatChunk.A1, cutoffFreq);

    %% Common pre-logging
    kpiTable.label(i) = filename;
    kpiTable.condTrue(i) = true;
    kpiTable.logTime(i) = round(seconds(signalMatChunk.Time(1)), 2);

    % --- Locate intervention start (M0) ---
    [AEB_Req, ~, ~] = utils.findFirstLastIndicesAdvanced( ...
        signalMatChunk.DADCAxLmtIT4, -6, 'less', 0.1);

    if isempty(AEB_Req)
        % No intervention detected -> skip this file
        continue;
    end

    M0 = signalMatChunk.Time(AEB_Req(1));
    kpiTable.m0IntvStart(i) = round(seconds(M0), 2);

    % Take vehicle speed at first AEB trigger
    vehSpd = signalMatChunk.VehicleSpeed(AEB_Req(1));
    kpiTable.vehSpd(i) = vehSpd;


    % --- Thresholds interpolation ---
    steerAngTh      = utils.interpolateThresholdClamped(SteeringWheelAngle_Th, vehSpd);
    steerAngRateTh  = utils.interpolateThresholdClamped(AEB_SteeringAngleRate_Override, vehSpd);
    pedalPosIncTh   = utils.interpolateThresholdClamped(PedalPosProIncrease_Th, vehSpd);
    yawRateSuspTh   = utils.interpolateThresholdClamped(YawrateSuspension_Th, vehSpd);
    latAccelTh      = utils.interpolateThresholdClamped(LateralAcceleration_th, vehSpd);

    % --- KPI calculations ---
    kpiTable = kpiThrottle(kpiTable, i, signalMatChunk, AEB_Req, pedalPosIncTh);
    kpiTable = kpiSteeringWheel(kpiTable, i, signalMatChunk, AEB_Req, steerAngTh, steerAngRateTh, timeSampleOffset);
    kpiTable = kpiLatAccel(kpiTable, i, signalMatChunk, AEB_Req, latAccelTh, timeSampleOffset);
    kpiTable = kpiYawRate(kpiTable, i, signalMatChunk, AEB_Req, yawRateSuspTh, timeSampleOffset);
    kpiTable = kpiBrakeMode(kpiTable, i, signalMatChunk, AEB_Req, cutoffFreq);
    kpiTable = kpiLatency(kpiTable, i, signalMatChunk, AEB_Req, cutoffFreq);

end


%% Export Data to CSV
RowsToDelete = ismissing(kpiTable.label);
kpiTable(RowsToDelete, :) = [];
kpiTable = sortrows(kpiTable, 'vehSpd');
writetable(kpiTable, 'data_v01.csv');
