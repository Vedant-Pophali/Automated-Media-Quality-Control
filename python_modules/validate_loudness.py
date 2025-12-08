import subprocess
import json
import sys
import os
import argparse

def get_ffmpeg_loudness(video_path, stream_index=0):
    if not os.path.exists(video_path):
        return {"error": f"File not found: {video_path}"}

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-map", f"0:a:{stream_index}",
        "-vn",
        "-af", "loudnorm=I=-23:LRA=7:tp=-2:print_format=json",
        "-f", "null",
        "-"
    ]

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        output = result.stderr
        try:
            json_start = output.rfind('{')
            json_end = output.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON payload found")
            json_str = output[json_start:json_end]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return {"error": "Could not parse metrics. Stream might be silent."}
    except FileNotFoundError:
        return {"error": "FFmpeg binary not found."}

def analyze_compliance(video_path, output_path, target_lufs=-23.0, tolerance=1.0):
    raw_data = get_ffmpeg_loudness(video_path)
    
    if "error" in raw_data:
        print(f"[ERROR] {raw_data['error']}")
        return

    try:
        input_i = float(raw_data.get("input_i", -99.0))
        input_tp = float(raw_data.get("input_tp", 99.0)) 
        input_lra = float(raw_data.get("input_lra", 0.0))
    except (ValueError, TypeError):
         print("[ERROR] Invalid FFmpeg data")
         return

    is_compliant = (target_lufs - tolerance) <= input_i <= (target_lufs + tolerance)
    
    status = "PASSED" if is_compliant else "REJECTED"
    events = []

    if status == "REJECTED":
        events.append({
            "type": "loudness_violation",
            "start_time": 0.0,
            "end_time": 0.0,
            "confidence": 1.0,
            "details": {
                "measured_lufs": input_i,
                "target_lufs": target_lufs,
                "correction_needed_db": round(target_lufs - input_i, 2)
            }
        })

    unified_report = {
        "module": "audio_qc",
        "video_file": video_path,
        "status": status,
        "events": events
    }

    with open(output_path, "w") as f:
        json.dump(unified_report, f, indent=4)
        print(f"[Audio QC] Report saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio QC: EBU R.128 Validator")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", required=True, help="Path to save JSON report")
    
    args = parser.parse_args()
    analyze_compliance(args.input, args.output)