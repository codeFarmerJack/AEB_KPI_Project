

originpath = pwd;  % Store current folder (tool location)
seldatapath = uigetdir(originpath);  % Select folder containing log files
cd(seldatapath);  % Navigate to selected folder

files = dir('*.mat');  % Get all .mat files in the folder
N = length(files);     % Total number of files

%% Create ExportData Table
% Define initial variable
var_name = {'label'};
var_type = {'string'};
sz = [N, 1];

% Define additional variables and their types
additional_vars = {
    'logTime', 'double';
    'vehSpd', 'double';
    'm0IntvStart', 'double';
    'm1IntvSysResp', 'double';
    'm1DeadTime', 'double';
    'm2IntvEnd', 'double';
    'intvDur', 'double';
    'vehStopCheck', 'logical';
    'partialBraking', 'logical';
    'fullBraking', 'logical';
    'pbDur', 'double';
    'fbDur', 'double';
    'pedalStart', 'double';
    'isPedalOnAtStrt', 'double';
    'pedalMax', 'double';
    'pedalInc', 'double';
    'pedalPosIncTh', 'double';
    'isPedalHigh', 'logical';
    'steerMax', 'double';
    'absSteerMaxDeg', 'double';
    'steerAngTh', 'double';
    'isSteerHigh', 'logical';
    'absSteerRateMaxDeg', 'double';
    'steerAngRateTh', 'double';
    'isSteerAngRateHigh', 'logical';
    'latAccelMax', 'double';
    'absLatAccelMax', 'double';
    'latAccelTh', 'double';
    'isLatAccelHigh', 'logical';
    'yawRateMax', 'double';
    'yawRateSuspTh', 'double';
    'absYawRateMaxDeg', 'double';
    'isYawRateHigh', 'logical';
    'longGap', 'double';
    'condTrue', 'logical'
};

% Add metadata for each variable
for iVar = 1:size(additional_vars, 1)
    [var_name, var_type, sz] = utils.addVariableMetadata(var_name, var_type, sz, ...
        additional_vars{iVar, 1}, additional_vars{iVar, 2});
end

% Create the ExportData table
ExportData = table('Size', sz, 'VariableTypes', var_type, 'VariableNames', var_name);

%% Post-Processing Constants
cutoff_freq = 10;  % Frequency used for filtering acceleration
time_sample_offset = 3000 / cutoff_freq;  % Offset in ms


% Read calibration thresholds
SteeringWheelAngle_Th = cfg.Calibratables.SteeringWheelAngle_Th;
AEB_SteeringAngleRate_Override = cfg.Calibratables.AEB_SteeringAngleRate_Override;
PedalPosProIncrease_Th = cfg.Calibratables.PedalPosProIncrease_Th;
PedalPosProIncrease_Th{2, :} = PedalPosProIncrease_Th{2, :} * 100;
YawrateSuspension_Th = cfg.Calibratables.YawrateSuspension_Th;
LateralAcceleration_th = cfg.Calibratables.LateralAcceleration_th;

