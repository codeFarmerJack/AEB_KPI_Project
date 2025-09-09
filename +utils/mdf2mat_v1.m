function [ Data, m, sigs, summary, used, Raster, mods ] = mdf2mat_v1( varargin )
    % mdf2mat reads mdf objects (.dat/.mf4) into a matlab timetable
    %
    % Inputs:
    %   datPath          - REQUIRED: path of the data file to read (.dat/.mf4)
    %   SignalDatabase   - OPTIONAL: table of signals with Generic/Tact name, synonyms, units
    %   Req              - OPTIONAL: cell array of requested signals
    %   m                - OPTIONAL: asam.MDF object if already read
    %   Data             - OPTIONAL: timetable of previously read signals
    %   Resample         - OPTIONAL: resampling step in seconds
    %   ConvertToTactUnit- OPTIONAL: convert units to Tact standard (default: true)
    %   LoadSignals      - OPTIONAL: logical, load signals or just return MDF object
    %   Waitbar          - OPTIONAL: logical, show progress bar
    %
    % Outputs:
    %   Data     - timetable of signals
    %   m        - asam.MDF object
    %   sigs     - list of signals and channel numbers
    %   summary  - table summarizing requested, read, and missing signals
    %   used     - details of exact signals read
    %   Raster   - table of original raster rates
    %   mods     - table of unit conversions applied

    % Parse inputs
    p = inputParser;
    addRequired(p,'datPath',@(x)ischar(x) && contains(x,{'.dat','.mf4'}));
    addParameter(p,'SignalDatabase',[],@(x)istable(x));
    addParameter(p,'Req',[],@(x)iscell(x) && all(cellfun(@ischar,x)));
    addParameter(p,'m',[],@(x)isa(x,'asam.MDF'));
    addParameter(p,'Data',[],@(x)isa(x,'timetable'));
    addParameter(p,'Resample',[],@(x)isa(x,'double'));
    addParameter(p,'ConvertToTactUnit',true,@(x)isa(x,'logical'));
    addParameter(p,'LoadSignals',true,@(x)isa(x,'logical'));
    addParameter(p,'Waitbar',false,@(x)isa(x,'logical'));
    parse(p,varargin{:});
    in = p.Results;

    Data = [];
    summary = [];
    used = [];
    Raster = [];
    mods = [];

    if isempty(in.m) || ~isvalid(in.m)
        in.m = mdf(in.datPath);
    end

    % get list of signals in file
    sigs = in.m.channelList;

    % abort if requested
    if ~in.LoadSignals
        m = in.m;
        return
    end

    % clean channel names
    sigs_copy = strrep(sigs.ChannelName,'.','_');
    sigs_copy = removeMdfSuffixes(sigs_copy);

    % initialize outputs
    Raster = cell2table(cell(0,2));
    Raster.Properties.VariableNames = {'Variable','Raster'};
    toRead = [];
    Data = in.Data;
    raster = [];

    if ~isempty(Data)
        nVars = width(Data);
        raster = cell(nVars,1);
        raster(:) = {mean(diff(seconds(Data.Time)))};
    end

    % track signals read
    if ~isempty(in.SignalDatabase) && isempty(in.Req)
        signalsRead(1:height(in.SignalDatabase),1) = {char(0)};
    elseif ~isempty(in.SignalDatabase) && ~isempty(in.Req)
        signalsRead(1:length(in.Req),1) = {char(0)};
    end

    % ==============================================================
    % CASE 1: No SignalDatabase → load all or requested only
    % ==============================================================

    if isempty(in.SignalDatabase)
        Data = [];

        if isempty(in.Req)
            % load all signals
            for i = 1:numel(in.m.ChannelGroup)
                if in.m.ChannelGroup(i).DataSize > 0
                    data = read(in.m,i,in.m.ChannelNames{i});
                    if isempty(Data)
                        Data = data;
                    else
                        Data = synchronize(Data,data);
                    end
                    r(1:width(data),:) = seconds(mean(diff(data.Time)));
                    raster = [raster;num2cell(r)];
                end
            end
        else
            % load only requested signals
            for i = 1:length(in.Req)
                signal = strrep(in.Req{i},'.','_');
                loc = find(strcmp(sigs_copy,signal));
                if isempty(loc)
                    loc = find(strcmp(sigs.ChannelName,signal));
                end
                if any(loc)
                    data = read(in.m, sigs.ChannelGroupNumber(loc), sigs.ChannelName{loc});
                    if isempty(Data)
                        Data = data;
                    else
                        Data = synchronize(Data,data);
                    end
                    raster{end+1,1} = seconds(mean(diff(data.Time)));
                end
            end
        end

        summary = table(Data.Properties.VariableNames');
        summary.Properties.VariableNames = {'Read'};
        used = [];

    else
    % ==============================================================
    % CASE 2: With SignalDatabase → match GenericName / Synonyms
    % ==============================================================

        if isempty(in.Req)
            if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
                ls = unique(in.SignalDatabase.GenericName)';
            elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
                ls = unique(in.SignalDatabase.TactName)';
            else
                ls = [];
            end
        else
            ls = in.Req(:)';
        end

        n = 0; toRead = [];
        for i = ls
            % find synonyms
            if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
                locs = strcmpi(in.SignalDatabase.GenericName,i);
                syns = in.SignalDatabase.Synonym(locs)';
            elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
                locs = strcmpi(in.SignalDatabase.TactName,i);
                syns = in.SignalDatabase.A2LName(locs)';
            else
                syns = [];
            end
            if iscell(syns{1}), syns = vertcat(syns{:}); end

            for ii = syns
                if ~isempty(ii{1})
                    sig2find = strrep(ii,'.','_');
                    loc = find(strcmpi(sigs_copy,sig2find));
                    if isempty(loc), continue; end
                    n = n + 1;
                    signalsRead{n,1} = i{1};
                    t = table({sigs.ChannelName{loc(1)}}', ...
                            sigs.ChannelGroupNumber(loc(1))', ...
                            i(1));
                    toRead = [toRead;t];
                end
            end
        end

        signalsRead = unique(signalsRead);

        if ~isempty(toRead)
            toRead.Properties.VariableNames = {'FullName','Channel','GenericName'};
            if ~isempty(Data)
                pres = ismember(toRead.GenericName,Data.Properties.VariableNames);
                toRead(pres,:) = [];
            end

            [toReadSigs,ia] = unique(toRead.GenericName);
            toReadFilt = false(height(toRead),1);

            for i = length(toReadSigs):-1:1
                toReadSyns = find(strcmp(toRead.GenericName,toReadSigs{i}));
                data = []; ii = 0;

                while isempty(data) && ii <= length(toReadSyns)
                    ii = ii + 1;
                    try
                        data = read(in.m, toRead.Channel(toReadSyns(ii)), toRead.FullName{toReadSyns(ii)});
                        if ~isempty(data)
                            toReadFilt(toReadSyns(ii)) = true;

                            if in.ConvertToTactUnit
                                channelGroup = toRead.Channel(toReadSyns(ii));
                                fullName = toRead.FullName{toReadSyns(ii)};
                                channelIdx = contains({in.m.ChannelGroup(channelGroup).Channel.Name},fullName);
                                channelUnit = in.m.ChannelGroup(channelGroup).Channel(channelIdx).Unit;
                                mdfTactUnit = mdfUnitToTactUnit(channelUnit);

                                fullNameNoDevice = strsplit(fullName,'\');
                                fullNameNoDevice = fullNameNoDevice{1};

                                if ismember('A2LName',in.SignalDatabase.Properties.VariableNames)
                                    sigIdx = strcmp(in.SignalDatabase.A2LName,fullNameNoDevice);
                                elseif ismember('Synonym',in.SignalDatabase.Properties.VariableNames)
                                    sigIdx = strcmp(in.SignalDatabase.Synonym,fullNameNoDevice);
                                end
                                if ismember('TactUnit',in.SignalDatabase.Properties.VariableNames)
                                    targetTactUnit = in.SignalDatabase.TactUnit{sigIdx};
                                elseif ismember('Unit',in.SignalDatabase.Properties.VariableNames)
                                    targetTactUnit = in.SignalDatabase.Unit{sigIdx};
                                end

                                [data.(data.Properties.VariableNames{1}),convert] = ...
                                    convertTactUnit(data.(data.Properties.VariableNames{1}), ...
                                    mdfTactUnit,targetTactUnit,fullName);
                                if convert
                                    mods = [mods; ...
                                        cell2table({fullNameNoDevice,mdfTactUnit,targetTactUnit}, ...
                                        'VariableNames',{'Signal','From','To'})];
                                end
                            end
                        end
                    catch
                    end

                    if ~isempty(data)
                        raster{end+1,1} = seconds(mean(diff(data.Time)));
                        if ~isempty(in.Resample)
                            times = seconds(data.Time);
                            steps = seconds(times(1):in.Resample:times(end));
                            try
                                data = retime(data,steps,'nearest');
                            catch
                                data = retime(data,steps);
                            end
                        end
                        data.Properties.VariableNames = toReadSigs(i);
                        signame = strsplit(toRead.FullName{toReadSyns(ii)},'\');
                        data.Properties.VariableDescriptions = signame(1);
                        if isempty(Data)
                            Data = data;
                        else
                            if ~isempty(in.Resample)
                                Data = [Data,data];
                            else
                                Data = synchronize(Data,data);
                            end
                        end
                        break
                    end
                end
            end
        end

        if ~isempty(in.Req)
            notRead = ~ismember(in.Req,signalsRead);
            notRead = in.Req(notRead);
            if length(notRead) < length(in.Req)
                notRead(end+1:length(in.Req),1) = {char(0)};
            end
            if length(signalsRead) < length(in.Req)
                signalsRead(end+1:length(in.Req),1) = {char(0)};
            end
            summary = table(in.Req,signalsRead,notRead);
            summary.Properties.VariableNames = {'Requested','Read','NotRead'};
        else
            summary = table(signalsRead);
            summary.Properties.VariableNames = {'Read'};
        end

        if exist('toReadFilt','var')
            used = toRead(toReadFilt,{'GenericName','FullName'});
        else
            used = [];
        end
    end

    % create raster rate table
    if ~isempty(raster)
        RasterRows = cell2table([Data.Properties.VariableNames',raster]);
        RasterRows.Properties.VariableNames = Raster.Properties.VariableNames;
        Raster = [Raster;RasterRows];
    end

    % fill missing values
    if any(ismissing(Data))
        if all(diff(Data.Time) ~= seconds(0))
            Data = fillmissing(Data,'nearest');
        end
    end

    m = in.m;
end % mdf2mat_new

% ==============================================================
% Helper functions
% ==============================================================

function [allsigs] = removeMdfSuffixes(channelNames)
    allsigs = cellstr(channelNames);
    allsigs = cellfun(@(allsigs) strsplit(allsigs,'\'),string(allsigs),'UniformOutput', false);
    allsigs = cellfun(@(v) v(1), allsigs);
end

function tactUnit = mdfUnitToTactUnit(mdfUnit)
    if isempty(mdfUnit), mdfUnit = '-'; end
    switch mdfUnit
        case {'[%]','%','perc','Perc'}, tactUnit = '%';
        case {'[Nm]','Nm','nm'}, tactUnit = 'nm';
        case {'[°C]','°C','[degree Celsius]','degree Celsius','[degC]','degC','[degc]','degc','deg. C','Deg. C'}, tactUnit = 'degc';
        case {'[°C/s]','°C/s'}, tactUnit = 'degc-1';
        case {'[bar]','bar','[Bar]','Bar'}, tactUnit = 'bar';
        case {'[mbar]','mbar'}, tactUnit = 'mbar';
        case {'[Pa]','Pa'}, tactUnit = 'pa';
        case {'[hPa]','hPa'}, tactUnit = 'hpa';
        case {'[U/min]','U/min','[1/min]','1/min','[RPM]','RPM','[rpm]','rpm'}, tactUnit = 'rpm';
        case {'[U/(min*s)]','U/(min*s)','rpm/s','Rpm/s','RPM/s'}, tactUnit = 'rpms-1';
        case {'g','G','[g]','[G]'}, tactUnit = 'g';
        case {'[-]','-','','gear','Gear','1'}, tactUnit = 'u[1]';
        case {'[s]','s'}, tactUnit = 's';
        case {'[m_s2]','m_s2','[m/s2]','m/s2','[m/s^2]','m/s^2','[1/s^2]','1/s^2','m_s_s','m/s/s'}, tactUnit = 'ms-2';
        case {'[ms]','ms'}, tactUnit = 'ms';
        case {'[km/h]','km/h','[kph]','kph'}, tactUnit = 'kph';
        case {'[m/h]','m/h','[mph]','mph'}, tactUnit = 'kph';
        case {'[Volt]','Volt','[V]','V'}, tactUnit = 'v';
        case {'[W]','W'}, tactUnit = 'w';
        case {'[kW]','kW'}, tactUnit = 'kw';
        case {'[kg]','kg'}, tactUnit = 'kg';
        otherwise, fprintf('Unit "%s" not found.\n',mdfUnit); tactUnit = 'u[1]';
    end
end % mdfUnitToTactUnit

function [dataOut,convert] = convertTactUnit(dataIn,unitIn,unitOut,fullName)
    if strcmp(unitIn,unitOut)
        dataOut = dataIn; convert = false; return
    end
    cnvName = sprintf('%s>>%s',unitIn,unitOut);
    convert = true;
    switch cnvName
        case 'ms-2>>g'
            dataOut = dataIn / config.Math.G;
        case {'mbar>>bar','hpa>>bar','ms>>s'}
            dataOut = dataIn / 1000;
        case {'bar>>mbar','s>>ms'}
            dataOut = dataIn * 1000;
        otherwise
            fprintf('"%s" - Could not convert "%s". Passing original value.\n',fullName,cnvName);
            dataOut = dataIn; convert = false;
    end
end % convertTactUnit
