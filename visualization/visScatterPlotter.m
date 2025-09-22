function visScatterPlotter(obj, graphIndex)
% visScatterPlotter - Generates scatter plot for a specific graph index
% Inputs:
%   obj        - Visualizer object with graphSpec, lineColors, calibratables, pathToCsv
%   graphIndex - Row index in graphSpec to plot

    % --- persistent map of figures ---
    persistent figs firstRows lastRows titleIdx

    graphSpec        = obj.graphSpec;
    lineColors       = obj.lineColors;
    markerShapes     = obj.markerShapes;
    calibratables    = obj.calibratables;
    pathToCsv        = obj.pathToCsv;
    pathToKpiSchema  = obj.pathToKpiSchema;

    %% --- Setup group information once ---
    if isempty(titleIdx)
        [firstRows, lastRows, titleIdx] = initGroupInfo(graphSpec);
    end

    %% --- Load variable names and units from JSON schema ---
    [varName, displayNames] = loadSchemaVars(pathToKpiSchema);

    originpath = pwd;
    cd(pathToCsv);

    files = dir('*.csv');
    N = length(files);
    if N == 0
        warning('No CSV files found in %s. Skipping plot.', pathToCsv);
        cd(originpath);
        return;
    end

    calibratables = applyCalibrations(calibratables);
    
    %% --- Select variables for this plot ---
    xVar        = char(graphSpec.Reference(1));
    yVar        = char(graphSpec.Reference(graphIndex));
    xLabel      = char(graphSpec.Axis_Name(1));
    plotEnabled = strtrim(string(graphSpec.plotEnabled(graphIndex)));
    fprintf('Graph %d plotEnabled = %s\n', graphIndex, plotEnabled); % debug

    % Skip plotting if plotEnabled is false or NA
    if ~strcmpi(plotEnabled, "false") && ~strcmpi(plotEnabled, "NA")

        % Group info
        groupId    = titleIdx(graphIndex);
        groupRows  = find(titleIdx == groupId);
        rowInGroup = find(groupRows == graphIndex);   
        firstRow   = firstRows(groupId);
        lastRow    = lastRows(groupId);
        isFirst    = (graphIndex == firstRow);
        isLast     = (graphIndex == lastRow);

        % --- persistent figure handling ---
        titleStr = char(graphSpec.Title(graphIndex));
        titleKey = matlab.lang.makeValidName(titleStr);  % safe key for struct field
        if isFirst
            figs.(titleKey) = figure; 
            hold on;
            set(figs.(titleKey), 'Position', [10 10 900 600]);
            % Set axis limits
            xlim([graphSpec.Min_Axis_value(1), graphSpec.Max_Axis_value(1)]);
            ylim([graphSpec.Min_Axis_value(firstRow), graphSpec.Max_Axis_value(firstRow)]);
            xlabel(strrep(xLabel, '_', '\_'), 'Interpreter', 'none');
            yLabel = char(graphSpec.Axis_Name(firstRow));
            ylabel(strrep(yLabel, '_', '\_'), 'Interpreter', 'none');
            title(titleStr, 'Interpreter','none');
        end

        fig = figs.(titleKey);
        figure(fig); % bring current

        %% --- Process all CSV files ---
        for i = 1:N
            % Load the i-th csv file
            filename = files(i).name;
            data = safeReadCsv(filename);

            % --- Resolve X and Y column indices robustly (case-insensitive) ---
            [xColIdx, yColIdx] = resolveXYColumns(xVar, yVar, varName, displayNames, data, filename);
            if isempty(xColIdx) || isempty(yColIdx)
                continue;   % skip this file if columns not found
            end

            % Filter the rows to plot based on plotEnabled
            filtIdx = resolveFilter(plotEnabled, data, filename);
            if isempty(filtIdx)
                continue;   % skip this file
            end

            % Extract legends from the table graphSpec
            legendName = string(graphSpec.Legend(graphIndex));
            legendName = char(legendName);  % ensure char for plot

            % --- Force numeric extraction ---
            x = table2array(data(filtIdx, xColIdx));
            y = table2array(data(filtIdx, yColIdx));

            % --- Marker + Color selection ---
            [markerStyle, thisColor] = selectMarkerAndColor(markerShapes, lineColors, groupRows, rowInGroup);

            % Check whether to connect points 
            connectFlag = resolveConnectFlag(graphSpec.ConnectPoints(graphIndex));

            if connectFlag
                plot(x, y, 'LineStyle','-',   'Marker', markerStyle, ...
                    'DisplayName', legendName, 'Color', thisColor);
            else
                plot(x, y, 'LineStyle','none','Marker', markerStyle, ...
                    'DisplayName', legendName, 'Color', thisColor);
            end

        end % for i = 1:N

        %% --- Add Calibration limits ---
        addCalibrationLimit(graphSpec.Calibration_Lim(graphIndex), calibratables);

        % --- Finalize if last in group ---
        if isLast
            legend('Interpreter', 'none', 'Location', 'northeast', ...
                   'FontSize', 8, 'Orientation', 'vertical');
            grid on;
            set(gca, 'xminorgrid', 'on', 'yminorgrid', 'on');
            fig_name = strcat('Fig_', num2str(firstRow-1, '%02d'), ' - ', ...
                             char(graphSpec.Legend(graphIndex)));
            print(fig, fig_name, '-dpng', '-r400');
        end
    end % End of plotEnabled check

    cd(originpath);
