function [Data, m, used, sigs, Raster] = mdf2mat_new(varargin)
    % mdf2mat reads mdf objects (.dat/.mf4) into a matlab timetable
    %
    % Usage:
    %   [Data, m, used, sigs, Raster] = mdf2mat_new(datPath,'SignalDatabase',map,'Resample',0.01);

    % --- Parse inputs ---
    p = inputParser;
    addRequired(p,'datPath',@(x)ischar(x) && contains(x,{'.dat','.mf4'}));
    addParameter(p,'SignalDatabase',[],@(x)istable(x));
    addParameter(p,'Resample',[],@(x)isa(x,'double'));
    parse(p,varargin{:});
    in = p.Results;

    Data = [];
    used = [];
    Raster = [];

    % --- Read MDF file if needed ---
    if isempty(in.SignalDatabase)
        error('SignalDatabase is required in this workflow.');
    end

    m = mdf(in.datPath);
    sigs = m.channelList;
    sigs_copy = strrep(sigs.ChannelName,'.','_');
    sigs_copy = removeMdfSuffixes(sigs_copy);

    % --- Predefine outputs ---
    Raster = cell2table(cell(0,2));
    Raster.Properties.VariableNames = {'Variable','Raster'};
    toRead = [];

    % --- Get list of signals to read ---
    if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
        ls = unique(in.SignalDatabase.GenericName)';
    elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
        ls = unique(in.SignalDatabase.TactName)';
    else
        ls = [];
    end

    % --- Match signals in MDF file with SignalDatabase ---
    for i = ls
        if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
            locs = strcmpi(in.SignalDatabase.GenericName,i);
        elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
            locs = strcmpi(in.SignalDatabase.TactName,i);
        end

        if ismember('Synonym',in.SignalDatabase.Properties.VariableNames)
            syns = in.SignalDatabase.Synonym(locs)';
        elseif ismember('A2LName',in.SignalDatabase.Properties.VariableNames)
            syns = in.SignalDatabase.A2LName(locs)';
        else
            syns = [];
        end

        if iscell(syns{1}), syns = vertcat(syns{:}); end

        for ii = syns
            if ~isempty(ii{1})
                sig2find = strrep(ii,'.','_');
                loc = find(strcmpi(sigs_copy,sig2find));

                if ~isempty(loc)
                    t = table({sigs.ChannelName{loc(1)}}', ...
                            sigs.ChannelGroupNumber(loc(1))', ...
                            i(1));
                    toRead = [toRead;t];
                end
            end
        end
    end

    % --- Read signals ---
    if ~isempty(toRead)
        toRead.Properties.VariableNames = {'FullName','Channel','GenericName'};
        [toReadSigs,~] = unique(toRead.GenericName);

        raster = {};
        for i = 1:length(toReadSigs)
            idx = find(strcmp(toRead.GenericName,toReadSigs{i}),1);
            data = read(m,toRead.Channel(idx),toRead.FullName{idx});

            % Raster
            raster{end+1,1} = seconds(mean(diff(data.Time)));

            % Resample
            if ~isempty(in.Resample)
                times = seconds(data.Time);
                steps = seconds(times(1):in.Resample:times(end));
                try
                    data = retime(data,steps,'nearest');
                catch
                    data = retime(data,steps);
                end
            end

            % Rename
            data.Properties.VariableNames = toReadSigs(i);

            if isempty(Data)
                Data = data;
            else
                if ~isempty(in.Resample)
                    Data = [Data,data];
                else
                    Data = synchronize(Data,data);
                end
            end
        end

        % Raster table
        RasterRows = cell2table([Data.Properties.VariableNames',raster]);
        RasterRows.Properties.VariableNames = Raster.Properties.VariableNames;
        Raster = [Raster;RasterRows];

        % Used signals
        used = toRead(:,{'GenericName','FullName'});
    end

    % --- Fill missing values ---
    if any(ismissing(Data)) && all(diff(Data.Time) ~= seconds(0))
        Data = fillmissing(Data,'nearest');
    end

end % function


% --- Helper functions ---
function allsigs = removeMdfSuffixes(channelNames)
allsigs = cellstr(channelNames);
allsigs = cellfun(@(allsigs) strsplit(allsigs,'\'),string(allsigs),'UniformOutput', false);
allsigs = cellfun(@(v) v(1), allsigs);
end
