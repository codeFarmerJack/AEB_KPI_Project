classdef Visualizer
    properties
        graphFormat     % metadata of graph
        lineColor       % color of the curve
        calibratables   % unpacked calibratables
    end

    methods
        function obj = Visualizer(handler)
            % Constructor: initializes Visualizer from handler struct
            obj.graphFormat   = handler.Graphs;
            obj.lineColor     = handler.LineColors;
            obj.calibratables = handler.Calibratables;
        end

        function plot(obj)
            % Select folder once
            originpath = pwd;
            seldatapath = uigetdir(originpath, 'Select folder containing CSV files');
            if seldatapath == 0
                warning('No folder selected. Plotting aborted.');
                return;
            end

            % Main plotting dispatcher
            numGraphs = height(obj.graphFormat);

            for j = 2:numGraphs
                plotType = lower(strtrim(obj.graphFormat.plotType{j}));

                switch plotType
                    case 'scatter'
                        Vis_ScatterPlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j, seldatapath);
                    case 'stem'
                        Vis_StemPlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j, seldatapath);
                    case 'pie'
                        Vis_PiePlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j, seldatapath);
                    otherwise
                        warning('Unsupported plot type "%s" at row %d. Skipping.', plotType, j);
                end
            end
        end

    end
end
