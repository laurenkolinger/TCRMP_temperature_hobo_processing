#!/usr/bin/env python3
"""
GENERATE_METADATA.PY - Integrated Metadata Generation

Generates comprehensive DATASET files from processing logs.

This script:
1. Reads processing logs (JSON) for each site/deployment
2. Loads all Details files mentioned in logs
3. Extracts site metadata from YAML files
4. Checks for TOREVIEW status and prompts for resolution
5. Generates ONE DATASET file per final output (not per logger)
6. Embeds all logger Details in the DATASET file
7. Includes complete processing history with timestamps

Run after NCPLOT.py to generate final metadata documentation.
"""

import pandas as pd
import os
import yaml
import re
import glob
import json
from datetime import datetime
from pathlib import Path

# Set paths from config
from config import CONFIG, get_path_for
from processing_logger import ProcessingLogger

hobo_out_folder = get_path_for("01_HOBO_OUT")
ready_folder = get_path_for("05_READY")
metadata_output = get_path_for("07_METADATA")
log_dir = get_path_for("07_METADATA/processing_logs")
site_metadata_folder = os.path.join(CONFIG['WORKFLOW_DIRECTORY'], "Site_Metadata")
template_folder = os.path.join(os.path.dirname(CONFIG['BASE_DIRECTORY']), "misc", "templates")

# Load template
template_path = os.path.join(template_folder, "DATASET-BT_Template.txt")

def load_template():
    """Load the DATASET template file."""
    with open(template_path, 'r') as f:
        return f.read()

def get_site_metadata(site_code):
    """Load site metadata from YAML file."""
    yaml_file = os.path.join(site_metadata_folder, f"{site_code}.yaml")
    
    if not os.path.exists(yaml_file):
        print(f"[WARN] Site metadata file not found for {site_code}")
        return None
    
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    
    return data.get(site_code, {}).get('global_attributes', {})

def load_processing_log(site_code, start_yymm):
    """Load processing log JSON for a site/deployment."""
    log_file = os.path.join(log_dir, f"{site_code}_{start_yymm}.json")
    if not os.path.exists(log_file):
        return None
    
    with open(log_file, 'r') as f:
        return json.load(f)

def read_details_file(details_path):
    """Read a Details.txt file."""
    if not os.path.exists(details_path):
        return f"Details file not found: {os.path.basename(details_path)}"
    
    with open(details_path, 'r') as f:
        return f.read()

def format_serial_numbers(log_data):
    """
    Format serial numbers from log data.
    Returns formatted string with context (e.g., "21958083, 20733084 (duplicate loggers, averaged)")
    """
    serials = [f["serial"] for f in log_data["input_files"] if f.get("serial")]
    
    if not serials:
        return "Unknown"
    
    serial_str = ", ".join(serials)
    
    # Add context about how they were processed
    method = None
    for step in log_data.get("processing_steps", []):
        if step["step"] == "AVERAGING":
            method = step.get("method")
            break
    
    if method == "duplicate_average":
        return f"{serial_str} (duplicate loggers, averaged)"
    elif method == "offset_merge":
        return f"{serial_str} (offset loggers, merged)"
    elif method == "single":
        return serial_str
    else:
        return serial_str

def format_processing_history(log_data):
    """Format processing history from log data into readable text."""
    history_lines = []
    
    for step in log_data.get("processing_steps", []):
        timestamp = step.get("timestamp", "")
        step_name = step.get("step", "")
        action = step.get("action", "")
        details = step.get("details", "")
        
        line = f"- {timestamp} | {step_name} | {action}"
        if details:
            line += f" ({details})"
        
        history_lines.append(line)
    
    return "\n".join(history_lines) if history_lines else "No processing history available"

