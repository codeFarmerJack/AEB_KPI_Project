function visScatterPlotter(obj, graphIndex)
% visScatterPlotter - Generates scatter plot for a specific graph index
% Inputs:
%   obj        - Visualizer object with graphSpec, lineColor, calibratables, pathToCsv
%   graphIndex - Row index in graphSpec to plot

    graphSpec       = obj.graphSpec;
    lineColor       = obj.lineColor;
    calibratables   = obj.calibratables;
    pathToCsv       = obj.pathToCsv;
    pathToKpiSchema = obj.pathToKpiSchema;

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
    xVar = 'vehSpd';
    yVar = char(graphSpec.Reference(graphIndex));

    % Axis labels 
    xLabel = char(graphSpec.Axis_Name(1));
    yLabel = char(graphSpec.Axis_Name(graphIndex));

    % Normalize plotEnabled (already guaranteed to be string from import)
    plotEnabled = strtrim(string(graphSpec.plotEnabled(graphIndex)));

    % Debug
    fprintf('Graph %d plotEnabled = %s\n', graphIndex, plotEnabled);

    % Skip plotting if plotEnabled is false or NA
    if ~strcmpi(plotEnabled, "false") && ~strcmpi(plotEnabled, "NA")
        % Create figure only if plotting is enabled
        fig = figure; hold on;
        set(fig, 'Position', [10 10 900 600]);
        
        % Set axis limits
        xlim([graphSpec.Min_Axis_value(1), graphSpec.Max_Axis_value(1)]);
        ylim([graphSpec.Min_Axis_value(graphIndex), graphSpec.Max_Axis_value(graphIndex)]);
        
        % Use variable names without units for axis labels
        xlabel(strrep(xLabel, '_', '\_'), 'Interpreter', 'none');
        ylabel(strrep(yLabel, '_', '\_'), 'Interpreter', 'none');
        title(char(graphSpec.Legend(graphIndex)));

        Calibration_Limit = char(graphSpec.Calibration_Lim(graphIndex));

        % prepare quick lookup map from lower(varName) -> displayName
        varNameLower = lower(varName);
        % for mapping convenience (parallel arrays used below)

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
            % Candidate display-name (JSON) for x and y
            xCandidate = xVar;
            idxX = find(strcmpi(xVar, varName), 1);
            if ~isempty(idxX), xCandidate = displayNames{idxX}; end

            yCandidate = yVar;
            idxY = find(strcmpi(yVar, varName), 1);
            if ~isempty(idxY), yCandidate = displayNames{idxY}; end

            % Try to find actual column indices in the CSV (case-insensitive)
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
                filtIdx = 1:height(data);   % all rows
            elseif ismember(plotEnabled, data.Properties.VariableNames)
                % Dynamic filtering based on a column in the CSV
                condCol = data.(plotEnabled);

                % Convert if not logical
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

            legendName = char(graphSpec.Legend(graphIndex));
            
            % extract x and y using column indices (safe for any column name)
            x = round(data{filtIdx, xColIdx}, 1);
            y = data{filtIdx, yColIdx};

            plot(x, y, 'LineStyle', 'none', 'Marker', '*', ...
                 'DisplayName', legendName, 'Color', lineColor{i,:});
        end % for i = 1:N

        % Extract and plot calibration limit if specified
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

        legend('Interpreter', 'none', 'Location', 'northeast', ...
               'FontSize', 8, 'Orientation', 'vertical');
        grid on;
        set(gca, 'xminorgrid', 'on', 'yminorgrid', 'on');

        fig_name = strcat('Fig_', num2str(graphIndex-1, '%02d'), ' - ', ...
                         char(graphSpec.Legend(graphIndex)));
        print(fig, fig_name, '-dpng', '-r400');
    end % End of plotEnabled check

    cd(originpath);
end