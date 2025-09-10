function [kneeIdx, kneeTime, kneeValue] = detectKneepoint_v4(time, acc, direction, cutoffFreq, method)
    % Ensure inputs are column vectors
    time = time(:);
    acc = acc(:);
 
    % Convert duration to numeric seconds if needed
    if isduration(time)
        time = seconds(time);
    end
 
    % Sampling frequency
    dt = mean(diff(time));
    fs = 1 / dt;
 
    % Design Butterworth low-pass filter
    [b, a] = butter(4, cutoffFreq / (fs / 2), 'low');
    accFiltered = filtfilt(b, a, acc);
 
    % Compute first and second derivatives
    dAcc = gradient(accFiltered, dt);
    ddAcc = gradient(dAcc, dt);
 
    % Detect turning points in dAcc
    localMaxIdx = islocalmax(dAcc);
    localMinIdx = islocalmin(dAcc);
    turningPointIdx = localMaxIdx | localMinIdx;
    numTurningPoints = sum(turningPointIdx);
    turningPointTimes = time(turningPointIdx);
 
    % Apply direction filter
    if strcmpi(direction, 'positive')
        slopeMask = dAcc > 0;
        curvatureMask = ddAcc > 0;
    elseif strcmpi(direction, 'negative')
        slopeMask = dAcc < 0;
        curvatureMask = ddAcc < 0;
    else
        error('Direction must be either "positive" or "negative".');
    end
 
    % Select detection method
    switch lower(method)
        case 'curvature'
            ddAccFiltered = abs(ddAcc);
            ddAccFiltered(~curvatureMask) = -inf;
            [~, kneeIdx] = max(ddAccFiltered);
 
        case 'slope'
            dAccFiltered = abs(dAcc);
            dAccFiltered(~slopeMask) = -inf;
            [~, kneeIdx] = max(dAccFiltered);
 
        otherwise
            error('Method must be either "curvature" or "slope".');
    end
 
    % Extract kneepoint time and value
    kneeTime = time(kneeIdx);
    kneeValue = acc(kneeIdx);
 
end
 
 