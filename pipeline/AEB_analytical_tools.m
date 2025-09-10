% filepath: /Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/io/AEB_analytical_tools.m
% ...existing code...
%% Initialization
clear all;
clc;

originpath = pwd; % Save current working directory
seldatapath = uigetdir(path); % Prompt user to select folder containing log files
cd(seldatapath); % Change to selected directory

files = dir('*.mat'); % List all .mat files in the folder
N = length(files); % Total number of files

%% Define ExportData Table Format
var_name = {'Label'};
var_type = {'string'};
sz = [N, 1];

% Define additional variables and their types
additional_vars = {
    'LogTime', 'double';
    'Veh_Spd', 'double';
    'M0_Intervention_Start', 'double';
    'M1_Intervention_Sys_Resp', 'double';
    'M1_DeadTime', 'double';
    'M2_Intervention_End', 'double';
    'Intervention_Duration', 'double';
    'Veh_Stop_Check', 'logical';
    'Partial_Braking', 'logical';
    'Full_Braking', 'logical';
    'PB_Duration', 'double';
    'FB_Duration', 'double';
    'Pedal_Start', 'double';
    'is_Pedal_Pressed_at_Start', 'double';
    'Pedal_Max', 'double';
    'Pedal_Inc', 'double';
    'pedel_pos_inc_th', 'double';
    'Is_Pedal_Inc', 'logical';
    'Steer_Max', 'double';
    'Abs_Steer_Max_deg', 'double';
    'steering_angle_th', 'double';
    'is_Steer_Inc', 'logical';
    'Abs_Steer_Rate_Max_deg', 'double';
    'steering_angle_rate_th', 'double';
    'is_Steer_Rate_Inc', 'logical';
    'Lat_Acc_Max', 'double';
    'Abs_Lat_Acc_Max', 'double';
    'lat_accel_th', 'double';
    'is_Lat_Acc_Inc', 'logical';
    'Yaw_Rate_Max', 'double';
    'yaw_rate_suspension_th', 'double';
    'Abs_Yaw_Rate_Max_deg', 'double';
    'is_Yaw_Rate_Inc', 'logical';
    'Long_Clearance', 'double';
    'Cond_true', 'logical'
};

% Add metadata for each variable
for i = 1:size(additional_vars, 1)
    [var_name, var_type, sz] = utils.addVariableMetadata(var_name, var_type, sz, ...
        additional_vars{i,1}, additional_vars{i,2});
end

% Create the ExportData table
ExportData = table('Size', sz, 'VariableTypes', var_type, 'VariableNames', var_name);

%% Post-Processing Constants
cutoff_freq = 10; % Frequency used for filtering acceleration
time_sample_offset = 3000 / cutoff_freq; % Offset in ms

%% Load Calibration Thresholds
cal_path = "C:\Users\jwang79\OneDrive\OneDrive - JLR\04_ActiveSafety\02_cal_plan";
cal_file = 'Active_Safety_Long_Calibration_Plan.xlsx';
cal_file_path = fullfile(cal_path, cal_file);

SteeringWheelAngle_Th = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M7:X8');
AEB_SteeringAngleRate_Override = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M13:X14');
PedalPosProIncrease_Th = readmatrix(cal_file_path, 'Sheet', 'throttle_abrt_aeb', 'Range', 'L12:P13');
PedalPosProIncrease_Th(2, :) = PedalPosProIncrease_Th(2, :) * 100; % Convert to percentage
YawrateSuspension_Th = readmatrix(cal_file_path, 'Sheet', 'yaw_rate', 'Range', 'K6:P7');
LateralAcceleration_th = readmatrix(cal_file_path, 'Sheet', 'lat_accel', 'Range', 'I6:N7');

%% Process Each AEB Log File
for i = 1:N
    filename = files(i).name;
    load(filename); % Load .mat file

    % Convert speed to km/h and apply filtering
    datVars_Extract.VehicleSpeed = round(datVars_Extract.VehicleSpeed * 3.6, 1);
    datVars_Extract.A2_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A2, cutoff_freq);
    datVars_Extract.A1_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A1, cutoff_freq);

    Check = 1;
    if Check == 1
        %% Locate Start of AEB Intervention
        locateStart% filepath: /Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/io/AEB_analytical_tools.m
% ...existing code...
%% Initialization
clear all;
clc;

originpath = pwd; % Save current working directory
seldatapath = uigetdir(path); % Prompt user to select folder containing log files
cd(seldatapath); % Change to selected directory

files = dir('*.mat'); % List all .mat files in the folder
N = length(files); % Total number of files

%% Define ExportData Table Format
var_name = {'Label'};
var_type = {'string'};
sz = [N, 1];

