classdef Visualizer
    properties
        graphSpec        % metadata of graph
        lineColors       % color of the curve
        markerShapes     % marker shape of the curve
        calibratables    % unpacked calibratables
        pathToCsv        % path to csv files
        pathToKpiSchema  % path to JSON schema file
    end

    methods
        function obj = Visualizer(config, kpiExtractor)
            % Constructor: initializes Visualizer from config and KPIExtractor
            if nargin < 2
                error('Configuration object and KPIExtractor instance are required for initialization.');
            end
            
            % Validate input is a KPIExtractor instance
            if ~isa(kpiExtractor, 'KPIExtractor')
                error('Second argument must be an instance of KPIExtractor.');
            end
            
            % Initialize properties
            obj.graphSpec       = config.graphSpec;
            obj.lineColors      = config.lineColors;
            obj.markerShapes    = config.markerShapes;
            obj.calibratables   = config.calibratables;
            obj.pathToKpiSchema = config.kpiSchemaPath;
            obj.pathToCsv       = kpiExtractor.pathToCsv;
        end

        function plot(obj)
            % Main plotting dispatcher using pathToCsv
            if isempty(obj.pathToCsv) || ~isfolder(obj.pathToCsv)
                warning('Invalid or empty pathToCsv: %s. Plotting aborted.', obj.pathToCsv);
                return;
            end

            numGraphs = height(obj.graphSpec);

            for j = 2:numGraphs
                plotType = lower(strtrim(obj.graphSpec.plotType{j}));

                switch lower(plotType)
                    case 'scatter'
                        visScatterPlotter(obj, j);
                    case 'stem'
                        visStemPlotter(obj, j);
                    case 'pie'
                        visPiePlotter(obj, j);
                    otherwise
                        warning('Unsupported plot type "%s" at row %d. Skipping.', plotType, j);
                end
            end
        end % function plot
    end % methods
end % classdef Visualizer