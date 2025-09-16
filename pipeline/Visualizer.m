classdef Visualizer
    properties
        graphSpec      % metadata of graph
        lineColor      % color of the curve
        calibratables  % unpacked calibratables
    end

    methods
        function obj = Visualizer(config)
            % Constructor: initializes Visualizer from handler struct
            obj.graphSpec     = config.graphSpec;
            obj.lineColor     = config.lineColors;
            obj.calibratables = config.calibratables;
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
            numGraphs = height(obj.graphSpec);

            for j = 2:numGraphs
                plotType = lower(strtrim(obj.graphSpec.plotType{j}));

                switch lower(plotType)
                    case 'scatter'
                        visScatterPlotter(obj.graphSpec, obj.lineColor, obj.calibratables, j, seldatapath);
                    case 'stem'
                        visStemPlotter(obj.graphSpec, obj.lineColor, obj.calibratables, j, seldatapath);
                    case 'pie'
                        visPiePlotter(obj.graphSpec, obj.lineColor, obj.calibratables, j, seldatapath);
                    otherwise
                        warning('Unsupported plot type "%s" at row %d. Skipping.', plotType, j);
                end
            end
        end % function plot
    end % methods
end % classdef Visualizer
