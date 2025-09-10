function kpiTable = kpiLatency(kpiTable, i, sig, AEB_Req, cutoff_freq)
    [AEB_Resp, ~, ~] = utils.detectKneepoint_v4( ...
        sig.Time(AEB_Req:AEB_Req+30), ...
        sig.A2(AEB_Req:AEB_Req+30), ...
        'negative', cutoff_freq, 'curvature');

    M0 = sig.Time(AEB_Req);
    M1 = sig.Time(AEB_Req + AEB_Resp);

    kpiTable.m1IntvSysResp(i) = round(seconds(M1), 2);
    kpiTable.m1DeadTime(i)    = round(seconds(M1 - M0), 2);
end
