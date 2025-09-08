function [kneeIdx, kneeTime, kneeValue] = detectKneepoint_v3(time, acc, direction, cutoffFreq, method)
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

    % Plot results
    figure;

    subplot(3,1,1);
    plot(time, acc, 'r-', 'DisplayName', 'Original Acceleration');
    hold on;
    plot(time, accFiltered, 'b--', 'DisplayName', 'Filtered Acceleration');
    plot(kneeTime, kneeValue, 'ko', 'MarkerSize', 8, 'DisplayName', 'Kneepoint');
    legend('Location', 'southwest');
    xlabel('Time (s)');
    ylabel('Acceleration (m/s^2)');
    title('Acceleration and Kneepoint');
    grid on;

    subplot(3,1,2);
    plot(time, dAcc, 'g-', 'DisplayName', 'First Derivative (dAcc)');
    hold on;
    plot(time(kneeIdx), dAcc(kneeIdx), 'ko', 'MarkerSize', 8, 'DisplayName', 'Kneepoint');
    legend('Location', 'southwest');
    xlabel('Time (s)');
    ylabel('dAcc (m/s^3)');
    title('First Derivative of Acceleration');
    grid on;

    subplot(3,1,3);
    plot(time, ddAcc, 'm-', 'DisplayName', 'Second Derivative (ddAcc)');
    hold on;
    plot(time(kneeIdx), ddAcc(kneeIdx), 'ko', 'MarkerSize', 8, 'DisplayName', 'Kneepoint');
    legend('Location', 'southwest');
    xlabel('Time (s)');
    ylabel('ddAcc (m/s^4)');
    title('Second Derivative of Acceleration');
    grid on;
end
