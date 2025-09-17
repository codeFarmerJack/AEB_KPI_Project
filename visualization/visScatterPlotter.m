function visScatterPlotter(obj, graphIndex)
% visScatterPlotter - Generates scatter plot for a specific graph index
% Inputs:
%   obj        - Visualizer object with graphSpec, lineColor, calibratables, pathToCsv
%   graphIndex - Row index in graphSpec to plot
%   jsonFile   - Path to JSON schema file for variable name mapping

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
    schema = jsondecode(raw);
    vars = schema.variables;
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

    fig = figure; hold on;
    set(fig, 'Position', [10 10 900 600]);
    xlim([-5 95]);
    ylim([graphSpec.Min_Axis_value(graphIndex), graphSpec.Max_Axis_value(graphIndex)]);
    
    % Define x and y variables
    xVar = 'vehSpd';
    yVar = char(graphSpec.Reference(graphIndex));
    conditionVar = char(graphSpec.Condition_Var(graphIndex));
    
    % Use variable names without units for axis labels
    xlabel(strrep(xVar, '_', '\_'), 'Interpreter', 'none');
    ylabel(strrep(yVar, '_', '\_'), 'Interpreter', 'none');
    title(char(graphSpec.Legend(graphIndex)));

    Calibration_Limit = char(graphSpec.Calibration_Lim(graphIndex));

    for i = 1:N
        filename = files(i).name;
        opts = detectImportOptions(filename, 'VariableNamesLine', 1, ...
            'Delimiter', ',', 'PreserveVariableNames', true);
        if ismember(conditionVar, opts.VariableNames)
            opts.VariableTypes{strcmp(opts.VariableNames, conditionVar)} = 'logical';
        end
        try
            data = readtable(filename, opts);
        catch e
            warning('Failed to read %s: %s. Skipping file.', filename, e.message);
            continue;
        end

        % Map expected names to actual column names
        xCol = '';
        yCol = '';
        for j = 1:length(varName)
            if strcmp(varName{j}, xVar)
                xCol = displayNames{j};
            end
            if strcmp(varName{j}, yVar)
                yCol = displayNames{j};
            end
        end
        if isempty(xCol)
            xCol = xVar;
        end
        if isempty(yCol)
            yCol = yVar;
        end

        % Validate x and y variables
        if ~ismember(xCol, data.Properties.VariableNames) || ...
           ~ismember(yCol, data.Properties.VariableNames)
            warning('X (%s) or Y (%s) variable not found in %s. Skipping file.', ...
                    xCol, yCol, filename);
            continue;
        end

        % Validate condition variable
        if ~ismember(conditionVar, data.Properties.VariableNames)
            warning('Column "%s" not found in %s. Plotting without condition.', ...
                    conditionVar, filename);
            filtIdx = 1:height(data);
        else
            if ~islogical(data.(conditionVar))
                warning('Column "%s" in %s is not logical. Converting.', ...
                        conditionVar, filename);
                if isstring(data.(conditionVar)) || iscellstr(data.(conditionVar))
                    data.(conditionVar) = strcmp(data.(conditionVar), 'true');
                elseif isnumeric(data.(conditionVar))
                    data.(conditionVar) = logical(data.(conditionVar));
                end
            end
            filtIdx = find(data.(conditionVar));
            if isempty(filtIdx)
                warning('No data satisfies condition "%s" in %s. Plotting without condition.', ...
                        conditionVar, filename);
                filtIdx = 1:height(data);
            end
        end

        legendName = char(graphSpec.Legend(graphIndex));
        
        x = round(data.(xCol)(filtIdx), 1);
        y = data.(yCol)(filtIdx);

        plot(x, y, 'LineStyle', 'none', 'Marker', '*', ...
             'DisplayName', legendName, 'Color', lineColor{i,:});
    end

    % Extract and plot calibration limit if specified
    if ~strcmp(Calibration_Limit, 'none')
        if isfield(calibratables, Calibration_Limit)
            lim_data = calibratables.(Calibration_Limit);
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

    cd(originpath);
end