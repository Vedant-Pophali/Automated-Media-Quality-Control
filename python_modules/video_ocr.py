import cv2
import os
import shutil
import subprocess
import sys
import easyocr
import glob
import json
import argparse
from datetime import timedelta

# --- CRITICAL FIX: Force UTF-8 Output for Windows/Java ---
sys.stdout.reconfigure(encoding='utf-8')

CONFIDENCE_THRESHOLD = 0.5

def detect_language(text):
    hindi_chars = 0
    english_chars = 0
    for char in text:
        if '\u0900' <= char <= '\u097F':
            hindi_chars += 1
        elif 'a' <= char <= 'z' or 'A' <= char <= 'Z':
            english_chars += 1
    if hindi_chars > 0:
        return 'hi'
    return 'en'

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Using simple print to avoid encoding errors
        print("FFmpeg error")
        sys.exit(1)

def extract_frames(video_path, output_folder, interval_seconds):
    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        sys.exit(1)
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    fps_value = 1 / interval_seconds
    cmd = [
        "ffmpeg", "-i", video_path, "-vf", f"fps={fps_value}",
        "-hide_banner", "-loglevel", "error",
        os.path.join(output_folder, "frame_%04d.jpg")
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("FFmpeg extraction failed")
        sys.exit(1)

def run_ocr_pipeline(frame_folder, output_json, interval_seconds, video_path_name):
    # CRITICAL FIX: gpu=False ensures stability in background processes
    # CRITICAL FIX: verbose=False stops the internal progress bar
    reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)

    frame_files = sorted(glob.glob(os.path.join(frame_folder, "*.jpg")))
    detected_events = []

    # Loop silently (Removed the "Processing Frame..." print statement)
    for idx, frame_path in enumerate(frame_files):
        try:
            results = reader.readtext(frame_path)
        except Exception:
            continue

        for (bbox, text, prob) in results:
            if prob > CONFIDENCE_THRESHOLD:
                detected_events.append({
                    "type": "vernacular_text_detected",
                    "start_time": idx * interval_seconds,
                    "end_time": (idx * interval_seconds) + interval_seconds,
                    "confidence": float(prob),
                    "details": {
                        "text": text.strip(),
                        "language": detect_language(text)
                    }
                })

    unified_report = {
        "module": "ocr_extraction",
        "video_file": video_path_name,
        "status": "PASSED",
        "events": detected_events
    }

    with open(output_json, "w", encoding='utf-8') as f:
        json.dump(unified_report, f, indent=4, ensure_ascii=False)
        print(f"OCR Report saved to {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    check_ffmpeg()
    extract_frames(args.input, "extracted_frames", 2)
    run_ocr_pipeline("extracted_frames", args.output, 2, args.input)