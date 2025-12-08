import argparse
import json
import os
import sys

def merge_reports(report_paths):
    master_report = {
        "overall_status": "PASSED",
        "modules_run": 0,
        "timeline": []
    }

    print("--- Aggregating Reports ---")

    for path in report_paths:
        # Graceful Degradation: Skip missing files
        if not os.path.exists(path):
            print(f"[WARN] Report not found: {path}. Skipping.")
            continue

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            module_name = data.get("module", "unknown")
            status = data.get("status", "UNKNOWN")
            events = data.get("events", [])

            print(f"[INFO] Merging {module_name}... Status: {status}")

            # 1. Update Overall Status
            # If ANY module fails, the whole asset is REJECTED
            if status == "REJECTED":
                master_report["overall_status"] = "REJECTED"

            # 2. Merge Events into Timeline
            # Add 'source_module' to each event for clarity
            for event in events:
                event["source_module"] = module_name
                master_report["timeline"].append(event)

            master_report["modules_run"] += 1

        except Exception as e:
            print(f"[ERROR] Failed to parse {path}: {e}")

    # 3. Sort Timeline Chronologically
    master_report["timeline"] = sorted(
        master_report["timeline"], 
        key=lambda x: x.get("start_time", 0.0)
    )

    return master_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregator: Generate Master QC Report")
    parser.add_argument("--inputs", nargs='+', required=True, help="List of JSON report paths")
    parser.add_argument("--output", default="Master_Report.json", help="Output file path")

    args = parser.parse_args()

    final_data = merge_reports(args.inputs)

    with open(args.output, "w", encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n[SUCCESS] Master Report generated: {args.output}")
    print(f"Overall Status: {final_data['overall_status']}")