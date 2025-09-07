function Vis_ScatterPlotter(configFilePath, dataFolder)
    % Read configuration from Excel
    configTable = readtable(configFilePath);

    for i = 1:height(configTable)
        % Extract plot settings
        graphTitle = configTable.Title{i};
        xName = configTable.XName{i};
        yName = configTable.YName{i};
        xRange = str2num(configTable.XRange{i}); %#ok<ST2NM>
        yRange = str2num(configTable.YRange{i}); %#ok<ST2NM>
        isCalParamIncluded = configTable.isCalParamIncluded(i);
        isAveIncluded = configTable.isAveIncluded(i);
        isConnected = configTable.isConnected(i);

        % Load scatter data
        dataFile = fullfile(dataFolder, configTable.DataFile{i});
        data = readtable(dataFile);
        xData = data.(xName);
        yData = data.(yName);

        % Sort by x for connection
        [xDataSorted, sortIdx] = sort(xData);
        yDataSorted = yData(sortIdx);

        % Begin plotting
        figure;
        scatter(xData, yData, 'filled');
        hold on;

        % Plot threshold line if needed
        if isCalParamIncluded
            threshold = configTable.CalThreshold(i);
            yline(threshold, '--r', 'Threshold');
        end

        % Plot average line if needed
        if isAveIncluded
            yAvg = mean(yData);
            yline(yAvg, '--k', sprintf('Average: %.2f', yAvg));
        end

        % Connect points if needed
        if isConnected
            plot(xDataSorted, yDataSorted, '-b');
        end

        % Final touches
        title(graphTitle);
        xlabel(xName);
        ylabel(yName);
        xlim(xRange);
        ylim(yRange);
        grid on;
        hold off;
    end
end
