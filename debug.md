# Add the entire path string to MATLAB's search path
addpath(genpath('/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project'));

# Create a Config instance
cfg = Config.fromJSON('/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/config/Config.json')

# Create an input handler
handler = InputHandler(cfg);

# Debug mdf2mat converter 
processedData = handler.processMF4Files();


# Process MF4 file 
processedData = handler.processMF4Files();

# AEB event detector 
eventDet = EventDetector()

eventDet.processAllFiles()


# KPIExtractor
By default, MATLAB classdef classes (like KPIExtractor) are value classes, meaning every time you assign to obj inside a method, MATLAB creates a copy, and when the method ends, those changes are not reflected in the original object (unless you explicitly return obj and reassign it).

extractor = KPIExtractor(cfg);
extractor = extractor.processAllMatFiles();
extractor.exportToCSV();

# Visualizer
viz = Visualizer(cfg)

figure;

% Subplot 1: lateral accel, longitudinal accel, target decel
subplot(4,2,1);
plot(dataPy.time, dataPy.latActAccel, 'b', 'LineWidth', 1.2); hold on;
plot(dataPy.time, dataPy.longActAccel, 'r', 'LineWidth', 1.2);
plot(dataPy.time, dataPy.aebTargetDecel, 'k--', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Acceleration');
title('Lat/Long Accel & Target Decel');
legend('Lat Accel','Long Accel','Target Decel');
grid on;

% Subplot 2: ego speed and throttle
subplot(4,2,2);
yyaxis left;
plot(dataPy.time, dataPy.egoSpeed, 'g', 'LineWidth', 1.2);
ylabel('Ego Speed');

yyaxis right;
plot(dataPy.time, dataPy.throttleValue, 'm', 'LineWidth', 1.2);
ylabel('Throttle');

xlabel('Time [s]');
title('Ego Speed & Throttle');
legend('Ego Speed','Throttle');
grid on;

% Subplot 3: longGap
subplot(4,2,3);
plot(dataPy.time, dataPy.longGap, 'c', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Distance [m]');
title('Longitudinal Gap');
grid on;

% Subplot 4: targetId
subplot(4,2,4);
plot(dataPy.time, dataPy.targetId, 'k', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Target ID');
title('Target ID');
grid on;

% Subplot 5: steer wheel angle
subplot(4,2,5);
plot(dataPy.time, dataPy.steerWheelAngle, 'b', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Angle [deg]');
title('Steer Wheel Angle');
grid on;

% Subplot 6: steer wheel angle speed
subplot(4,2,6);
plot(dataPy.time, dataPy.steerWheelAngleSpeed, 'r', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Angle Speed');
title('Steer Wheel Angle Speed');
grid on;

% Subplot 7: yaw rate
subplot(4,2,7);
plot(dataPy.time, dataPy.yawRate, 'm', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Yaw Rate [deg/s]');
title('Yaw Rate');
grid on;

% Subplot 8: TTC and brake pedal pressed
subplot(4,2,8);
yyaxis left;
plot(dataPy.time, dataPy.ttc, 'k', 'LineWidth', 1.2);
ylabel('TTC [s]');

yyaxis right;
stairs(dataPy.time, dataPy.brakePedalPressed, 'r', 'LineWidth', 1.2);
ylabel('Brake Pressed');

xlabel('Time [s]');
title('TTC & Brake Pedal Pressed');
legend('TTC','Brake Pressed');
grid on;



Save and ensure readability: 
chmod +r /Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/+utils/mdf2matSim.py