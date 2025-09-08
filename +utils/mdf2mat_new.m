function [ Data, m, sigs, summary, used, Raster, mods ] = mdf2mat_new( varargin )
 
% mdf2mat reads mdf objects (.dat/.mf4) into a matlab timetable
 
% inputs:
    % dat path - REQUIRED -  path of the data file to read inc. file extension (.dat/.mf4) - char. 
         % If this is the only input all signals will be read
    % SignalDatabase - OPTIONAL - database of signals detail generic/ TACT name + potential synonyms and any other information e.g fill method - table
         % If this and the dat path are included only the signals in the signal database will be read
    % Req - OPTIONAL - list of signals requested - cell array of strings
         % If this is included only the requested signals will be read based on the synonyms within the Signal Database
    % m - OPTIONAL - mdf object of the specified mdf file if already read - asam.MDF
         % if this is included the function is not required to created the mdf object
    % Data - OPTIONAL - if the file has been read previously and data extracted this can be input back into the function if extra signals are wanted - timetable
         % if this is included the file will check whether any requested signals are already present and if not will read and sync the requested signals
    % ConvertToTactUnit - OPTIONAL - convert signals read from mdf object to the
         % unit specified by TactUnit in the SignalDatabase
    % LoadSignals - OPTIONAL - logical determining whether to load signals
         % or abort after reading m
    
% outputs 
    % Data - time series data from the mdf file - timetable
    % m - mdf object of the specified mdf file - asam.MDF
    % sigs - list of signals within the file and the corresponding channel number - cell array of strings
    % summary - summary of the signals requested, the signals read and the signals not present - table
    % used - details of the exact signals which have been read from the file for each generic signal
    % Raster - original rates rates of the signals read (before synchronisation)
 
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
 
    % read mdf object
    in.m = mdf(in.datPath);
    
end % if
 
% get list of signals in file
sigs = in.m.channelList;
 
% abort if requested
if ~in.LoadSignals
    m = in.m;
    return
end % if

% create copy
sigs_copy = strrep(sigs.ChannelName,'.','_');
 
% remove excess information - when read via the mdf function the signals
% have a suffix typically separated by \. This needs to be removed in order
% to find a match for the signal name. 
sigs_copy = removeMdfSuffixes(sigs_copy);
 