def format_logger_details(log_data, hobo_out_folder):
    """
    Format all logger Details content for embedding in DATASET.
    Returns formatted string with each logger's full Details content.
    """
    details_sections = []
    
    for i, input_file in enumerate(log_data.get("input_files", []), 1):
        filename = input_file.get("filename", "")
        serial = input_file.get("serial", "Unknown")
        
        # Find corresponding Details file
        # Remove .csv and add _Details.txt
        base_name = filename.replace('.csv', '')
        details_pattern = os.path.join(hobo_out_folder, f"{base_name}_Details.txt")
        
        # Also try without identifier (for single files)
        if not glob.glob(details_pattern):
            # Try pattern like BT_TCBKIT_2410_Details.txt (no _a or _b)
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 4:
                alt_pattern = f"{parts[0]}_{parts[1]}_{parts[2]}_Details.txt"
                details_pattern = os.path.join(hobo_out_folder, alt_pattern)
        
        details_files = glob.glob(details_pattern)
        
        if details_files:
            details_content = read_details_file(details_files[0])
        else:
            details_content = f"Details file not found for {filename}"
        
        section = f"--- Logger {i} (Serial: {serial}) ---\n"
        section += f"File: {filename}\n"
        section += f"Samples (trimmed): {input_file.get('samples_trimmed', 'Unknown')}\n\n"
        section += details_content
        
        details_sections.append(section)
    
    return "\n\n".join(details_sections) if details_sections else "No logger details available"

def generate_merge_average_note(log_data):
    """Generate the merge/average note for the Data Processing section."""
    method = None
    details = ""
    
    for step in log_data.get("processing_steps", []):
        if step["step"] == "AVERAGING":
            method = step.get("method")
            details = step.get("details", "")
            break
    
    if method == "duplicate_average":
        serials = [f["serial"] for f in log_data["input_files"] if f.get("serial")]
        note = f"Records from probe 1 (Serial: {serials[0]}) and probe 2 (Serial: {serials[1]}) were averaged.\n"
        if details:
            note += f"Temperature comparison: {details}.\n"
        return note
    elif method == "offset_merge":
        serials = [f["serial"] for f in log_data["input_files"] if f.get("serial")]
        return f"Records from offset loggers (Serials: {', '.join(serials)}) were merged.\n"
    elif method == "single":
        return "Single logger deployment.\n"
    else:
        return ""

def generate_qc_notes(log_data):
    """Generate QC notes including review status if applicable."""
    review_status = log_data.get("review_status")
    
    if review_status == "RESOLVED":
        notes = "Quality check: FLAGGED FOR REVIEW - RESOLVED\n"
        notes += f"Review reason: {log_data.get('review_reason', 'Not specified')}\n"
        notes += f"Resolution: {log_data.get('user_notes', 'No notes provided')}\n"
        return notes
    elif review_status == "NEEDS_REVIEW":
        notes = "Quality check: FLAGGED FOR REVIEW - PENDING\n"
        notes += f"Review reason: {log_data.get('review_reason', 'Not specified')}\n"
        return notes
    else:
        return "Quality check: PASSED - No issues detected.\n"

def prompt_user_input(prompt_text, default_value=""):
    """Prompt user for input with optional default."""
    if default_value:
        user_input = input(f"{prompt_text} [{default_value}]: ").strip()
        return user_input if user_input else default_value
    else:
        return input(f"{prompt_text}: ").strip()

def read_csv_dates(csv_path):
    """Read CSV file to get actual start and end dates."""
    try:
        df = pd.read_csv(csv_path)
        date_col = [col for col in df.columns if 'Date Time' in col][0]
        df[date_col] = pd.to_datetime(df[date_col])
        
        start_date = df[date_col].min().strftime('%B %d, %Y')
        end_date = df[date_col].max().strftime('%B %d, %Y')
        
        return start_date, end_date
    except Exception as e:
        print(f"[WARN] Could not read CSV dates: {e}")
        return None, None