end


%% =============== Helper Functions ===============

function [firstRows, lastRows, titleIdx] = initGroupInfo(graphSpec)
    [uniqueTitles, ~, titleIdx] = unique(graphSpec.Title);
    groupRows = arrayfun(@(g) find(titleIdx==g), 1:numel(uniqueTitles), ...
                         'UniformOutput', false);
    firstRows = cellfun(@min, groupRows);
    lastRows  = cellfun(@max, groupRows);
end

function [varName, displayNames] = loadSchemaVars(pathToKpiSchema)
    if isempty(pathToKpiSchema)
        error('JSON schema file path required.');
    end

    fid = fopen(pathToKpiSchema, 'r');
    if fid == -1
        error('Failed to open JSON file: %s', pathToKpiSchema);
    end
    raw = fread(fid, inf, 'uint8=>char')';
    fclose(fid);

    schema = jsondecode(raw);

    % Handle struct vs. cell array
    vars = schema.variables;
    if iscell(vars)
        vars = [vars{:}];
    end

    % Collect variable names
    varName = {vars.name};

    % Collect display names
    displayNames = cell(size(varName));
    for i = 1:numel(vars)
        unit = '';
        if isfield(vars(i), 'unit') && ~isempty(vars(i).unit)
            unit = vars(i).unit;
        end
        if isempty(unit)
            displayNames{i} = varName{i};
        else
            displayNames{i} = sprintf('%s [%s]', varName{i}, unit);
        end
    end
end

function data = safeReadCsv(filename)
    opts = detectImportOptions(filename, 'VariableNamesLine', 1, ...
                'Delimiter', ',', 'PreserveVariableNames', true);
    try
        data = readtable(filename, opts);
    catch e
        warning('Failed to read %s: %s. Skipping file.', filename, e.message);
        data = [];
    end
end

function [xColIdx, yColIdx] = resolveXYColumns(xVar, yVar, varName, displayNames, data, filename)
    % resolveXYColumns - Resolve X and Y column indices robustly (case-insensitive)
    %
    % Inputs:
    %   xVar, yVar     - char: variable names from graphSpec
    %   varName        - cellstr: raw JSON variable names
    %   displayNames   - cellstr: display names with units
    %   data           - table: CSV data
    %   filename       - char: file name (for warnings)
    %
    % Outputs:
    %   xColIdx, yColIdx - numeric indices of X and Y columns in data.Properties.VariableNames
    %
    % Returns empty indices if not found.

    % --- Match X candidate ---
    xCandidate = xVar;
    idxX = find(strcmpi(xVar, varName), 1);
    if ~isempty(idxX)
        xCandidate = displayNames{idxX};
    end

    % --- Match Y candidate ---
    yCandidate = yVar;
    idxY = find(strcmpi(yVar, varName), 1);
    if ~isempty(idxY)
        yCandidate = displayNames{idxY};
    end

    % --- Find column indices in data ---
    xColIdx = find(strcmpi(xCandidate, data.Properties.VariableNames), 1);
    if isempty(xColIdx)
        xColIdx = find(strcmpi(xVar, data.Properties.VariableNames), 1);
    end

    yColIdx = find(strcmpi(yCandidate, data.Properties.VariableNames), 1);
    if isempty(yColIdx)
        yColIdx = find(strcmpi(yVar, data.Properties.VariableNames), 1);
    end

    % --- Check if found ---
    if isempty(xColIdx) || isempty(yColIdx)
        warning('X (%s) or Y (%s) variable not found in %s. Skipping file.', ...
                xVar, yVar, filename);
        xColIdx = [];
        yColIdx = [];
    end
