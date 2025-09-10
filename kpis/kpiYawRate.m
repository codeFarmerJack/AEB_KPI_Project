function kpiTable = kpiYawRate(kpiTable, i, sig, AEB_Req, yawRateSuspTh, offset)
    [~, idx] = max(abs(sig.YawRate(AEB_Req - offset:end)));
    yawRateMax = sig.YawRate(AEB_Req - offset + idx - 1);
    absYawRateMaxDeg = round(abs(yawRateMax * 180 / pi()), 2);

    kpiTable.yawRateMax(i) = yawRateMax;
    kpiTable.absYawRateMaxDeg(i) = absYawRateMaxDeg;
    kpiTable.isYawRateHigh(i) = absYawRateMaxDeg > yawRateSuspTh;
end
