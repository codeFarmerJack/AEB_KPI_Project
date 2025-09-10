function kpiTable = kpiLatAccel(kpiTable, i, sig, AEB_Req, latAccelTh, offset)
    [~, idx] = max(abs(sig.A1_Filt(AEB_Req - offset:end)));
    latAccelMax = sig.A1_Filt(AEB_Req - offset + idx - 1);
    absLatAccelMax = abs(latAccelMax);

    kpiTable.latAccelMax(i) = latAccelMax;
    kpiTable.absLatAccelMax(i) = absLatAccelMax;
    kpiTable.isLatAccelHigh(i) = absLatAccelMax > latAccelTh;
end