% Define additional variables and their types
additional_vars = {
    'LogTime', 'double';
    'Veh_Spd', 'double';
    'M0_Intervention_Start', 'double';
    'M1_Intervention_Sys_Resp', 'double';
    'M1_DeadTime', 'double';
    'M2_Intervention_End', 'double';
    'Intervention_Duration', 'double';
    'Veh_Stop_Check', 'logical';
    'Partial_Braking', 'logical';
    'Full_Braking', 'logical';
    'PB_Duration', 'double';
    'FB_Duration', 'double';
    'Pedal_Start', 'double';
    'is_Pedal_Pressed_at_Start', 'double';
    'Pedal_Max', 'double';
    'Pedal_Inc', 'double';
    'pedel_pos_inc_th', 'double';
    'Is_Pedal_Inc', 'logical';
    'Steer_Max', 'double';
    'Abs_Steer_Max_deg', 'double';
    'steering_angle_th', 'double';
    'is_Steer_Inc', 'logical';
    'Abs_Steer_Rate_Max_deg', 'double';
    'steering_angle_rate_th', 'double';
    'is_Steer_Rate_Inc', 'logical';
    'Lat_Acc_Max', 'double';
    'Abs_Lat_Acc_Max', 'double';
    'lat_accel_th', 'double';
    'is_Lat_Acc_Inc', 'logical';
    'Yaw_Rate_Max', 'double';
    'yaw_rate_suspension_th', 'double';
    'Abs_Yaw_Rate_Max_deg', 'double';
    'is_Yaw_Rate_Inc', 'logical';
    'Long_Clearance', 'double';
    'Cond_true', 'logical'
};

% Add metadata for each variable
for i = 1:size(additional_vars, 1)
    [var_name, var_type, sz] = utils.addVariableMetadata(var_name, var_type, sz, ...
        additional_vars{i,1}, additional_vars{i,2});
end

% Create the ExportData table
ExportData = table('Size', sz, 'VariableTypes', var_type, 'VariableNames', var_name);

%% Post-Processing Constants
cutoff_freq = 10; % Frequency used for filtering acceleration
time_sample_offset = 3000 / cutoff_freq; % Offset in ms

%% Load Calibration Thresholds
cal_path = "C:\Users\jwang79\OneDrive\OneDrive - JLR\04_ActiveSafety\02_cal_plan";
cal_file = 'Active_Safety_Long_Calibration_Plan.xlsx';
cal_file_path = fullfile(cal_path, cal_file);

SteeringWheelAngle_Th = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M7:X8');
AEB_SteeringAngleRate_Override = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M13:X14');
PedalPosProIncrease_Th = readmatrix(cal_file_path, 'Sheet', 'throttle_abrt_aeb', 'Range', 'L12:P13');
PedalPosProIncrease_Th(2, :) = PedalPosProIncrease_Th(2, :) * 100; % Convert to percentage
YawrateSuspension_Th = readmatrix(cal_file_path, 'Sheet', 'yaw_rate', 'Range', 'K6:P7');
LateralAcceleration_th = readmatrix(cal_file_path, 'Sheet', 'lat_accel', 'Range', 'I6:N7');

%% Process Each AEB Log File
for i = 1:N
    filename = files(i).name;
    load(filename); % Load .mat file

    % Convert speed to km/h and apply filtering
    datVars_Extract.VehicleSpeed = round(datVars_Extract.VehicleSpeed * 3.6, 1);
    datVars_Extract.A2_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A2, cutoff_freq);
    datVars_Extract.A1_Filt = utils.accelFilter(datVars_Extract.Time, datVars_Extract.A1, cutoff_freq);

    Check = 1;
    if Check == 1
        %% Locate Start of AEB Intervention
        locateStart= find(diff(datVars_Extract.LMCAutoBrkEnabled, 1));
%% Event Definitions
% M0 = AEB Start Event
% M1 = Vehicle Reaction (Deceleration begins)
% M2 = End of AEB Event (Vehicle stops or AEB aborts)



%% Log Event Calculations



% Store filename in export table
Label = filename;
ExportData.Label(i) = Label;



% Set condition flag to true for graphing logic
ExportData.Cond_true(i) = 1;



% Log start time of the recording
Log_Time = datVars_Extract.Time(1);
ExportData.LogTime(i) = round(seconds(Log_Time), 2);



%% M0: Start of AEB Intervention
% Detect when longitudinal acceleration drops below threshold
[AEB_Req, ~, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -6, 'less', 0.1);
M0 = datVars_Extract.Time(AEB_Req);
ExportData.M0_Intervention_Start(i) = round(seconds(M0), 2);



% Vehicle speed at AEB trigger
VehSpd = round(datVars_Extract.VehicleSpeed(AEB_Req), 2);
ExportData.Veh_Spd(i) = VehSpd;



