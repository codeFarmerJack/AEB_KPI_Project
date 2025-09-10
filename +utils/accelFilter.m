function [accFiltered] = accelFilter(time,acc,cutoffFreq)
 
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
 
 
end