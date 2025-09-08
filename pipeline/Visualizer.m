classdef Visualizer
    properties
        graphFormat     % metadata of graph
        lineColor       % color of the curve
        calibratables   % unpacked calibratables
    end

    methods
        function obj = Visualizer(graphFormat, lineColor, calStruct)
            % Constructor: unpack calibratables internally
            obj.graphFormat = graphFormat;
            obj.lineColor = lineColor;
            obj.calibratables = obj.unpackCalibratables(calStruct);
        end

        function plot(obj)
            % Main plotting dispatcher
            numGraphs = height(obj.graphFormat);

            for j = 2:numGraphs
                plotType = lower(strtrim(obj.graphFormat.Format{j}));

                switch plotType
                    case 'scatter'
                        Vis_ScatterPlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j);
                    case 'stem'
                        Vis_StemPlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j);
                    case 'pie'
                        Vis_PiePlotter(obj.graphFormat, obj.lineColor, obj.calibratables, j);
                    otherwise
                        warning('Unsupported plot type "%s" at row %d. Skipping.', plotType, j);
                end
            end
        end
    end

    methods (Access = private)
        function unpacked = unpackCalibratables(~, calStruct)
            % Internal method to unpack nested calibratables
            unpacked = struct();
            categories = fieldnames(calStruct);

            for i = 1:numel(categories)
                categoryStruct = calStruct.(categories{i});
                signals = fieldnames(categoryStruct);

                for j = 1:numel(signals)
                    signalName = signals{j};
                    signalStruct = categoryStruct.(signalName);

                    if isfield(signalStruct, 'Data')
                        unpacked.(signalName) = signalStruct.Data;
                    else
                        warning('Skipping "%s" in "%s": no .Data field found.', signalName, categories{i});
                    end
                end
            end
        end
    end
end
