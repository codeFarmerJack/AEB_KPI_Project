classdef Visualizer
    properties
        OutputFolder  % Where plots will be saved
    end

    methods
        function obj = Visualizer(outputFolder)
            % Constructor: set output folder for saving plots
            if nargin < 1
                outputFolder = 'Plots';
            end
            obj.OutputFolder = outputFolder;

            if ~exist(obj.OutputFolder, 'dir')
                mkdir(obj.OutputFolder);
            end
        end

        function plotScatter(obj, configTable, dataFolder)
            % Plot scatter graphs based on config table
            for i = 1:height(configTable)
                % Extract config
                titleStr = configTable.Title{i};
                xName = configTable.XName{i};
                yName = configTable.YName{i};
                xRange = str2num(configTable.XRange{i}); %#ok<ST2NM>
                yRange = str2num(configTable.YRange{i}); %#ok<ST2NM>
                dataFile = fullfile(dataFolder, configTable.DataFile{i});
                isCalParamIncluded = configTable.isCalParamIncluded(i);
                isAveIncluded = configTable.isAveIncluded(i);
                isConnected = configTable.isConnected(i);

                % Load data
                data = readtable(dataFile);
                xData = data.(xName);
                yData = data.(yName);

                % Sort by x for connection
                [xSorted, sortIdx] = sort(xData);
                ySorted = yData(sortIdx);

                % Begin plotting
                figure;
                scatter(xData, yData, 'filled');
                hold on;

                % Threshold line
                if isCalParamIncluded
                    threshold = configTable.CalThreshold(i);
                    yline(threshold, '--r', 'Threshold');
                end

                % Average line
                if isAveIncluded
                    yAvg = mean(yData);
                    yline(yAvg, '--k', sprintf('Average: %.2f', yAvg));
                end

                % Connect points
                if isConnected
                    plot(xSorted, ySorted, '-b');
                end

                % Final touches
                title(titleStr);
                xlabel(xName);
                ylabel(yName);
                xlim(xRange);
                ylim(yRange);
                grid on;

                % Save plot
                saveas(gcf, fullfile(obj.OutputFolder, sprintf('%s.png', titleStr)));
                close;
            end
        end

        function plotTimeSeries(obj, time, signal, titleStr, xLabel, yLabel)
            % Simple time-series plot
            figure;
            plot(time, signal, 'LineWidth', 1.5);
            title(titleStr);
            xlabel(xLabel);
            ylabel(yLabel);
            grid on;

            % Save plot
            saveas(gcf, fullfile(obj.OutputFolder, sprintf('%s.png', titleStr)));
            close;
        end

        function plotBarComparison(obj, kpiValues, thresholds, labels, titleStr)
            % Bar plot comparing KPIs to thresholds
            figure;
            bar(kpiValues);
            hold on;
            plot(thresholds, 'r--o', 'LineWidth', 1.5);
            hold off;

            title(titleStr);
            ylabel('Value');
            xticks(1:length(labels));
            xticklabels(labels);
            legend('KPI', 'Threshold');
            grid on;

            % Save plot
            saveas(gcf, fullfile(obj.OutputFolder, sprintf('%s.png', titleStr)));
            close;
        end
    end
end
