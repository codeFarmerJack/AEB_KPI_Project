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

    % Init grouping info once
    if isempty(titleIdx)
        [uniqueTitles, ~, titleIdx] = unique(graphSpec.Title);
        groupRows = arrayfun(@(g) find(titleIdx==g), 1:numel(uniqueTitles), ...
                             'UniformOutput', false);
        firstRows = cellfun(@min, groupRows);
        lastRows  = cellfun(@max, groupRows);
    end

    % Read JSON schema to get variable names and units
    if isempty(pathToKpiSchema)
        error('JSON schema file path required.');
    end
    fid = fopen(pathToKpiSchema, 'r');
    if fid == -1
        error('Failed to open JSON file: %s', pathToKpiSchema);
    end
    raw = fread(fid, inf, 'uint8=>char')';
    fclose(fid);
    schema  = jsondecode(raw);
    vars    = schema.variables;
    varName = {vars.name};
    varUnit = cell(size(varName));
    for i = 1:length(vars)
        varUnit{i} = '';
        if isfield(vars(i), 'unit') && ~isempty(vars(i).unit)
            varUnit{i} = vars(i).unit;
        end
    end
    displayNames = cell(size(varName));
    for i = 1:length(varName)
        if isempty(varUnit{i})
            displayNames{i} = varName{i};
        else
            displayNames{i} = sprintf('%s [%s]', varName{i}, varUnit{i});
        end
    end

    originpath = pwd;
    cd(pathToCsv);

    files = dir('*.csv');
    N = length(files);
    if N == 0
        warning('No CSV files found in %s. Skipping plot.', pathToCsv);
        cd(originpath);
        return;
    end

    % Optional: apply transformation to specific calibratables
    if isfield(calibratables, 'PedalPosProIncrease_Th')
        calibratables.PedalPosProIncrease_Th{2, :} = ...
            calibratables.PedalPosProIncrease_Th{2, :} * 100;
    end

    % Define x and y variables (JSON variable names)
    xVar = char(graphSpec.Reference(1));
    yVar = char(graphSpec.Reference(graphIndex));

    % Axis labels 
    xLabel = char(graphSpec.Axis_Name(1));

    % Normalize plotEnabled
    plotEnabled = strtrim(string(graphSpec.plotEnabled(graphIndex)));

    % Debug
    fprintf('Graph %d plotEnabled = %s\n', graphIndex, plotEnabled);

    % Skip plotting if plotEnabled is false or NA
    if ~strcmpi(plotEnabled, "false") && ~strcmpi(plotEnabled, "NA")

        % Group info
        groupId   = titleIdx(graphIndex);
        groupRows = find(titleIdx == groupId);
        rowInGroup = find(groupRows == graphIndex);   
        firstRow  = firstRows(groupId);
        lastRow   = lastRows(groupId);
        isFirst   = (graphIndex == firstRow);
        isLast    = (graphIndex == lastRow);

        % --- Option 2: persistent figure handling ---
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

        Calibration_Limit = char(graphSpec.Calibration_Lim(graphIndex));

        for i = 1:N
            filename = files(i).name;
            opts = detectImportOptions(filename, 'VariableNamesLine', 1, ...
                'Delimiter', ',', 'PreserveVariableNames', true);
            try
                data = readtable(filename, opts);
            catch e
                warning('Failed to read %s: %s. Skipping file.', filename, e.message);
                continue;
            end

            % --- Resolve X and Y column indices robustly (case-insensitive) ---
            xCandidate = xVar;
            idxX = find(strcmpi(xVar, varName), 1);
            if ~isempty(idxX), xCandidate = displayNames{idxX}; end

            yCandidate = yVar;
            idxY = find(strcmpi(yVar, varName), 1);
            if ~isempty(idxY), yCandidate = displayNames{idxY}; end

            xColIdx = find(strcmpi(xCandidate, data.Properties.VariableNames), 1);
            if isempty(xColIdx)
                xColIdx = find(strcmpi(xVar, data.Properties.VariableNames), 1);
            end
            yColIdx = find(strcmpi(yCandidate, data.Properties.VariableNames), 1);
            if isempty(yColIdx)
                yColIdx = find(strcmpi(yVar, data.Properties.VariableNames), 1);
            end

            if isempty(xColIdx) || isempty(yColIdx)
                warning('X (%s) or Y (%s) variable not found in %s. Skipping file.', ...
                        xVar, yVar, filename);
                continue;
            end

            % Apply condition
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
                    continue;
                end
            else
                warning('Condition column "%s" not found in %s. Using all rows.', ...
                        plotEnabled, filename);
                filtIdx = 1:height(data);
            end

            legendName = string(graphSpec.Legend(graphIndex));
            legendName = char(legendName);  % ensure char for plot

            % --- Force numeric extraction ---
            x = table2array(data(filtIdx, xColIdx));
            y = table2array(data(filtIdx, yColIdx));

            % --- Marker + Color selection ---
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

            if isstring(markerStyle)
                markerStyle = char(markerStyle);
            end

            % ConnectPoints 
            cpRaw = graphSpec.ConnectPoints(graphIndex);
            cpStr = lower(strtrim(string(cpRaw)));
            connectFlag = false;
            if islogical(cpRaw)
                connectFlag = cpRaw;
            elseif isnumeric(cpRaw)
                connectFlag = cpRaw ~= 0;
            else
                connectFlag = ismember(cpStr, ["true","1","yes","y"]);
            end

            % Ensure lineColors is numeric
            if istable(lineColors)
                lineColors = table2array(lineColors);
            end

            if connectFlag
                plot(x, y, 'LineStyle','-',   'Marker', markerStyle, ...
                    'DisplayName', legendName, 'Color', thisColor);
            else
                plot(x, y, 'LineStyle','none','Marker', markerStyle, ...
                    'DisplayName', legendName, 'Color', thisColor);
            end

        end % for i = 1:N

        % Calibration limit
        if ~strcmp(Calibration_Limit, 'none')
            if isfield(calibratables, Calibration_Limit)
                lim_data   = calibratables.(Calibration_Limit);
                lim_data_x = lim_data{1,:};
                lim_data_y = lim_data{2,:};
                plot(lim_data_x, lim_data_y, 'DisplayName', Calibration_Limit);
            else
                warning('Calibration limit "%s" not found in calibratables.', Calibration_Limit);
            end
        end

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