% sigs_copy = strrep(sigs_copy,'CAN-Monitoring','');
% sigs_copy = strrep(sigs_copy,'ETKC','');
% sigs_copy = strrep(sigs_copy,'XCP','');
% sigs_copy = strrep(sigs_copy,'\FLX Monitoring A:1','');
% sigs_copy = strrep(sigs_copy,'FLX Monitoring','');
% sigs_copy = strrep(sigs_copy,'PT CAN','');
% sigs_copy = strrep(sigs_copy,'PMZ CAN','');
% sigs_copy = strrep(sigs_copy,'CCP:1','');
% sigs_copy = strrep(sigs_copy,'TB_CAN','');
% sigs_copy = strrep(sigs_copy,'\:1','');
% sigs_copy = strrep(sigs_copy,'\ES410','');
% sigs_copy = strrep(sigs_copy,'\ES610','');
% sigs_copy = strrep(sigs_copy,' / AD:1','');
% sigs_copy = strrep(sigs_copy,'\EGS','');
% sigs_copy = strrep(sigs_copy,'\FLX','');
% sigs_copy = strrep(sigs_copy,'\','');
 
% waitbar
% if in.Waitbar
%     mwb = classes.gui.components.MultiWaitbar('ConstructPars',{'Tasks',{{'task1','Loading data...',0}}}); pause(0.01);
% end % if

% predefine raster output
Raster = cell2table(cell(0,2));
Raster.Properties.VariableNames = {'Variable','Raster'};

% predefine the variables to read as empty
toRead = [];
 
% predefine data
Data = in.Data;

% predefine raster rate
raster = [];

if ~isempty(Data)
    nVars = width(Data);
    raster = cell(nVars,1);
    raster(:) = {mean(diff(seconds(Data.Time)))};
end % if
 
% predefine the signals that have been read
if ~isempty(in.SignalDatabase) && isempty(in.Req)
    
    signalsRead(1:height(in.SignalDatabase),1) = {char(0)};
    
elseif ~isempty(in.SignalDatabase) && ~isempty(in.Req)
 
    signalsRead(1:length(in.Req),1) = {char(0)};
    
end % if
 
% if no signal database has been provided
if isempty(in.SignalDatabase)
    
    % reset data
    Data = [];
    
    if isempty(in.Req)
        
        % loop through channels to get data
        for i = 1:numel(in.m.ChannelGroup)
            
            % if there is data in the channel
            if in.m.ChannelGroup(i).DataSize > 0
                
                if in.Waitbar
                    mwb.updateTask('task1','Value',i/numel(in.m.ChannelGroup)); pause(0.01);
                end % if
                
                % read channel data
                data = read(in.m,i,in.m.ChannelNames{i});
                
                % synchronise data
                if isempty(Data)
                    
                    Data = data;
                    
                else
                    
                    Data = synchronize(Data,data);
                    
                end % if
                
                % get raster
                r = [];
                r(1:width(data),:) = seconds(mean(diff(data.Time)));
                raster = [raster;num2cell(r)];
                
            end % if
            
        end % for

    else
        
        % loop through in.Req
        for i = 1:length(in.Req)
            
            if in.Waitbar
                mwb.updateTask('task1','Value',i/length(in.Req)); pause(0.01);
            end % if
            
            % get signal
            signal = in.Req{i};
            signal = strrep(signal,'.','_');
            
            % get location of requested signal
            loc = find(strcmp(sigs_copy,signal));
            
            if isempty(loc)
                
                loc = find(strcmp(sigs.ChannelName,signal));
                
            end % if
            
            % if the signal exists
            if any(loc)
                
                % read channel dat
                data = read(in.m, sigs.ChannelGroupNumber(loc), sigs.ChannelName{loc});
                
            end % if
            
            if isempty(Data)
                
                Data = data;
                
            else
                
                Data = synchronize(Data,data);
                
            end % if
            
            % get raster
            raster{end+1,1} = seconds(mean(diff(data.Time)));
                        
        end % for
        
    end % if
    
    summary = table(Data.Properties.VariableNames');
    summary.Properties.VariableNames = {'Read'};
    used = [];
    
else
    
        if isempty(in.Req)
            
            % get signals to read
            if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
                
                ls = unique(in.SignalDatabase.GenericName)';
                
            elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
                
                ls = unique(in.SignalDatabase.TactName)';
                
            else
                
                ls = [];
                
            end % if
            
        else
            
            % get signals to read
            ls = in.Req;
            
            if size(ls,1) > 1
                
                ls = ls';
                
            end % if
            
        end % if
        
        n = 0;
        w = 0;
        wL = length(ls);
        for i = ls
            
            if in.Waitbar
                w = w + 1;
                mwb.updateTask('task1','Value',w/wL); pause(0.01);
            end % if
            
            % get locations of link
            if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
                
                locs = strcmpi(in.SignalDatabase.GenericName,i);
                
            elseif ismember('TactName',in.SignalDatabase.Properties.VariableNames)
                
                locs = strcmpi(in.SignalDatabase.TactName,i);
                
            end % if
            
            % get possible signal names
            if ismember('GenericName',in.SignalDatabase.Properties.VariableNames)
            
                syns = in.SignalDatabase.Synonym(locs)';
                
            elseif ismember('A2LName',in.SignalDatabase.Properties.VariableNames)
                
                syns = in.SignalDatabase.A2LName(locs)';
                
            else
                
                syns = [];
                
            end % if
            
            if iscell(syns{1})
                
                syns = vertcat(syns{:});
                
            end % if
                
            % loop through links
            for ii = syns
                
                if ~isempty(ii{1})
                    
                    t = [];
                    sig2find = strrep(ii,'.','_');
                    
                    % find if the possible signal is present in the file
                    loc = find(strcmpi(sigs_copy,sig2find));
                    if ~isempty(loc)
                        lenL = length(loc) > 1;
                    end % if
                    
                    % TODO RLEACH add in method which if there is more than one
                    % occurrence of the same signal choses the one with the
                    % correct or preferred raster rate - fix for this issue
                    % below is temporary

                    tempR = zeros(length(loc),1);
                    
                    for iv = 1:length(loc)
                         
                        n = n + 1;
                        signalsRead{n,1} = i{1};

                        % if there is more than one location read a sample of data to get the raster
                        if lenL
                            
                              tempdata = read(in.m, sigs.ChannelGroupNumber(loc(iv)), sigs.ChannelName{loc(iv)},1,10);
                              tempR(iv,1) = mean(diff(seconds(tempdata.Time))); 
                            
                        end % if

                    end % for
                    
                    if ~isempty(loc) && lenL
                        
                       [~,idx] = min(tempR); 
                        
                       t = table({sigs.ChannelName{loc(idx)}}', ...
                            sigs.ChannelGroupNumber(loc(idx))', ...
                            i(1));
                       
                    elseif ~isempty(loc) && ~lenL
                        
                        t = table({sigs.ChannelName{loc(1)}}', ...
                            sigs.ChannelGroupNumber(loc(1))', ...
                            i(1));
                        
                    end % if
                    
                    toRead = [toRead;t];
                        
                end % if
                
            end % for
 
        end % for
        
        signalsRead = unique(signalsRead);
 
        if ~isempty(toRead)
            
            % fix headings
            toRead.Properties.VariableNames = {'FullName','Channel','GenericName'};
            
            % remove any variables if already present in Data
            if ~isempty(Data)
                
                pres = ismember(toRead.GenericName,Data.Properties.VariableNames);
                toRead(pres,:) = [];
                
            end % if
            
            [toReadSigs,ia] = unique(toRead.GenericName);
            
            
            toReadFilt = false(height(toRead),1);

            % loop through channels
            n1 = 0;
            for i = length(toReadSigs):-1:1

                % get all the possible synonyms present
                toReadSyns = find(strcmp(toRead.GenericName,toReadSigs{i}));
                
                % reset data
                data = [];
                ii = 0;
                
                while isempty(data) && ii <= length(toReadSyns)
                    
                    ii = ii + 1;
                    
                    try
     
                        % read channel dat
                        data = read(in.m, toRead.Channel(toReadSyns(ii)), toRead.FullName{toReadSyns(ii)});
                        if ~isempty(data)
                            toReadFilt(toReadSyns(ii)) = true;
                        end % if
                        
                        % check file stiching (relevant for trigger events
                        % that have been stiched together into one file
                        backTime = diff(seconds(data.Time)) < 0;
                        stichErr = any(backTime);
                        
                        % if a stich error is identified
                        if stichErr
                            
                            % get error locations
                            loc = find(backTime);
                            
                            % loop through errors
                            for iii = 1:length(loc)
                                
                                % get time
                                eTime = data.Time(loc(iii));
                                
                                % get any time stamps after error detected
                                errLoc = find(data.Time < eTime);
                                
                                % remove any locations less than the
                                % original idx
                                rLoc = errLoc < loc(iii);
                                errLoc = errLoc(~rLoc);
                                
                                % delete stiching overlap - results in data
                                % loss
                                data(errLoc,:) = [];
                                
                            end % for
                            
                        end % if
                        
                        
                        if in.ConvertToTactUnit
                            
                            channelGroup = toRead.Channel(toReadSyns(ii));
                            fullName = toRead.FullName{toReadSyns(ii)};

                            % Map mdf unit to tact unit
                            channelIdx = contains({in.m.ChannelGroup(channelGroup).Channel.Name},fullName);
                            channelUnit = in.m.ChannelGroup(channelGroup).Channel(channelIdx).Unit;
                            mdfTactUnit = mdfUnitToTactUnit(channelUnit);
  
                            fullNameNoDevice = strsplit(fullName,'\');
                            fullNameNoDevice = fullNameNoDevice{1};

                            if ismember('A2LName',in.SignalDatabase.Properties.VariableNames)
                                sigIdx = strcmp(in.SignalDatabase.A2LName,fullNameNoDevice);
                            elseif ismember('Synonym',in.SignalDatabase.Properties.VariableNames)
                                sigIdx = strcmp(in.SignalDatabase.Synonym,fullNameNoDevice);
                            end % if
                            
                            if ismember('TactUnit',in.SignalDatabase.Properties.VariableNames)
                                targetTactUnit = in.SignalDatabase.TactUnit{sigIdx};
                            elseif ismember('Unit',in.SignalDatabase.Properties.VariableNames)
                                targetTactUnit = in.SignalDatabase.Unit{sigIdx};
                            end % if
                            
                            [data.(data.Properties.VariableNames{1}),convert] = convertTactUnit(data.(data.Properties.VariableNames{1}),mdfTactUnit,targetTactUnit,fullName);
                            
                            if convert
                                
                                mods = [mods; ...
                                    cell2table({fullNameNoDevice,mdfTactUnit,targetTactUnit}, ...
                                    'VariableNames',{'Signal','From','To'})];
                            end
                            
                            
                        end
                        
                    catch
                        
                        
                    end
                    
                    if ~isempty(data)
                        
                        % get raster
                        raster{end+1,1} = seconds(mean(diff(data.Time)));
                        
                        % resample if requested
                        if ~isempty(in.Resample)
                            
                            n1 = n1 + 1;
                            if n1 == 1
                                
                                times = seconds(data.Time);
                                steps = seconds(times(1):in.Resample:times(end));
                                
                            end
                            
                            try
                                data = retime(data,steps,'nearest');
                            catch
                                data = retime(data,steps);
                            end 
                            
                        end % if
                        
                        % correct column name
                        data.Properties.VariableNames = toReadSigs(i);
                        
                        % add description
                        signame = strsplit(toRead.FullName{toReadSyns(ii)},'\');
                        data.Properties.VariableDescriptions = signame(1);
                        
                        if isempty(Data)
                            
                            Data = data;
                            
                        else
                            
                            if ~isempty(in.Resample)
                                
                                Data = [Data,data];
                                
                            else
                                
                                Data = synchronize(Data,data);
                                
                            end % if
                            
                        end % if
  
                        break
                        
                    end % if
                    
                end % while
        
            end % for
            
        end % if
        
        % create summary table
        if ~isempty(in.Req)
            
            notRead = ~ismember(in.Req,signalsRead);
            notRead = in.Req(notRead);
            
            if length(notRead) < length(in.Req)
                
                notRead(end+1:length(in.Req),1) = {char(0)};
                
            end
            
            if length(signalsRead) < length(in.Req)
                
                signalsRead(end+1:length(in.Req),1) = {char(0)};
                
            end % if
            
            summary = table(in.Req,signalsRead,notRead);
            summary.Properties.VariableNames = {'Requested','Read','NotRead'};
            
        else
            
            summary = table(signalsRead);
            summary.Properties.VariableNames = {'Read'};
            
        end % if
        
        % get the signals used
        if exist('toReadFilt','var')
            
            used = toRead(toReadFilt,{'GenericName','FullName'});
            
        else
            
            used = [];
            
        end % if
        
end % if

% create raster rate table
if ~isempty(raster)
    RasterRows = cell2table([Data.Properties.VariableNames',raster]);
    RasterRows.Properties.VariableNames = Raster.Properties.VariableNames;
    Raster = [Raster;RasterRows];
end % if

% if there are missing values
if any(ismissing(Data))
    
    % fillmissing values
    if all(diff(Data.Time) ~= seconds(0))
        
        Data = fillmissing(Data,'nearest');
        
    end % if
    
end % if
 
% resample Data
% if ~isempty(in.Resample)
%     
%     times = seconds(Data.Time);
%     steps = seconds(times(1):0.01:times(end));
%     Data2 = retime(Data,steps,'previous');
%     
%     % fillmissing values
%     if all(diff(Data2.Time) ~= seconds(0))
%         
%         Data2 = fillmissing(Data2,'nearest');
%         
%     end % if
%     
%     Data = Data2;
%  
% end % if
 
% get the m file
m = in.m;

% close waitbar
% if in.Waitbar
%     mwb.delete;
% end % if

end % mdfSQT

function [allsigs] = removeMdfSuffixes(channelNames)

% Removes suffixes from the end of mdf channel names
% e.g. /ETK, /CAN, ETC.

allsigs = cellstr(channelNames);
allsigs = cellfun(@(allsigs) strsplit(allsigs,'\'),string(allsigs),'UniformOutput', false);
allsigs = cellfun(@(v) v(1), allsigs);

end

function tactUnit = mdfUnitToTactUnit(mdfUnit)
%MDFUNIT2TACTUNIT Summary of this function goes here
%   Detailed explanation goes here

if isempty(mdfUnit)
    mdfUnit = '-';
end

% NOTE: Do not pre-process these units for easier matching. Best if they're
% exact matches so the source can be correctly identified.
switch mdfUnit
    case {'[%]','%','perc','Perc'}
        tactUnit = '%';
        
    case {'[Nm]','Nm','nm'}
        tactUnit = 'nm';
        
    case {'[°C]','°C','[degree Celsius]','degree Celsius','[degC]','degC','[degc]','degc','deg. C','Deg. C'}
        tactUnit = 'degc';
        
    case {'[°C/s]','°C/s'}
        tactUnit = 'degc-1';
        
    case {'[bar]','bar','[Bar]','Bar'}
        tactUnit = 'bar';
        
    case {'[mbar]','mbar'}
        tactUnit = 'mbar';
        
    case {'[Pa]','Pa'}
        tactUnit = 'pa';
        
    case {'[hPa]','hPa'}
        tactUnit = 'hpa';
        
    case {'[U/min]','U/min','[1/min]','1/min','[RPM]','RPM','[rpm]','rpm','Shaft Speed in RPM'}
        tactUnit = 'rpm';
        
    case {'[U/(min*s)]','U/(min*s)','rpm/s','Rpm/s','RPM/s'}
        tactUnit = 'rpms-1';
        
    case {'g','G','[g]','[G]'}
        tactUnit = 'g';
        
    case {'[-]','-','','gear','Gear','1'}
        tactUnit = 'u[1]';
        
    case {'[s]','s'}
        tactUnit = 's';
        
    case {'[m_s2]','m_s2','[m/s2]','m/s2','[m/s^2]','m/s^2','[1/s^2]','1/s^2','m_s_s','m/s/s'}
        tactUnit = 'ms-2';
        
    case {'[ms]','ms'}
        tactUnit = 'ms';
        
    case {'[km/h]','km/h','[kph]','kph'}
        tactUnit = 'kph';
        
    case {'[m/h]','m/h','[mph]','mph'}
        tactUnit = 'kph';
        
    case {'[VER]','VER','[ver]','ver'}
        tactUnit = 'ver';
        
    case {'[Volt]','Volt','[V]','V'}
        tactUnit = 'v';
        
    case {'[W]','W'}
        tactUnit = 'w';
        
    case {'[kW]','kW'}
        tactUnit = 'kw';
        
    case {'[kg]','kg'}
        tactUnit = 'kg';
        
    otherwise
        fprintf('Unit "%s" not found.\n',mdfUnit);
        tactUnit = 'u[1]';     
end


end


function [dataOut,convert] = convertTactUnit(dataIn,unitIn,unitOut,fullName)
%UNTITLED Summary of this function goes here
%   Detailed explanation goes here


if strcmp(unitIn,unitOut)
    dataOut = dataIn;
    convert = false;
    return
end

% Generate conversion name for switch/case
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
        fprintf('"%s" - ',fullName);
        fprintf('Could not convert "%s". Passing original value.\n',cnvName);
        dataOut = dataIn;
        convert = false;
        
end


end

