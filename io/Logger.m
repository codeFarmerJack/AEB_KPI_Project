classdef Logger
    properties
        Messages   % Cell array to store log messages
        LogPath    % Path to save the log file
    end

    methods
        function obj = Logger(logPath)
            % Constructor: initialize log path and message list
            if nargin < 1
                logPath = fullfile('Logs', ['log_' datestr(now, 'yyyymmdd_HHMMSS') '.txt']);
            end
            obj.LogPath = logPath;
            obj.Messages = {};

            % Create Logs folder if needed
            logFolder = fileparts(logPath);
            if ~exist(logFolder, 'dir')
                mkdir(logFolder);
            end
        end

        function obj = log(obj, message)
            % Add a timestamped message to the log
            timestamp = datestr(now, 'yyyy-mm-dd HH:MM:SS');
            fullMessage = sprintf('[%s] %s', timestamp, message);
            obj.Messages{end+1} = fullMessage;
            fprintf('%s\n', fullMessage);  % Also print to console
        end

        function save(obj)
            % Save all log messages to the log file
            fid = fopen(obj.LogPath, 'w');
            for i = 1:length(obj.Messages)
                fprintf(fid, '%s\n', obj.Messages{i});
            end
            fclose(fid);
            fprintf('📝 Log saved to: %s\n', obj.LogPath);
        end

        function clear(obj)
            % Clear all stored messages
            obj.Messages = {};
        end
    end
end
