import cv2  # OpenCV for video processing
import numpy as np  # NumPy for fast array math
import sys  # For command line arguments
import json # For JSON output
import os   # For file path verification
import argparse

def analyze_video(video_path):
    """
    Analyzes a video file to detect 'Black Screen' glitches.
    """

    # --- 0. SAFETY CHECK ---
    if not os.path.exists(video_path):
        error_msg = {"error": f"File not found: {video_path}", "status": "ERROR"}
        print(json.dumps(error_msg, indent=4))
        return None

    # --- 1. CONFIGURATION ---
    DARK_THRESHOLD = 13      
    COVERAGE_THRESHOLD = 0.98 
    DURATION_THRESHOLD = 2.0  

    # --- 2. INITIALIZATION ---
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(json.dumps({"error": "Could not open video source", "status": "ERROR"}))
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30 
    
    frame_count = 0
    consecutive_black_frames = 0
    detected_segments = []

    # --- 3. ANALYSIS LOOP ---
    while True:
        ret, frame = cap.read()
        if not ret:
            break 
        
        frame_count += 1
        timestamp = frame_count / fps

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        dark_pixel_count = np.sum(gray < DARK_THRESHOLD)
        total_pixels = gray.size
        dark_ratio = dark_pixel_count / total_pixels

        if dark_ratio > COVERAGE_THRESHOLD:
            consecutive_black_frames += 1
        else:
            duration = consecutive_black_frames / fps
            if duration >= DURATION_THRESHOLD:
                start_time = timestamp - duration
                detected_segments.append({
                    "start_time": round(start_time, 2),
                    "end_time": round(timestamp, 2),
                    "duration": round(duration, 2),
                    "type": "black_screen_glitch"
                })
            consecutive_black_frames = 0

    # --- 4. FINAL CHECK ---
    if consecutive_black_frames > 0:
        duration = consecutive_black_frames / fps
        if duration >= DURATION_THRESHOLD:
            start_time = timestamp - duration
            detected_segments.append({
                "start_time": round(start_time, 2),
                "end_time": round(timestamp, 2),
                "duration": round(duration, 2),
                "type": "black_screen_glitch"
            })

    cap.release()

    # --- 5. FORMAT TO UNIFIED DATA CONTRACT ---
    unified_report = {
        "module": "visual_qc",
        "video_file": video_path,
        "status": "REJECTED" if len(detected_segments) > 0 else "PASSED",
        "events": []
    }

    for defect in detected_segments:
        event = {
            "type": "black_screen_glitch",
            "start_time": defect["start_time"],
            "end_time": defect["end_time"],
            "confidence": 1.0, 
            "details": {
                "duration": defect["duration"]
            }
        }
        unified_report["events"].append(event)

    return unified_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual QC: Black Screen Detector")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", required=True, help="Path to save JSON report")
    
    args = parser.parse_args()
    
    report_data = analyze_video(args.input)
    
    if report_data:
        with open(args.output, "w") as f:
            json.dump(report_data, f, indent=4)
        print(f"[Visual QC] Report saved to {args.output}")