end

function filtIdx = resolveFilter(plotEnabled, data, filename)
    % resolveFilter - Determine row indices based on plotEnabled condition
    %
    % Inputs:
    %   plotEnabled - string: "true", "false", "NA", or a column name
    %   data        - table: CSV data
    %   filename    - char: name of the file (for warnings)
    %
    % Output:
    %   filtIdx     - numeric indices of rows to plot

    if strcmpi(plotEnabled, "true")
        filtIdx = 1:height(data);

    elseif ismember(plotEnabled, data.Properties.VariableNames)
        condCol = data.(plotEnabled);

        if isnumeric(condCol)
            condCol = condCol ~= 0;
        elseif isstring(condCol) || iscellstr(condCol)
            condCol = strcmpi(condCol, "true");
        elseif ~islogical(condCol)
            warning('Unexpected type in column "%s". Defaulting to all rows.', plotEnabled);
            condCol = true(height(data),1);
        end

        filtIdx = find(condCol);

        if isempty(filtIdx)
            warning('Condition "%s" in %s has no true rows. Skipping.', ...
                    plotEnabled, filename);
            filtIdx = [];   % return empty to signal skip
        end

    else
        warning('Condition column "%s" not found in %s. Using all rows.', ...
                plotEnabled, filename);
        filtIdx = 1:height(data);
    end
end

function [markerStyle, thisColor] = selectMarkerAndColor(markerShapes, lineColors, groupRows, rowInGroup)
    % selectMarkerAndColor - Pick marker style and color for a scatter plot
    %
    % Inputs:
    %   markerShapes - table/struct with a field 'Shapes'
    %   lineColors   - table or numeric array [N x 3]
    %   groupRows    - indices of rows belonging to this group
    %   rowInGroup   - current row's index within groupRows
    %
    % Outputs:
    %   markerStyle  - char: marker symbol for plotting
    %   thisColor    - 1x3 numeric RGB row vector
    
    % Ensure lineColors is numeric
    if istable(lineColors)
        lineColors = table2array(lineColors);
    end

    if numel(groupRows) == 1
        % Only one scatter → always use first marker & color
        markerStyle = markerShapes.Shapes{1};
        thisColor   = lineColors(1,:);
    else
        % Multiple scatters → cycle by rowInGroup
        mIdx = mod(rowInGroup-1, height(markerShapes)) + 1;
        cIdx = mod(rowInGroup-1, size(lineColors,1)) + 1;

        markerStyle = markerShapes.Shapes{mIdx};
        thisColor   = lineColors(cIdx,:);
    end

    % Convert to char if string
    if isstring(markerStyle)
        markerStyle = char(markerStyle);
    end

    % Ensure lineColors is numeric
    if istable(lineColors)
        lineColors = table2array(lineColors);
    end
end

function connectFlag = resolveConnectFlag(cpRaw)
    % resolveConnectFlag - Interpret ConnectPoints value as a logical flag
    %
    % Inputs:
    %   cpRaw - raw value from graphSpec.ConnectPoints (logical, numeric, or string)
    %
    % Output:
    %   connectFlag - boolean indicating whether to connect points

    cpStr = lower(strtrim(string(cpRaw)));

    if islogical(cpRaw)
        connectFlag = cpRaw;
    elseif isnumeric(cpRaw)
        connectFlag = cpRaw ~= 0;
    else
        connectFlag = ismember(cpStr, ["true","1","yes","y"]);
    end
end

function calibratables = applyCalibrations(calibratables)
    if isfield(calibratables, 'PedalPosProIncrease_Th')
        calibratables.PedalPosProIncrease_Th{2, :} = ...
            calibratables.PedalPosProIncrease_Th{2, :} * 100;
    end
end

function addCalibrationLimit(calLimit, calibratables)
    calLimit = char(calLimit);
    if ~strcmp(calLimit, 'none')
        if isfield(calibratables, calLimit)
            lim_data   = calibratables.(calLimit);
            lim_data_x = lim_data{1,:};
            lim_data_y = lim_data{2,:};
            plot(lim_data_x, lim_data_y, 'DisplayName', calLimit);
        else
            warning('Calibration limit "%s" not found in calibratables.', calLimit);
        end
    end
end