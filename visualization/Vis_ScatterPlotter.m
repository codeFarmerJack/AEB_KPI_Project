function Vis_ScatterPlotter(handler)
% ScatterPlotter - Generates scatter plots for calibration data
% Input:
%   handler - Struct containing configuration and calibratable data

    % Save original path
    originpath = pwd;

    % Select data folder
    seldatapath = uigetdir(originpath, 'Select folder containing CSV files');
    cd(seldatapath);

    % Get CSV files
    files = dir('*.csv');
    N = length(files);

    % Load configuration
    lineColor = handler.Config.LineColors;
    graphFormat = handler.Config.Graphs;
    heightGraphFormat = height(graphFormat);

    % Unpack calibratables
    unpackedCal = utils.extractCalibratables(handler.Config.Calibratables);

    SteeringWheelAngle_Th           = unpackedCal.SteeringWheelAngle_Th;
    AEB_SteeringAngleRate_Override  = unpackedCal.AEB_SteeringAngleRate_Override;
    PedalPosProIncrease_Th          = unpackedCal.PedalPosProIncrease_Th;
    PedalPosProIncrease_Th{2, :}    = PedalPosProIncrease_Th{2, :} * 100;
    PedalPosPro_Override            = unpackedCal.PedalPosPro_Override;
    LateralAcceleration_th          = unpackedCal.LateralAcceleration_th;
    YawrateSuspension_Th            = unpackedCal.YawrateSuspension_Th;

    % Generate comparison figures
    for j = 2 : heightGraphFormat
        fig = figure; hold on;
        set(fig, 'Position', [10 10 900 600]);
        xlim([-5 95]);
        ylim([graphFormat.Min_Axis_value(j), graphFormat.Max_Axis_value(j)]);
        xlabel(char(graphFormat.Output_name(1)), 'Interpreter', 'none');
        ylabel(char(graphFormat.Output_name(j)), 'Interpreter', 'none');
        title(char(graphFormat.Legend(j)));

        Calibration_Limit = char(graphFormat.Calibration_Lim(j));

        for i = 1:N
            filename = files(i).name;
            opts = detectImportOptions(filename, 'VariableNamesLine', 1, ...
                "ReadRowNames", true, 'Delimiter', ',');
            data = readtable(filename, opts);

            Filt_Idx = find(data.(char(graphFormat.Condition_Var(j))));
            x = round(data.Veh_Spd(Filt_Idx), 1);
            y = data.(char(graphFormat.Reference(j)))(Filt_Idx);

            plot(x, y, 'LineStyle', 'none', 'Marker', '*', ...
                'DisplayName', filename, 'Color', lineColor{i,:});
        end

        % Plot calibration limit if available
        if ~strcmp(Calibration_Limit, "none")
            lim_data = eval(Calibration_Limit);
            lim_data_x = lim_data{1,:};
            lim_data_y = lim_data{2,:};
            plot(lim_data_x, lim_data_y, 'DisplayName', Calibration_Limit);
        end

        legend('Interpreter', 'none', 'Location', 'northeast', ...
            'FontSize', 8, 'Orientation', 'vertical');
        grid on;
        set(gca, 'xminorgrid', 'on', 'yminorgrid', 'on');

        fig_name = strcat('Fig_', num2str(j-1, '%02d'), " - ", char(graphFormat.Legend(j)));
        print(fig, fig_name, '-dpng', '-r400');
    end

    % Return to original path
    cd(originpath);
end
