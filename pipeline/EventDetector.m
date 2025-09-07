classdef EventDetector
    properties
        RawData          % Full dataset containing multiple AEB events
        EventField       % Field used to identify event boundaries (e.g., event ID or timestamp gaps)
        OutputFolder     % Folder to store individual AEB event files
    end

    methods
        function obj = EventDetector(rawData, eventField)
            % Constructor: initialize with raw data and event identifier field
            obj.RawData = rawData;
            obj.EventField = eventField;
            obj.OutputFolder = 'AEBEvents';

            % Create output folder if it doesn't exist
            if ~exist(obj.OutputFolder, 'dir')
                mkdir(obj.OutputFolder);
            end
        end

        function eventFiles = segmentAndSaveEvents(obj)
            % Segment the raw data into individual events and save each one
            eventIDs = unique(obj.RawData.(obj.EventField));
            eventFiles = {};

            for i = 1:length(eventIDs)
                eventID = eventIDs(i);
                eventData = obj.RawData(obj.RawData.(obj.EventField) == eventID, :);

                % Construct filename
                filename = fullfile(obj.OutputFolder, sprintf('AEBEvent_%d.mat', eventID));
                save(filename, 'eventData');

                eventFiles{end+1} = filename;
            end

            fprintf('✅ %d AEB events saved to "%s"\n', length(eventIDs), obj.OutputFolder);
        end
    end
end