%% Interpolate Calibration Thresholds Based on Vehicle Speed
ExportData.steering_angle_th(i) = round(utils.interpolateThresholdClamped(SteeringWheelAngle_Th, VehSpd), 2);
ExportData.steering_angle_rate_th(i) = round(utils.interpolateThresholdClamped(AEB_SteeringAngleRate_Override, VehSpd), 2);
ExportData.pedel_pos_inc_th(i) = round(utils.interpolateThresholdClamped(PedalPosProIncrease_Th, VehSpd), 2);
ExportData.yaw_rate_suspension_th(i) = round(utils.interpolateThresholdClamped(YawrateSuspension_Th, VehSpd), 2);
ExportData.lat_accel_th(i) = round(utils.interpolateThresholdClamped(LateralAcceleration_th, VehSpd), 2);



%% Pedal Position at AEB Trigger
Pedal_Start = datVars_Extract.PedalPosPro(AEB_Req);
ExportData.Pedal_Start(i) = Pedal_Start;



% Check if pedal was pressed
is_Pedal_Pressed_at_Start = isempty(find(Pedal_Start == 0));
ExportData.is_Pedal_Pressed_at_Start(i) = is_Pedal_Pressed_at_Start;
%% Steering and Acceleration at AEB Trigger



% Steering wheel angle at AEB trigger
Steer_Start = datVars_Extract.SteerAngle(AEB_Req);
% ExportData.Steer_Start(i) = Steer_Start;  % Uncomment if needed



% Steering wheel angle rate at AEB trigger
Steer_Rate_Start = datVars_Extract.SteerAngle_Rate(AEB_Req);
% ExportData.Steer_Rate_Start(i) = Steer_Rate_Start;  % Uncomment if needed



% Lateral acceleration at AEB trigger
Lat_Acc_Start = datVars_Extract.A1_Filt(AEB_Req);



%% M2: End of AEB Intervention



% Check for end of actuation and vehicle stop
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



% Record M2 timestamp
M2 = datVars_Extract.Time(AEB_End_Req);
ExportData.M2_Intervention_End(i) = round(seconds(M2), 2);



%% Calculate Intervention Duration
T = M2 - M0;
ExportData.Intervention_Duration(i) = round(seconds(T), 2);



%% Vehicle Stop Check
ExportData.Veh_Stop_Check(i) = Check_if_vehicle_stop;
 
%% Check Partial and Full Braking



% Partial Braking: acceleration between -6.1 and -5.9 m/s²
is_PB_on = ~isempty(find(datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -5.9 & ...
                         datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) > -6.1));
ExportData.Partial_Braking(i) = is_PB_on;



% Full Braking: acceleration below -11.9 m/s²
is_FB_on = ~isempty(find(datVars_Extract.DADCAxLmtIT4(AEB_Req:AEB_End_Req) < -11.9));
ExportData.Full_Braking(i) = is_FB_on;



%% Vehicle Deceleration Check



if is_PB_on && ~is_FB_on
    disp("Only Partial Braking");
    Vehicle_Respond = find(datVars_Extract.A2_Filt(AEB_Req:AEB_End_Req) < -6, 1);
    Min_Decel = min(datVars_Extract.A2_Filt(Vehicle_Respond:AEB_End_Req));
    Undershoot_Perc = (-6 - Min_Decel);
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
ExportData.M1_Intervention_Sys_Resp(i) = round(seconds(M1), 2);



%% Calculate Dead Time (Delay between AEB trigger and system response)



M1_DT = M1 - M0;
ExportData.M1_DeadTime(i) = round(seconds(M1_DT), 2);



%% Calculate Partial Braking Duration



if is_PB_on
    [PB_Start, PB_End, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -6, 'equal', 0.1);
    PB_Duration = datVars_Extract.Time(min(AEB_End_Req, PB_End)) - datVars_Extract.Time(PB_Start);
    ExportData.PB_Duration(i) = round(seconds(PB_Duration), 2);
else
    ExportData.PB_Duration(i) = 0;
end



%% Calculate Full Braking Duration



if is_FB_on
    [FB_Start, FB_End, ~] = utils.findFirstLastIndicesAdvanced(datVars_Extract.DADCAxLmtIT4, -15, 'equal', 0.1);
    FB_Duration = datVars_Extract.Time(min(AEB_End_Req, FB_End)) - datVars_Extract.Time(FB_Start);
    ExportData.FB_Duration(i) = round(seconds(FB_Duration), 2);
else
    ExportData.FB_Duration(i) = 0;
end



%% Check Throttle Increase



Pedal_Max = max(datVars_Extract.PedalPosPro(AEB_Req:AEB_End_Req));
ExportData.Pedal_Max(i) = Pedal_Max;



