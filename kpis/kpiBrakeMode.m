function kpiTable = kpiBrakeMode(kpiTable, i, sig, AEB_Req, cutoff_freq)
    aebEndReq = length(sig.Time); % Simplified: you can reuse your end-detection logic
    isPbOn = any(sig.DADCAxLmtIT4(AEB_Req:aebEndReq) < -6.1 & ...
                   sig.DADCAxLmtIT4(AEB_Req:aebEndReq) > -5.9);
    isFbOn = any(sig.DADCAxLmtIT4(AEB_Req:aebEndReq) < -11.9);

    kpiTable.partialBraking(i) = isPbOn;
    kpiTable.fullBraking(i) = isFbOn;

    if isPbOn
        [PB_Start, PB_End, ~] = utils.findFirstLastIndicesAdvanced(sig.DADCAxLmtIT4, -6, 'equal', 0.1);
        pbDur = sig.Time(PB_End) - sig.Time(PB_Start);
        kpiTable.pbDur(i) = round(seconds(pbDur), 2);
    else
        kpiTable.pbDur(i) = 0;
    end

    if isFbOn
        [FB_Start, FB_End, ~] = utils.findFirstLastIndicesAdvanced(sig.DADCAxLmtIT4, -15, 'equal', 0.1);
        fbDur = sig.Time(FB_End) - sig.Time(FB_Start);
        kpiTable.fbDur(i) = round(seconds(fbDur), 2);
    else
        kpiTable.fbDur(i) = 0;
    end
end
