classdef OutputHandler
    methods(Static)
        function saveResults(resultsTable, outputPath)
            % Save results to Excel or CSV
            [~, ~, ext] = fileparts(outputPath);

            switch lower(ext)
                case '.xlsx'
                    writetable(resultsTable, outputPath);
                case '.csv'
                    writetable(resultsTable, outputPath);
                otherwise
                    error('Unsupported output format: %s', ext);
            end

            fprintf('✅ Results saved to: %s\n', outputPath);
        end

        function saveStructAsMat(dataStruct, outputPath)
            % Save a struct to a .mat file
            save(outputPath, '-struct', 'dataStruct');
            fprintf('✅ Struct saved to: %s\n', outputPath);
        end

        function saveLog(logMessages, logPath)
            % Save log messages to a text file
            fid = fopen(logPath, 'w');
            for i = 1:length(logMessages)
                fprintf(fid, '%s\n', logMessages{i});
            end
            fclose(fid);
            fprintf('📝 Log saved to: %s\n', logPath);
        end
    end
end
