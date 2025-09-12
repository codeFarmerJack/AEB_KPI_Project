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

pathToKpiSchema = cfg.kpiSchemaPath;  % Path to kpiSchema JSON file

kpiTable = utils.createKpiTableFromJson(pathToKpiSchema, N);

%% Post-Processing Constants
cutoff_freq = 10;  % Frequency used for filtering acceleration
time_sample_offset = 3000 / cutoff_freq;  % Offset in ms


% Read calibration thresholds
SteeringWheelAngle_Th = cfg.calibratables.SteeringWheelAngle_Th;
AEB_SteeringAngleRate_Override = cfg.calibratables.AEB_SteeringAngleRate_Override;
PedalPosProIncrease_Th = cfg.calibratables.PedalPosProIncrease_Th;
PedalPosProIncrease_Th{2, :} = PedalPosProIncrease_Th{2, :} * 100;
YawrateSuspension_Th = cfg.calibratables.YawrateSuspension_Th;
LateralAcceleration_th = cfg.calibratables.LateralAcceleration_th;

%% Load and Process AEB Data
for i = 1:N
    filename = files(i).name;
    load(filename);  % Assumes signalMatChunk is loaded

    % Convert speed to km/h and apply filtering
    signalMatChunk.VehicleSpeed = round(signalMatChunk.VehicleSpeed * 3.6, 1);
    signalMatChunk.A2_Filt = utils.accelFilter(signalMatChunk.Time, signalMatChunk.A2, cutoff_freq);
    signalMatChunk.A1_Filt = utils.accelFilter(signalMatChunk.Time, signalMatChunk.A1, cutoff_freq);

    check = 1;
    if check == 1
        %% Locate Start of AEB Intervention
        locateStart = find(diff(signalMatChunk.LMCAutoBrkEnabled, 1));

        % Store filename in kpiTable
        kpiTable.label(i) = filename;
        kpiTable.condTrue(i) = true;

        % Log start time of the recording
        kpiTable.logTime(i) = round(seconds(signalMatChunk.Time(1)), 2);

        %% M0: Start of AEB Intervention
        [AEB_Req, ~, ~] = utils.findFirstLastIndicesAdvanced(signalMatChunk.DADCAxLmtIT4, -6, 'less', 0.1);
        M0 = signalMatChunk.Time(AEB_Req);
        kpiTable.m0IntvStart(i) = round(seconds(M0), 2);

        % Vehicle speed at AEB trigger
        vehSpd = signalMatChunk.VehicleSpeed(AEB_Req);
        kpiTable.vehSpd(i) = vehSpd;

        class(vehSpd)

        %% Threshold Interpolation Based on Vehicle Speed
        steerAngTh = utils.interpolateThresholdClamped(SteeringWheelAngle_Th, vehSpd);
        kpiTable.steerAngTh(i) = steerAngTh;
        steerAngRateTh = utils.interpolateThresholdClamped(AEB_SteeringAngleRate_Override, vehSpd);
        kpiTable.steerAngRateTh(i) = steerAngRateTh;
        pedalPosIncTh = utils.interpolateThresholdClamped(PedalPosProIncrease_Th, vehSpd);
        kpiTable.pedalPosIncTh(i) = pedalPosIncTh;
        yawRateSuspTh = utils.interpolateThresholdClamped(YawrateSuspension_Th, vehSpd);
        kpiTable.yawRateSuspTh(i) = yawRateSuspTh;
        latAccelTh = utils.interpolateThresholdClamped(LateralAcceleration_th, vehSpd);
        kpiTable.latAccelTh(i) = latAccelTh;

        %% Pedal Position at AEB Trigger
        pedalStart = signalMatChunk.PedalPosPro(AEB_Req);
        kpiTable.pedalStart(i) = pedalStart;
        kpiTable.isPedalOnAtStrt(i) = ~isempty(find(pedalStart ~= 0, 1));

        %% Steering and Acceleration at AEB Trigger
        Steer_Start = signalMatChunk.SteerAngle(AEB_Req);              % Optional export
        Steer_Rate_Start = signalMatChunk.SteerAngle_Rate(AEB_Req);    % Optional export
        Lat_Acc_Start = signalMatChunk.A1_Filt(AEB_Req);               % Optional export
    

        %% M2: End of AEB Intervention
        % Check for actuation end and vehicle stop
        Check_if_actuation_end = ~isempty(find(signalMatChunk.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1));
        Check_if_vehicle_stop = ~isempty(find(signalMatChunk.VehicleSpeed(AEB_Req:end) == 0, 1));

        if Check_if_actuation_end && Check_if_vehicle_stop
            % Both conditions met: take earliest of the two
            AEB_End_Req = min( ...
                find(signalMatChunk.VehicleSpeed(AEB_Req:end) == 0, 1) + AEB_Req, ...
                find(signalMatChunk.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1) + AEB_Req);
        elseif ~Check_if_actuation_end && Check_if_vehicle_stop
            % Only vehicle stop detected
            AEB_End_Req = find(signalMatChunk.VehicleSpeed(AEB_Req:end) == 0, 1) + AEB_Req;
        elseif Check_if_actuation_end && ~Check_if_vehicle_stop
            % Only actuation end detected
            AEB_End_Req = find(signalMatChunk.DADCAxLmtIT4(AEB_Req:end) > -4.9, 1) + AEB_Req;
        else
            % Neither condition met: use end of log
            AEB_End_Req = length(signalMatChunk.Time);
        end

        M2 = signalMatChunk.Time(AEB_End_Req);
        kpiTable.m2IntvEnd(i) = round(seconds(M2), 2);

        %% Calculate Intervention Duration
        T = M2 - M0;
        kpiTable.intvDur(i) = round(seconds(T), 2);

        %% Vehicle Stop Check
        kpiTable.vehStopCheck(i) = Check_if_vehicle_stop;

        %% Check Partial Braking / Full Braking
        is_PB_on = ~isempty(find(signalMatChunk.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -5.9 & ...
                                signalMatChunk.DADCAxLmtIT4(AEB_Req:AEB_End_Req) > -6.1));
        kpiTable.partialBraking(i) = is_PB_on;

        is_FB_on = ~isempty(find(signalMatChunk.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -11.9));
        kpiTable.fullBraking(i) = is_FB_on;

        %% Vehicle Deceleration Analysis
        if is_PB_on && ~is_FB_on
            disp("Only Partial Braking");
            Vehicle_Respond = find(signalMatChunk.A2_Filt(AEB_Req:AEB_End_Req) < -6, 1);
            Min_Decel = min(signalMatChunk.A2_Filt(Vehicle_Respond:AEB_End_Req));
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
            signalMatChunk.Time(AEB_Req:AEB_Req+30), ...
            signalMatChunk.A2(AEB_Req:AEB_Req+30), ...
            'negative', cutoff_freq, 'curvature');

        M1 = signalMatChunk.Time(AEB_Req + AEB_Resp);
        kpiTable.m1IntvSysResp(i) = round(seconds(M1), 2);

        %% Calculate Dead Time
        M1_DT = M1 - M0;
        kpiTable.m1DeadTime(i) = round(seconds(M1_DT), 2);

        %% Partial Braking Duration
        if is_PB_on
            [PB_Start, PB_End, ~] = utils.findFirstLastIndicesAdvanced(signalMatChunk.DADCAxLmtIT4, -6, 'equal', 0.1);
            pbDur = signalMatChunk.Time(min(AEB_End_Req, PB_End)) - signalMatChunk.Time(PB_Start);
            kpiTable.pbDur(i) = round(seconds(pbDur), 2);
        else
            kpiTable.pbDur(i) = 0;
        end

        %% Full Braking Duration
        if is_FB_on
            [FB_Start, FB_End, ~] = utils.findFirstLastIndicesAdvanced(signalMatChunk.DADCAxLmtIT4, -15, 'equal', 0.1);
            fbDur = signalMatChunk.Time(min(AEB_End_Req, FB_End)) - signalMatChunk.Time(FB_Start);
            kpiTable.fbDur(i) = round(seconds(fbDur), 2);
        else
            kpiTable.fbDur(i) = 0;
        end

        %% Throttle Increase
        pedalMax = max(signalMatChunk.PedalPosPro(AEB_Req:AEB_End_Req));
        kpiTable.pedalMax(i) = pedalMax;

        isPedalHigh = (pedalMax - pedalStart) > pedalPosIncTh;
        kpiTable.isPedalHigh(i) = isPedalHigh;

        kpiTable.pedalInc(i) = isPedalHigh * (pedalMax - pedalStart);

        %% Steering Increase
        [~, Steer_Max_Idx] = max(abs(signalMatChunk.SteerAngle(AEB_Req - time_sample_offset:AEB_End_Req)));
        steerMax = round(signalMatChunk.SteerAngle(AEB_Req - time_sample_offset + Steer_Max_Idx - 1), 2);
        absSteerMaxDeg = round(abs(steerMax * 180 / pi()), 2);

        kpiTable.steerMax(i) = steerMax;
        kpiTable.absSteerMaxDeg(i) = absSteerMaxDeg;
        kpiTable.isSteerHigh(i) = absSteerMaxDeg > steerAngTh;

        %% Steering Rate Increase
        [~, Steer_Rate_Max_Idx] = max(abs(signalMatChunk.SteerAngle_Rate(AEB_Req - time_sample_offset:AEB_End_Req)));
        Steer_Rate_Max = signalMatChunk.SteerAngle_Rate(AEB_Req - time_sample_offset + Steer_Rate_Max_Idx - 1);
        absSteerRateMaxDeg = round(abs(Steer_Rate_Max * 180 / pi()), 2);

        kpiTable.Steer_Rate_Max(i) = Steer_Rate_Max;
        kpiTable.absSteerRateMaxDeg(i) = absSteerRateMaxDeg;
        kpiTable.isSteerAngRateHigh(i) = absSteerRateMaxDeg > steerAngRateTh;

        %% Lateral Acceleration Increase
        [~, Lat_Acc_Max_Idx] = max(abs(signalMatChunk.A1_Filt(AEB_Req - time_sample_offset:AEB_End_Req)));
        latAccelMax = round(signalMatChunk.A1_Filt(AEB_Req - time_sample_offset + Lat_Acc_Max_Idx - 1), 2);
        absLatAccelMax = round(abs(latAccelMax), 2);

        kpiTable.latAccelMax(i) = latAccelMax;
        kpiTable.absLatAccelMax(i) = absLatAccelMax;
        kpiTable.isLatAccelHigh(i) = absLatAccelMax > latAccelTh;

        %% Yaw Rate Increase
        [~, Yaw_Rate_Max_Idx] = max(abs(signalMatChunk.YawRate(AEB_Req - time_sample_offset:AEB_End_Req)));
        yawRateMax = round(signalMatChunk.YawRate(AEB_Req - time_sample_offset + Yaw_Rate_Max_Idx - 1), 2);
        absYawRateMaxDeg = round(abs(yawRateMax * 180 / pi()), 2);

        kpiTable.yawRateMax(i) = yawRateMax;
        kpiTable.absYawRateMaxDeg(i) = absYawRateMaxDeg;
        kpiTable.isYawRateHigh(i) = absYawRateMaxDeg > yawRateSuspTh;

        %% Longitudinal Clearance
        longGap = round(signalMatChunk.Long_Clearance(AEB_End_Req), 2);
        kpiTable.longGap(i) = longGap;

        %% End of Loop
    end % if check == 1
end % for i = 1:N

%% Export Data to CSV
RowsToDelete = ismissing(kpiTable.label);
kpiTable(RowsToDelete, :) = [];
kpiTable = sortrows(kpiTable, 'vehSpd');
writetable(kpiTable, 'data_v01.csv');