def generate_dataset_file(log_data):
    """Generate comprehensive DATASET file from processing log."""
    site_code = log_data["site_code"]
    start_yymm = log_data["start_yymm"]
    final_filename = log_data.get("final_filename")
    
    if not final_filename:
        print(f"[ERROR] No final filename in log for {site_code}_{start_yymm}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Generating metadata for: {final_filename}")
    print(f"{'='*60}")
    
    # Load site metadata
    site_meta = get_site_metadata(site_code)
    if not site_meta:
        print(f"[ERROR] Could not load site metadata for {site_code}")
        return False
    
    # Extract site information
    site_full_name = site_meta.get('location', site_code)
    coords = site_meta.get('coordinates', '')
    latitude = coords.split(',')[0].strip() if coords else ''
    longitude = coords.split(',')[1].strip() if coords and ',' in coords else ''
    depth = site_meta.get('depth', 'Unknown')
    site_description = site_meta.get('site_description', '')
    
    # Get dates from final CSV
    csv_path = os.path.join(ready_folder, final_filename)
    start_date, end_date = read_csv_dates(csv_path)
    
    if not start_date or not end_date:
        start_date = "Unknown"
        end_date = "Unknown"
    
    # Check for TOREVIEW status
    review_status = log_data.get("review_status")
    if review_status == "NEEDS_REVIEW":
        print(f"\n[FLAG] This file was flagged for review!")
        print(f"Reason: {log_data.get('review_reason', 'Not specified')}")
        print()
        user_notes = prompt_user_input(
            "How was this resolved?\n(Describe what was done - e.g., used only logger A, manually trimmed data, etc.)",
            ""
        )
        
        if user_notes:
            # Update log with resolution
            logger = ProcessingLogger(site_code, start_yymm, log_dir)
            logger.resolve_review(user_notes)
            log_data = logger.get_log()  # Reload updated log
    
    # Get sensor deployment info
    sensor_deployment_info = prompt_user_input(
        "Enter sensor deployment info (or press Enter to skip)",
        ""
    )
    
    # Get creator name
    created_by = prompt_user_input("Enter your name", os.getenv('USER', 'Unknown'))
    created_date = datetime.now().strftime('%B %d, %Y')
    
    # Load template
    template = load_template()
    
    # Fill template
    dataset_content = template
    dataset_content = dataset_content.replace('{{SITE_FULL_NAME}}', site_full_name)
    dataset_content = dataset_content.replace('{{START_DATE}}', start_date)
    dataset_content = dataset_content.replace('{{END_DATE}}', end_date)
    dataset_content = dataset_content.replace('{{DATASET_FILENAME}}', final_filename)
    dataset_content = dataset_content.replace('{{LATITUDE}}', latitude)
    dataset_content = dataset_content.replace('{{LONGITUDE}}', longitude)
    dataset_content = dataset_content.replace('{{DEPTH}}', str(depth))
    dataset_content = dataset_content.replace('{{SERIAL_NUMBERS}}', format_serial_numbers(log_data))
    dataset_content = dataset_content.replace('{{SITE_DESCRIPTION}}', site_description)
    dataset_content = dataset_content.replace('{{SENSOR_DEPLOYMENT_INFO}}', sensor_deployment_info)
    dataset_content = dataset_content.replace('{{MERGE_AVERAGE_NOTE}}', generate_merge_average_note(log_data))
    dataset_content = dataset_content.replace('{{QC_NOTES}}', generate_qc_notes(log_data))
    
    # Processing workflow details
    dataset_content = dataset_content.replace('{{WORKFLOW_VERSION}}', CONFIG.get('FRAMEWORK_VERSION', '1.0'))
    dataset_content = dataset_content.replace('{{PROCESSING_LOCATION}}', log_data.get('processing_location', 'Unknown'))
    dataset_content = dataset_content.replace('{{PROCESSING_DATE}}', datetime.now().strftime('%B %d, %Y'))
    
    # Config parameters
    config_params = log_data.get('config_parameters', {})
    dataset_content = dataset_content.replace('{{TEMP_THRESHOLD}}', str(config_params.get('temp_threshold', 0.2)))
    dataset_content = dataset_content.replace('{{BUFFER_HOURS}}', str(config_params.get('deployment_buffer_hours', 1)))
    dataset_content = dataset_content.replace('{{TRIM_START}}', str(config_params.get('trim_start_points', 4)))
    dataset_content = dataset_content.replace('{{TRIM_END}}', str(config_params.get('trim_end_points', 5)))
    dataset_content = dataset_content.replace('{{TIMEZONE}}', config_params.get('expected_timezone', 'GMT-04:00'))
    
    # Processing history
    dataset_content = dataset_content.replace('{{PROCESSING_HISTORY}}', format_processing_history(log_data))
    
    # Logger details (embeds all Details files)
    dataset_content = dataset_content.replace('{{LOGGER_DETAILS}}', format_logger_details(log_data, hobo_out_folder))
    
    # For backwards compatibility, add Details content to Related Files section too
    dataset_content = dataset_content.replace('{{DETAILS_CONTENT}}', format_logger_details(log_data, hobo_out_folder))
    
    # Creator info
    dataset_content = dataset_content.replace('{{CREATED_BY}}', created_by)
    dataset_content = dataset_content.replace('{{CREATED_DATE}}', created_date)
    
    # Save DATASET file (ONE file for the final output)
    dataset_filename_out = final_filename.replace('.csv', '.txt')
    dataset_filename_out = f"DATASET_{dataset_filename_out}"
    dataset_path = os.path.join(metadata_output, dataset_filename_out)
    
    with open(dataset_path, 'w') as f:
        f.write(dataset_content)
    
    print(f"[OK] Saved: {dataset_filename_out}")
    
    # Add final processing step to log
    logger = ProcessingLogger(site_code, start_yymm, log_dir)
    logger.add_processing_step(
        step_name="GENERATE_METADATA",
        action="Compiled comprehensive metadata",
        details=f"Generated from {len(log_data.get('input_files', []))} logger(s)",
        outputs=["DATASET file"]
    )
    
    return True

