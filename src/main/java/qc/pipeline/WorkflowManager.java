package qc.pipeline;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;

public class WorkflowManager {
    private static final Logger logger = LoggerFactory.getLogger(WorkflowManager.class);
    private final JobExecutor executor = new JobExecutor();
    private final ObjectMapper objectMapper = new ObjectMapper();

    private static final String PYTHON_CMD = "C:\\Users\\VEDANT\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";
    private static final String MODULES_DIR = "python_modules";
    private static final String OUTPUT_DIR = "outputs";

    public void runQualityControlPipeline(String videoFileName) {
        String videoPath = Paths.get(videoFileName).toAbsolutePath().toString();

        // Ensure output dir exists
        new File(OUTPUT_DIR).mkdirs();

        logger.info("--- STARTING HYBRID QC PIPELINE FOR: {} ---", videoFileName);

        // 1. Define the Tasks
        String visualReport = Paths.get(OUTPUT_DIR, "report_visual.json").toString();
        String audioReport = Paths.get(OUTPUT_DIR, "report_audio.json").toString();
        String ocrReport = Paths.get(OUTPUT_DIR, "report_ocr.json").toString();

        // Task A: Visual QC
        String cmdVisual = String.format("%s %s/detect_black.py --input \"%s\" --output \"%s\"",
                PYTHON_CMD, MODULES_DIR, videoPath, visualReport);

        // Task B: Audio QC
        String cmdAudio = String.format("%s %s/validate_loudness.py --input \"%s\" --output \"%s\"",
                PYTHON_CMD, MODULES_DIR, videoPath, audioReport);

        // Task C: OCR
        String cmdOcr = String.format("%s %s/video_ocr.py --input \"%s\" --output \"%s\"",
                PYTHON_CMD, MODULES_DIR, videoPath, ocrReport);

        // 2. Execute Parallel or Sequential? (Sequential for simplicity here)
        runTask("Visual QC", cmdVisual);
        runTask("Audio QC", cmdAudio);
        runTask("OCR Extraction", cmdOcr);

        // 3. Aggregate
        logger.info("--- AGGREGATING RESULTS ---");
        String masterReportPath = Paths.get(OUTPUT_DIR, "Master_Report.json").toString();
        // New Line (Points to python_modules folder)
        String cmdAggregator = String.format("%s %s/generate_master_report.py --inputs \"%s\" \"%s\" \"%s\" --output \"%s\"",
                PYTHON_CMD, MODULES_DIR, visualReport, audioReport, ocrReport, masterReportPath);

        boolean aggSuccess = runTask("Aggregator", cmdAggregator);

        // 4. Final Java Processing
        if (aggSuccess) {
            parseAndPrintResult(masterReportPath);
        } else {
            logger.error("Pipeline failed at Aggregation step.");
        }
    }

    private boolean runTask(String taskName, String command) {
        JobExecutor.ExecutionResult result = executor.executeCommand(command);
        if (result.exitCode == 0) {
            logger.info("[SUCCESS] {}", taskName);
            return true;
        } else {
            logger.error("[FAILED] {} (Exit Code: {})", taskName, result.exitCode);
            logger.error("Stderr: {}", result.errorLogs);
            return false;
        }
    }

    private void parseAndPrintResult(String jsonPath) {
        try {
            // Read JSON file into a Map
            Map<?, ?> report = objectMapper.readValue(new File(jsonPath), Map.class);

            String overallStatus = (String) report.get("overall_status");
            List<?> timeline = (List<?>) report.get("timeline");

            logger.info("==========================================");
            logger.info(" QC COMPLETED");
            logger.info(" Overall Status: {}", overallStatus);
            logger.info(" Events Found: {}", timeline.size());
            logger.info(" Report Location: {}", jsonPath);
            logger.info("==========================================");

        } catch (Exception e) {
            logger.error("Failed to parse Master JSON", e);
        }
    }

    // Main method for testing
    public static void main(String[] args) {
        // Ensure you copy your 'video.mp4' to the project root first!
        new WorkflowManager().runQualityControlPipeline("video.mp4");
    }
}