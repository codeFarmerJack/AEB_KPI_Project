function kpiTable = kpiThrottle(kpiTable, i, sig, AEB_Req, pedalPosIncTh)
    pedalStart = sig.PedalPosPro(AEB_Req);
    kpiTable.pedalStart(i) = pedalStart;
    kpiTable.isPedalOnAtStrt(i) = pedalStart ~= 0;

    pedalMax = max(sig.PedalPosPro(AEB_Req:end));
    kpiTable.pedalMax(i) = pedalMax;

    isPedalHigh = (pedalMax - pedalStart) > pedalPosIncTh;
    kpiTable.isPedalHigh(i) = isPedalHigh;
    kpiTable.pedalInc(i) = isPedalHigh * (pedalMax - pedalStart);
end
