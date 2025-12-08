package qc.pipeline;
import org.apache.commons.exec.CommandLine;
import org.apache.commons.exec.DefaultExecutor;
import org.apache.commons.exec.PumpStreamHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.IOException;

public class JobExecutor {
    private static final Logger logger = LoggerFactory.getLogger(JobExecutor.class);

    public static class ExecutionResult {
        public int exitCode;
        public String outputLogs;
        public String errorLogs;

        public ExecutionResult(int exitCode, String outputLogs, String errorLogs) {
            this.exitCode = exitCode;
            this.outputLogs = outputLogs;
            this.errorLogs = errorLogs;
        }
    }

    /**
     * Executes a CLI command and returns the result/logs.
     */
    public ExecutionResult executeCommand(String commandLineString) {
        CommandLine cmdLine = CommandLine.parse(commandLineString);
        DefaultExecutor executor = new DefaultExecutor();

        // --- STREAM GOBBLING (Crucial) ---
        // We capture stdout and stderr into streams so the Python script doesn't hang waiting for buffer space.
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ByteArrayOutputStream errorStream = new ByteArrayOutputStream();
        PumpStreamHandler streamHandler = new PumpStreamHandler(outputStream, errorStream);
        executor.setStreamHandler(streamHandler);

        // Don't throw exception on non-zero exit codes (we want to handle them manually)
        executor.setExitValues(null);

        try {
            logger.info("Executing: {}", commandLineString);
            int exitValue = executor.execute(cmdLine);
            return new ExecutionResult(exitValue, outputStream.toString(), errorStream.toString());
        } catch (IOException e) {
            logger.error("Execution failed", e);
            return new ExecutionResult(-1, "", "Exception: " + e.getMessage());
        }
    }
}