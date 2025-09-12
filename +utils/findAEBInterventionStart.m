function [aebStartIdx, M0] = findAEBInterventionStart(obj)

    % Locate AEB intervention start
    %% Input:
    % obj           - Object containing signalMatChunk
    %% Output:
    % aebStartIdx   - Index of AEB request event    
    % M0            - Timestamp of AEB intervention start
    
    [aebStartIdx, ~, ~] = utils.findFirstLastIndicesAdvanced(...
        obj.signalMatChunk.DADCAxLmtIT4, obj.PB_TGT_DECEL, 'less', 0.1);
    if ~isempty(aebStartIdx)
        M0 = obj.signalMatChunk.Time(aebStartIdx(1));
    else
        M0 = [];
    end
end