%% Load and Process AEB Data
for i = 1:N
    filename = files(i).name;
    load(filename);  % Assumes datVars_Extract is loaded

    % Convert speed to km/h and apply filtering
    datVars_Extract.VehicleSpeed = round(datVars_Extract.VehicleSpeed * 3.6, 1);
    datVars_Extract.A2_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A2, cutoff_freq);
    datVars_Extract.A1_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A1, cutoff_freq);

    check = 1;
    if check == 1
        %% Locate Start of AEB Intervention
        locateStart = find(diff(datVars_Extract.LMCAutoBrkEnabled, 1));

        % Store filename in ExportData
        ExportData.label(i) = filename;
        ExportData.condTrue(i) = true;

        % Log start time of the recording
        ExportData.logTime(i) = round(seconds(datVars_Extract.Time(1)), 2);

        %% M0: Start of AEB Intervention
        [AEB_Req, ~, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -6, 'less', 0.1);
        M0 = datVars_Extract.Time(AEB_Req);
        ExportData.m0IntvStart(i) = round(seconds(M0), 2);

        % Vehicle speed at AEB trigger
        vehSpd = datVars_Extract.VehicleSpeed(AEB_Req);
        ExportData.vehSpd(i) = vehSpd;

        class(vehSpd)

        %% Threshold Interpolation Based on Vehicle Speed
        steerAngTh = utils.interpolateThresholdClamped(SteeringWheelAngle_Th, vehSpd);
        ExportData.steerAngTh(i) = steerAngTh;
        steerAngRateTh = utils.interpolateThresholdClamped(AEB_SteeringAngleRate_Override, vehSpd);
        ExportData.steerAngRateTh(i) = steerAngRateTh;
        pedalPosIncTh = utils.interpolateThresholdClamped(PedalPosProIncrease_Th, vehSpd);
        ExportData.pedalPosIncTh(i) = pedalPosIncTh;
        yawRateSuspTh = utils.interpolateThresholdClamped(YawrateSuspension_Th, vehSpd);
        ExportData.yawRateSuspTh(i) = yawRateSuspTh;
        latAccelTh = utils.interpolateThresholdClamped(LateralAcceleration_th, vehSpd);
        ExportData.latAccelTh(i) = latAccelTh;

        %% Pedal Position at AEB Trigger
        pedalStart = datVars_Extract.PedalPosPro(AEB_Req);
        ExportData.pedalStart(i) = pedalStart;
        ExportData.isPedalOnAtStrt(i) = ~isempty(find(pedalStart ~= 0, 1));

        %% Steering and Acceleration at AEB Trigger
        Steer_Start = datVars_Extract.SteerAngle(AEB_Req);              % Optional export
        Steer_Rate_Start = datVars_Extract.SteerAngle_Rate(AEB_Req);    % Optional export
        Lat_Acc_Start = datVars_Extract.A1_Filt(AEB_Req);               % Optional export
    

        %% M2: End of AEB Intervention
        % Check for actuation end and vehicle stop
        Check_if_actuation_end = ~isempty(find(datVars_Extract.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1));
        Check_if_vehicle_stop = ~isempty(find(datVars_Extract.VehicleSpeed(AEB_Req:end) == 0, 1));

        if Check_if_actuation_end && Check_if_vehicle_stop
            % Both conditions met: take earliest of the two
            AEB_End_Req = min( ...
                find(datVars_Extract.VehicleSpeed(AEB_Req:end) == 0, 1) + AEB_Req, ...
                find(datVars_Extract.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1) + AEB_Req);
        elseif ~Check_if_actuation_end && Check_if_vehicle_stop
            % Only vehicle stop detected
            AEB_End_Req = find(datVars_Extract.VehicleSpeed(AEB_Req:end) == 0, 1) + AEB_Req;
        elseif Check_if_actuation_end && ~Check_if_vehicle_stop
            % Only actuation end detected
            AEB_End_Req = find(datVars_Extract.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1) + AEB_Req;
        else
            % Neither condition met: use end of log
            AEB_End_Req = length(datVars_Extract.Time);
        end

        M2 = datVars_Extract.Time(AEB_End_Req);
        ExportData.m2IntvEnd(i) = round(seconds(M2), 2);

        %% Calculate Intervention Duration
        T = M2 - M0;
        ExportData.intvDur(i) = round(seconds(T), 2);

        %% Vehicle Stop Check
        ExportData.vehStopCheck(i) = Check_if_vehicle_stop;

        %% Check Partial Braking / Full Braking
        is_PB_on = ~isempty(find(datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -5.9 & ...
                                datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) > -6.1));
        ExportData.partialBraking(i) = is_PB_on;

        is_FB_on = ~isempty(find(datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -11.9));
        ExportData.fullBraking(i) = is_FB_on;

        %% Vehicle Deceleration Analysis
        if is_PB_on && ~is_FB_on
            disp("Only Partial Braking");
            Vehicle_Respond = find(datVars_Extract.A2_Filt(AEB_Req:AEB_End_Req) < -6, 1);
            Min_Decel = min(datVars_Extract.A2_Filt(Vehicle_Respond:AEB_End_Req));
            Undershoot_Perc = -6 - Min_Decel;
        elseif ~is_PB_on && is_FB_on
            disp("Only Full Braking");
        elseif is_PB_on && is_FB_on
            disp("Both Partial and Full Braking");
        else
            disp("No Braking Detected");
        end

        %% Detect Acceleration Turning Point (System Response)
        [AEB_Resp, ~, kneeValue] = utils.detectKneepoint_v4( ...
            datVars_Extract.Time(AEB_Req:AEB_Req+30), ...
            datVars_Extract.A2(AEB_Req:AEB_Req+30), ...
            'negative', cutoff_freq, 'curvature');

        M1 = datVars_Extract.Time(AEB_Req + AEB_Resp);
        ExportData.m1IntvSysResp(i) = round(seconds(M1), 2);

        %% Calculate Dead Time
        M1_DT = M1 - M0;
        ExportData.m1DeadTime(i) = round(seconds(M1_DT), 2);

        %% Partial Braking Duration
        if is_PB_on
            [PB_Start, PB_End, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -6, 'equal', 0.1);
            pbDur = datVars_Extract.Time(min(AEB_End_Req, PB_End)) - datVars_Extract.Time(PB_Start);
            ExportData.pbDur(i) = round(seconds(pbDur), 2);
        else
            ExportData.pbDur(i) = 0;
        end

        %% Full Braking Duration
        if is_FB_on
            [FB_Start, FB_End, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -15, 'equal', 0.1);
            fbDur = datVars_Extract.Time(min(AEB_End_Req, FB_End)) - datVars_Extract.Time(FB_Start);
            ExportData.fbDur(i) = round(seconds(fbDur), 2);
        else
            ExportData.fbDur(i) = 0;
        end

        %% Throttle Increase
        pedalMax = max(datVars_Extract.PedalPosPro(AEB_Req:AEB_End_Req));
        ExportData.pedalMax(i) = pedalMax;

        isPedalHigh = (pedalMax - pedalStart) > pedalPosIncTh;
        ExportData.isPedalHigh(i) = isPedalHigh;

        ExportData.pedalInc(i) = isPedalHigh * (pedalMax - pedalStart);

        %% Steering Increase
        [~, Steer_Max_Idx] = max(abs(datVars_Extract.SteerAngle(AEB_Req - time_sample_offset:AEB_End_Req)));
        steerMax = round(datVars_Extract.SteerAngle(AEB_Req - time_sample_offset + Steer_Max_Idx - 1), 2);
        absSteerMaxDeg = round(abs(steerMax * 180 / pi()), 2);

        ExportData.steerMax(i) = steerMax;
        ExportData.absSteerMaxDeg(i) = absSteerMaxDeg;
        ExportData.isSteerHigh(i) = absSteerMaxDeg > steerAngTh;

        %% Steering Rate Increase
        [~, Steer_Rate_Max_Idx] = max(abs(datVars_Extract.SteerAngle_Rate(AEB_Req - time_sample_offset:AEB_End_Req)));
        Steer_Rate_Max = datVars_Extract.SteerAngle_Rate(AEB_Req - time_sample_offset + Steer_Rate_Max_Idx - 1);
        absSteerRateMaxDeg = round(abs(Steer_Rate_Max * 180 / pi()), 2);

        ExportData.Steer_Rate_Max(i) = Steer_Rate_Max;
        ExportData.absSteerRateMaxDeg(i) = absSteerRateMaxDeg;
        ExportData.isSteerAngRateHigh(i) = absSteerRateMaxDeg > steerAngRateTh;

        %% Lateral Acceleration Increase
        [~, Lat_Acc_Max_Idx] = max(abs(datVars_Extract.A1_Filt(AEB_Req - time_sample_offset:AEB_End_Req)));
        latAccelMax = round(datVars_Extract.A1_Filt(AEB_Req - time_sample_offset + Lat_Acc_Max_Idx - 1), 2);
        absLatAccelMax = round(abs(latAccelMax), 2);

        ExportData.latAccelMax(i) = latAccelMax;
        ExportData.absLatAccelMax(i) = absLatAccelMax;
        ExportData.isLatAccelHigh(i) = absLatAccelMax > latAccelTh;

        %% Yaw Rate Increase
        [~, Yaw_Rate_Max_Idx] = max(abs(datVars_Extract.YawRate(AEB_Req - time_sample_offset:AEB_End_Req)));
        yawRateMax = round(datVars_Extract.YawRate(AEB_Req - time_sample_offset + Yaw_Rate_Max_Idx - 1), 2);
        absYawRateMaxDeg = round(abs(yawRateMax * 180 / pi()), 2);

        ExportData.yawRateMax(i) = yawRateMax;
        ExportData.absYawRateMaxDeg(i) = absYawRateMaxDeg;
        ExportData.isYawRateHigh(i) = absYawRateMaxDeg > yawRateSuspTh;

        %% Longitudinal Clearance
        longGap = round(datVars_Extract.Long_Clearance(AEB_End_Req), 2);
        ExportData.longGap(i) = longGap;

        %% End of Loop
    end % if check == 1
end % for i = 1:N

%% Export Data to CSV
RowsToDelete = ismissing(ExportData.label);
ExportData(RowsToDelete, :) = [];
ExportData = sortrows(ExportData, 'vehSpd');
writetable(ExportData, 'data_v01.csv');
