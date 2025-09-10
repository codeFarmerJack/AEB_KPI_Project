%% ACS_CtrlAutonomousMode

% Extract mode change from signalMat
mode = int8(signalMat.DADCAxLmtIT4);
modeChange = diff(mode);
plot(modeChange)

%% Locate ACS_CtrlAutonomousMode transition 5 -> 8 (start)

locateStart = find(diff(modeChange < -30));

% Check if condition is met for transition
locateStartReq = signalMat.DADCAxLmtIT4(locateStart + 1, 1) < -5.9;

% Extract start times
locateStartTime = signalMat.Time(locateStart, 1) .* locateStartReq;
locateStartTime = seconds(nonzeros(seconds(locateStartTime)));
% Note: 'nonzeros' used because it works better than 'duration' type here

%% Locate ACS_CtrlAutonomousMode transition 8 -> 5 (end)

locateEnd = find(modeChange > 20);
locateEndStat = signalMat.DADCAxLmtIT4(locateEnd + 1, 1) > 20;

locateEndTime = signalMat.Time(locateEnd, 1) .* locateEndStat;
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
    [~, start] = utils.findDuration(signalMat.Time, startT);

    if i + 1 <= loopRun
        [~, startNext] = utils.findDuration(signalMat.Time, locateStartTime(i + 1) - preTime);
    else
        startNext = length(signalMat.Time);
    end

    if i + n <= length(locateEndTime)
        while stop < start
            stopT = locateEndTime(i + n) + postTime;
            [~, stop] = utils.findDuration(signalMat.Time, stopT);

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
        x = signalMat.Time(start:stop);
        y1 = signalMat.VehicleSpeed(start:stop);
        y3 = signalMat.DADCAxLmtIT4(start:stop);
        y4 = signalMat.A2(start:stop);

        signalMatChunk = signalMat(start:stop, :);
        ExtractFileName = fullfile(dest_folder, 'PostProcessing', sprintf('%s_%d.mat', name, i));
        save(ExtractFileName, 'signalMatChunk');

        MAX_Pedal = max(signalMatChunk.PedalPosPro);

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
