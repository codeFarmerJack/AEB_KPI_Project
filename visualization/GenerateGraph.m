% Pre-Requisites

originpath=pwd;

seldatapath = uigetdir(path);
cd (seldatapath);

files = dir('*.csv');   % get all text files of the present folder
N = length(files) ;     % Total number of files

Line_Colour = handler.Config.LineColors;
Graph_Format = handler.Config.Graphs;
Height_Graph_Format = height(Graph_Format);

% Unpack individual calibratables from nested struct
steering = handler.Config.Calibratables.steering_precond_abrt_aeb;
throttle = handler.Config.Calibratables.throttle_abrt_aeb;
lat_accel = handler.Config.Calibratables.lat_accel;
yaw_rate = handler.Config.Calibratables.yaw_rate;

SteeringWheelAngle_Th           = steering.SteeringWheelAngle_Th.Data;
AEB_SteeringAngleRate_Override  = steering.AEB_SteeringAngleRate_Override.Data;
PedalPosProIncrease_Th          = throttle.PedalPosProIncrease_Th.Data;
PedalPosPro_Override            = throttle.PedalPosPro_Override.Data;
LateralAcceleration_th          = lat_accel.LateralAcceleration_th.Data;
YawrateSuspension_Th            = yaw_rate.YawrateSuspension_Th.Data;

%Line_Colour = readtable('Graph_Format_v1.xlsx','Sheet', 'lineColors', 'ReadRowNames',false);
%Graph_Format = readtable("Graph_Format_v1.xlsx",'Sheet', 'graphFormat', 'ReadRowNames',false)
%Height_Graph_Format = height(Graph_Format);

%Load Calibratables from Active_Safety_Long_Calibration_Plan.xlsx
%cal_path = "C:\Users\jwang79\OneDrive\OneDrive - JLR\04_ActiveSafety\02_cal_plan";
%cal_file = 'Active_Safety_Long_Calibration_Plan.xlsx';
%cal_file_path = fullfile(cal_path, cal_file);

% SteeringWheelAngle_Th = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M7:X8');
%AEB_SteeringAngleRate_Override = readmatrix(cal_file_path, 'Sheet', 'steering_precond&abrt_aeb', 'Range', 'M13:X14');
% Multiply the 2nd row by 100 to convert the values to percentages
%PedalPosProIncrease_Th = readmatrix(cal_file_path, 'Sheet', 'throttle_abrt_aeb', 'Range', 'L12:P13');
%PedalPosProIncrease_Th(2, :) = PedalPosProIncrease_Th(2, :) * 100;
%YawrateSuspension_Th = readmatrix(cal_file_path, 'Sheet', 'yaw_rate', 'Range', 'K6:P7');
%LateralAcceleration_th = readmatrix(cal_file_path, 'Sheet', 'lat_accel', 'Range', 'I6:N7');

% Generate comparison figures

for j=2:Height_Graph_Format
    fig=figure; hold on
    set(fig,'Position', [10 10 900 600]);
    xlim([-5 95]);
    ylim([Graph_Format.Min_Axis_value(j) Graph_Format.Max_Axis_value(j)]);
    xlabel(char(Graph_Format.Output_name(1)),'Interpreter','none')
    ylabel(char(Graph_Format.Output_name(j)),'Interpreter','none')
    title(char(Graph_Format.Legend(j)));
    Calibration_Limit = Graph_Format.Calibration_Lim{j};


    for i=1:N
        filename = files(i).name;
        [filepath,name,ext] = fileparts(filename);
        opts = detectImportOptions(filename,'VariableNamesLine',1,"ReadRowNames",true,'Delimiter',',');
        data = readtable(filename,opts);
        Filt_Idx = find(data.(char(Graph_Format.Condition_Var(j))));
        x= round(data.Veh_Spd(Filt_Idx) ,1);
        y= data.(char(Graph_Format.Reference(j)))(Filt_Idx);
        p=plot(x,y,'LineStyle','none','Marker','*','DisplayName',name,'Color',Line_Colour{i,:});
        hold on;
        Calibration_Limit = char(Graph_Format.Calibration_Lim(j));
    end 

    if ~strcmp(Calibration_Limit, "none")
        lim_data = eval(Calibration_Limit);
        lim_data_x = lim_data{1,:};
        lim_data_y = lim_data{2,:};
        plot(lim_data_x,lim_data_y,'DisplayName',Calibration_Limit);
    end

    set(legend,'Interpreter','none','Location','northeast','Fontsize', 8,'Orientation','vertical');
    legend show
    grid on
    set(gca,'xminorgrid','on','yminorgrid','on');
    fig_name = strcat('Fig_',num2str(j-1,'%#02d')," - ",char(Graph_Format.Legend(j)));
    print(fig,fig_name,'-dpng','-r400');

end

cd(originpath);
