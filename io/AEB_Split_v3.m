%% ACS_CtrlAutonomousMode

% Extract mode change from datVars
Mode = int8(datVars.DADCAxLmtIT4);
Mode_Change = diff(Mode);
% plot(Mode_Change)

%% Locate ACS_CtrlAutonomousMode transition 5 -> 8 (start)

locateStart = find(diff(Mode_Change < -30));

% Check if condition is met for transition
locateStartReq = datVars.DADCAxLmtIT4(locateStart + 1, 1) < -5.9;

% Extract start times
locateStartTime = datVars.Time(locateStart, 1) .* locateStartReq;
locateStartTime = seconds(nonzeros(seconds(locateStartTime)));
% Note: 'nonzeros' used because it works better than 'duration' type here

%% Locate ACS_CtrlAutonomousMode transition 8 -> 5 (end)

locateEnd = find(Mode_Change > 20);
locateEndStat = datVars.DADCAxLmtIT4(locateEnd + 1, 1) > 20;

locateEndTime = datVars.Time(locateEnd, 1) .* locateEndStat;
locateEndTime = seconds(nonzeros(seconds(locateEndTime)));
% Alternative logic: locateEndTime = locateStartTime + seconds(4);

%% Extract AEB events (-1s to +1s around event)

preTime = seconds(4);
postTime = seconds(3);
loopRun = length(locateStartTime);
plotGraph = true;
n = 0;
stop = 0;

for i = 1:loopRun
    startT = locateStartTime(i) - preTime;
    [~, start] = utils.find_duration(datVars.Time, startT);

    if i + 1 <= loopRun
        [~, startNext] = utils.find_duration(datVars.Time, locateStartTime(i + 1) - preTime);
    else
        startNext = length(datVars.Time);
    end

    if i + n <= length(locateEndTime)
        while stop < start
            stopT = locateEndTime(i + n) + postTime;
            [~, stop] = utils.find_duration(datVars.Time, stopT);

            if stop < start
                n = n + 1;
            end

            if i + n > length(locateEndTime) || stop > startNext || ...
               (stopT - startT - preTime - postTime) > seconds(30)
                start = 1;
                stop = 1;
                plotGraph = false;
            end
        end
    else
        plotGraph = true;
    end

    if plotGraph
        x = datVars.Time(start:stop);
        y1 = datVars.VehicleSpeed(start:stop);
        y3 = datVars.DADCAxLmtIT4(start:stop);
        y4 = datVars.A2(start:stop);

        datVars_Extract = datVars(start:stop, :);
        ExtractFileName = fullfile(dest_folder, 'PostProcessing', sprintf('%s_%d.mat', name, i));
        save(ExtractFileName, 'datVars_Extract');

        MAX_Pedal = max(datVars_Extract.PedalPosPro);

        % Plotting
        figure;
        subplot(2, 1, 1);
        plot(x, y1, 'b-', 'DisplayName', 'Vehicle Speed');
        hold on;
        legend('Location', 'northeast');
        xlabel('Time (s)');
        ylabel('Vehicle Speed (m/s)');
        title('Vehicle Speed');
        grid on; grid minor;

        subplot(2, 1, 2);
        plot(x, y3, 'DisplayName', 'Accel Request');
        hold on;
        plot(x, y4, 'DisplayName', 'Long Accel');
        grid on; grid minor;
        legend('Location', 'northeast');
        xlabel('Time (s)');
        ylabel('Acceleration (m/s²)');
        title('Vehicle Acceleration');
    end

    plotGraph = true;
end