def main():
    """Main function to generate all metadata files."""
    print("\n" + "="*60)
    print("METADATA GENERATION - Comprehensive DATASET Files")
    print("="*60 + "\n")
    
    # Get all processing logs
    log_files = glob.glob(os.path.join(log_dir, "*.json"))
    
    if not log_files:
        print(f"[WARN] No processing logs found in {log_dir}")
        return
    
    print(f"[OK] Found {len(log_files)} processing log(s)\n")
    
    # Process each log that has a final filename (meaning it completed successfully)
    success_count = 0
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            
            # Only generate metadata if there's a final filename
            if log_data.get("final_filename"):
                if generate_dataset_file(log_data):
                    success_count += 1
            else:
                print(f"[SKIP] Skipping {os.path.basename(log_file)} - no final output (may have been flagged)")
        
        except Exception as e:
            print(f"[ERROR] Error processing {os.path.basename(log_file)}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"COMPLETE: Generated {success_count} DATASET file(s)")
    print(f"Output directory: {metadata_output}")
    print(f"{'='*60}\n")
    
    # Export metadata files to external location if configured
    export_path = CONFIG.get('EXPORT_METADATA_PATH', '')
    if export_path and os.path.exists(export_path):
        print(f"\n[EXPORT] Exporting metadata files to: {export_path}")
        import shutil
        
        metadata_files = glob.glob(os.path.join(metadata_output, "DATASET_*.txt"))
        exported_count = 0
        
        for metadata_file in metadata_files:
            basename = os.path.basename(metadata_file)
            dest_path = os.path.join(export_path, basename)
            shutil.copy2(metadata_file, dest_path)
            exported_count += 1
            print(f"  [OK] Exported: {basename}")
        
        print(f"\n[OK] Exported {exported_count} metadata file(s)")
    elif export_path:
        print(f"\n[WARN] Export path configured but does not exist: {export_path}")
        print("   Skipping export. Create the directory to enable export.")
    else:
        print("\n[SKIP] No export path configured for metadata files (test mode)")

if __name__ == "__main__":
    main()
