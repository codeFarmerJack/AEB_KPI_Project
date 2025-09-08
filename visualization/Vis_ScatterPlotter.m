function Vis_ScatterPlotter(graphFormat, lineColor, calibratables, graphIndex, seldatapath)
% Vis_ScatterPlotter - Generates scatter plot for a specific graph index
% Inputs:
%   graphFormat   - Table containing graph metadata
%   lineColor     - Cell array or table of line colors
%   calibratables - Struct of unpacked calibratable data
%   graphIndex    - Row index in graphFormat to plot
%   seldatapath   - Path to folder containing CSV files

    originpath = pwd;
    cd(seldatapath);

    files = dir('*.csv');
    N = length(files);

    % Optional: apply transformation to specific calibratables
    % Convert the decimal values to percentages
    if isfield(calibratables, 'PedalPosProIncrease_Th')
        calibratables.PedalPosProIncrease_Th{2, :} = ...
            calibratables.PedalPosProIncrease_Th{2, :} * 100;
    end

    fig = figure; hold on;
    set(fig, 'Position', [10 10 900 600]);
    xlim([-5 95]);
    ylim([graphFormat.Min_Axis_value(graphIndex), graphFormat.Max_Axis_value(graphIndex)]);
    xlabel(char(graphFormat.Output_name(1)), 'Interpreter', 'none');
    ylabel(char(graphFormat.Output_name(graphIndex)), 'Interpreter', 'none');
    title(char(graphFormat.Legend(graphIndex)));

    Calibration_Limit = char(graphFormat.Calibration_Lim(graphIndex));

    for i = 1:N
        filename = files(i).name;
        opts = detectImportOptions(filename, 'VariableNamesLine', 1, ...
            "ReadRowNames", true, 'Delimiter', ',');
        data = readtable(filename, opts);

        Filt_Idx = find(data.(char(graphFormat.Condition_Var(graphIndex))));
        x = round(data.Veh_Spd(Filt_Idx), 1);
        y = data.(char(graphFormat.Reference(graphIndex)))(Filt_Idx);

        plot(x, y, 'LineStyle', 'none', 'Marker', '*', ...
            'DisplayName', filename, 'Color', lineColor{i,:});
    end

    % Extract and plot calibration limit if specified
    if ~strcmp(Calibration_Limit, "none")
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

    fig_name = strcat('Fig_', num2str(graphIndex-1, '%02d'), " - ", char(graphFormat.Legend(graphIndex)));
    print(fig, fig_name, '-dpng', '-r400');

    cd(originpath);
end
