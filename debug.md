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
plot(data1.signalMatChunk.time, data1.signalMatChunk.latActAccel, 'b', 'LineWidth', 1.2); hold on;
plot(data1.signalMatChunk.time, data1.signalMatChunk.longActAccel, 'r', 'LineWidth', 1.2);
plot(data1.signalMatChunk.time, data1.signalMatChunk.aebTargetDecel, 'k--', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Acceleration');
title('Lat/Long Accel & Target Decel');
legend('Lat Accel','Long Accel','Target Decel');
grid on;

% Subplot 2: ego speed and throttle
subplot(4,2,2);
yyaxis left;
plot(data1.signalMatChunk.time, data1.signalMatChunk.egoSpeed, 'g', 'LineWidth', 1.2);
ylabel('Ego Speed');

yyaxis right;
plot(data1.signalMatChunk.time, data1.signalMatChunk.throttleValue, 'm', 'LineWidth', 1.2);
ylabel('Throttle');

xlabel('Time [s]');
title('Ego Speed & Throttle');
legend('Ego Speed','Throttle');
grid on;

% Subplot 3: longGap
subplot(4,2,3);
plot(data1.signalMatChunk.time, data1.signalMatChunk.longGap, 'c', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Distance [m]');
title('Longitudinal Gap');
grid on;

% Subplot 4: targetId
subplot(4,2,4);
plot(data1.signalMatChunk.time, data1.signalMatChunk.targetId, 'k', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Target ID');
title('Target ID');
grid on;

% Subplot 5: steer wheel angle
subplot(4,2,5);
plot(data1.signalMatChunk.time, data1.signalMatChunk.steerWheelAngle, 'b', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Angle [deg]');
title('Steer Wheel Angle');
grid on;

% Subplot 6: steer wheel angle speed
subplot(4,2,6);
plot(data1.signalMatChunk.time, data1.signalMatChunk.steerWheelAngleSpeed, 'r', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Angle Speed');
title('Steer Wheel Angle Speed');
grid on;

% Subplot 7: yaw rate
subplot(4,2,7);
plot(data1.signalMatChunk.time, data1.signalMatChunk.yawRate, 'm', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('Yaw Rate [deg/s]');
title('Yaw Rate');
grid on;

% Subplot 8: TTC and brake pedal pressed
subplot(4,2,8);
yyaxis left;
plot(data1.signalMatChunk.time, data1.signalMatChunk.ttc, 'k', 'LineWidth', 1.2);
ylabel('TTC [s]');

yyaxis right;
stairs(data1.signalMatChunk.time, data1.signalMatChunk.brakePedalPressed, 'r', 'LineWidth', 1.2);
ylabel('Brake Pressed');

xlabel('Time [s]');
title('TTC & Brake Pedal Pressed');
legend('TTC','Brake Pressed');
grid on;



Save and ensure readability: 
chmod +r /Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_Project/+utils/mdf2matSim.py