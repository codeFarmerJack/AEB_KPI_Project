function kpiTable = kpiSteeringWheel(kpiTable, i, sig, AEB_Req, steerAngTh, steerAngRateTh, offset)
    % Steering angle
    [~, idx] = max(abs(sig.SteerAngle(AEB_Req - offset:end)));
    steerMax = sig.SteerAngle(AEB_Req - offset + idx - 1);
    absSteerMaxDeg = round(abs(steerMax * 180 / pi()), 2);

    kpiTable.steerMax(i) = steerMax;
    kpiTable.absSteerMaxDeg(i) = absSteerMaxDeg;
    kpiTable.isSteerHigh(i) = absSteerMaxDeg > steerAngTh;

    % Steering rate
    [~, idxRate] = max(abs(sig.SteerAngle_Rate(AEB_Req - offset:end)));
    steerRateMax = sig.SteerAngle_Rate(AEB_Req - offset + idxRate - 1);
    absSteerRateMaxDeg = round(abs(steerRateMax * 180 / pi()), 2);

    kpiTable.absSteerRateMaxDeg(i) = absSteerRateMaxDeg;
    kpiTable.isSteerAngRateHigh(i) = absSteerRateMaxDeg > steerAngRateTh;
end