is_Pedal_Inc = ~isempty(find(Pedal_Max - Pedal_Start > pedel_pos_inc_th));
ExportData.Is_Pedal_Inc(i) = is_Pedal_Inc;



if is_Pedal_Inc
    ExportData.Pedal_Inc(i) = Pedal_Max - Pedal_Start;
else
    ExportData.Pedal_Inc(i) = 0;
end
 
%% Check Steering Increase
[Steer_Max_Abs, Steer_Max_Idx] = max(abs(datVars_Extract.SteerAngle(AEB_Req - time_sample_offset:AEB_End_Req)));
Steer_Max = round(datVars_Extract.SteerAngle(AEB_Req - time_sample_offset + Steer_Max_Idx - 1), 2);  % Adjust for MATLAB indexing
Abs_Steer_Max_deg = round(abs(Steer_Max * 180 / pi()), 2);



ExportData.Steer_Max(i) = Steer_Max;
ExportData.Abs_Steer_Max_deg(i) = Abs_Steer_Max_deg;
ExportData.is_Steer_Inc(i) = Abs_Steer_Max_deg > steering_angle_th;



%% Check Steering Rate Increase
[Steer_Rate_Max_Abs, Steer_Rate_Max_Idx] = max(abs(datVars_Extract.SteerAngle_Rate(AEB_Req - time_sample_offset:AEB_End_Req)));
Steer_Rate_Max = datVars_Extract.SteerAngle_Rate(AEB_Req - time_sample_offset + Steer_Rate_Max_Idx - 1);
Abs_Steer_Rate_Max_deg = round(abs(Steer_Rate_Max * 180 / pi()), 2);



ExportData.Steer_Rate_Max(i) = Steer_Rate_Max;
ExportData.Abs_Steer_Rate_Max_deg(i) = Abs_Steer_Rate_Max_deg;
ExportData.is_Steer_Rate_Inc(i) = Abs_Steer_Rate_Max_deg > steering_angle_rate_th;



%% Check Lateral Acceleration Increase
[Lat_Acc_Max_Abs, Lat_Acc_Max_Idx] = max(abs(datVars_Extract.A1_Filt(AEB_Req - time_sample_offset:AEB_End_Req)));
Lat_Acc_Max = round(datVars_Extract.A1_Filt(AEB_Req - time_sample_offset + Lat_Acc_Max_Idx - 1), 2);
Abs_Lat_Acc_Max = round(abs(Lat_Acc_Max), 2);



ExportData.Lat_Acc_Max(i) = Lat_Acc_Max;
ExportData.Abs_Lat_Acc_Max(i) = Abs_Lat_Acc_Max;
ExportData.is_Lat_Acc_Inc(i) = Abs_Lat_Acc_Max > lat_accel_th;



%% Check Yaw Rate Increase
[Yaw_Max_Abs, Yaw_Rate_Max_Idx] = max(abs(datVars_Extract.YawRate(AEB_Req - time_sample_offset:AEB_End_Req)));
Yaw_Rate_Max = round(datVars_Extract.YawRate(AEB_Req - time_sample_offset + Yaw_Rate_Max_Idx - 1), 2);
Abs_Yaw_Rate_Max_deg = round(abs(Yaw_Rate_Max * 180 / pi()), 2);



ExportData.Yaw_Rate_Max(i) = Yaw_Rate_Max;
ExportData.Abs_Yaw_Rate_Max_deg(i) = Abs_Yaw_Rate_Max_deg;
ExportData.is_Yaw_Rate_Inc(i) = Abs_Yaw_Rate_Max_deg > yaw_rate_suspension_th;



%% Longitudinal Clearance
Long_Clearance = round(datVars_Extract.Long_Clearance(AEB_End_Req), 2);
ExportData.Long_Clearance(i) = Long_Clearance;



%% Optional Plotting (Commented Out)
% figure;
% subplot(4,1,1); plot(datVars_Extract.Time, datVars_Extract.VehicleSpeed, 'k-');
% subplot(4,1,2); plot(datVars_Extract.Time, datVars_Extract.A2, 'r-'); hold on;
% subplot(4,1,3); plot(datVars_Extract.Time, datVars_Extract.PedalPosPro, 'g-');
% subplot(4,1,4); plot(datVars_Extract.Time, datVars_Extract.SteerAngle, 'm-');



% figure;
% plot(datVars_Extract.Time, datVars_Extract.A1, 'r-'); hold on;
% plot(datVars_Extract.Time, datVars_Extract.A1_Filt, 'b--'); ylim([-5 5]);



%% End of Processing Loop
end % if Check == 1
end % for i = 1:N



%% Export Data to CSV
RowsToDelete = ismissing(ExportData.Label);
ExportData(RowsToDelete, :) = [];
ExportData = sortrows(ExportData, 'Veh_Spd');
writetable(ExportData, 'data.csv');
 

