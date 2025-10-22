#!/usr/bin/env python3
"""
Processing Logger for Temperature Monitoring Workflow

Centralized logging system to track all workflow steps, creating an audit trail
of all processing decisions, parameters, and timestamps.
"""

import json
import os
from datetime import datetime
from pathlib import Path

class ProcessingLogger:
    """
    Manages processing logs for temperature data workflow.
    
    Each site/deployment combination gets one log file that tracks
    the entire processing history from raw data to final output.
    """
    
    def __init__(self, site_code, start_yymm, log_dir, config=None):
        """
        Initialize processing logger.
        
        Args:
            site_code: Site code (e.g., 'TCBKPT')
            start_yymm: Start year-month (e.g., '2410')
            log_dir: Directory to store log files
            config: CONFIG dict with processing parameters
        """
        self.site_code = site_code
        self.start_yymm = start_yymm
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / f"{site_code}_{start_yymm}.json"
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load log
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                self.log_data = json.load(f)
        else:
            self.log_data = {
                "site_code": site_code,
                "start_yymm": start_yymm,
                "end_yymm": None,
                "final_filename": None,
                "input_files": [],
                "processing_location": str(Path(log_dir).parent.parent),
                "config_parameters": {},
                "processing_steps": [],
                "review_status": None,
                "review_reason": None,
                "user_notes": ""
            }
            
            # Store config parameters if provided
            if config:
                self.log_data["config_parameters"] = {
                    "temp_threshold": config.get('TEMPERATURE_DIFFERENCE_THRESHOLD', 0.2),
                    "deployment_buffer_hours": config.get('DEPLOYMENT_BUFFER_HOURS', 1),
                    "trim_start_points": config.get('TRIM_START_POINTS', 4),
                    "trim_end_points": config.get('TRIM_END_POINTS', 5),
                    "expected_timezone": config.get('EXPECTED_TIMEZONE', 'GMT-04:00')
                }
    
    def add_input_file(self, filename, serial_number=None, samples_original=None):
        """
        Add an input file to the log.
        
        Args:
            filename: Input filename
            serial_number: Logger serial number
            samples_original: Original sample count
        """
        file_entry = {
            "filename": filename,
            "serial": serial_number,
            "samples_original": samples_original,
            "samples_trimmed": None
        }
        
        # Check if file already exists in log
        existing = [f for f in self.log_data["input_files"] if f["filename"] == filename]
        if not existing:
            self.log_data["input_files"].append(file_entry)
        
        self.save()
    
    def update_input_file(self, filename, **kwargs):
        """
        Update information for an input file.
        
        Args:
            filename: Filename to update
            **kwargs: Fields to update (serial, samples_original, samples_trimmed)
        """
        for file_entry in self.log_data["input_files"]:
            if file_entry["filename"] == filename:
                file_entry.update(kwargs)
                break
        self.save()
    
    def add_processing_step(self, step_name, action, details="", method=None, outputs=None):
        """
        Add a processing step to the log.
        
        Args:
            step_name: Name of the script (e.g., 'TRIM_PLOT')
            action: Short description of action taken
            details: Detailed information about the step
            method: Method used (e.g., 'duplicate_average', 'merge')
            outputs: List of outputs generated
        """
        step_entry = {
            "step": step_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "action": action,
            "details": details
        }
        
        if method:
            step_entry["method"] = method
        if outputs:
            step_entry["outputs"] = outputs
        
        self.log_data["processing_steps"].append(step_entry)
        self.save()
    
    def set_final_filename(self, filename):
        """Set the final output filename."""
        self.log_data["final_filename"] = filename
        # Extract end_yymm from filename if not set
        if not self.log_data["end_yymm"] and "_" in filename:
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 4:
                self.log_data["end_yymm"] = parts[3]
        self.save()
    
    def flag_for_review(self, reason):
        """
        Flag this dataset for review.
        
        Args:
            reason: Reason for flagging (e.g., 'Temperature difference exceeded threshold')
        """
        self.log_data["review_status"] = "NEEDS_REVIEW"
        self.log_data["review_reason"] = reason
        
        # Create needs_review flag file
        needs_review_dir = self.log_dir.parent / "needs_review"
        needs_review_dir.mkdir(parents=True, exist_ok=True)
        
        flag_file = needs_review_dir / f"{self.site_code}_{self.start_yymm}.txt"
        with open(flag_file, 'w') as f:
            f.write(f"FLAGGED FOR REVIEW\n")
            f.write(f"Site: {self.site_code}\n")
            f.write(f"Deployment: {self.start_yymm}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"\nFiles involved:\n")
            for file_entry in self.log_data["input_files"]:
                f.write(f"  - {file_entry['filename']}\n")
            f.write(f"\nAction needed: Review and provide resolution notes in GENERATE_METADATA.py\n")
        
        self.save()
    
    def resolve_review(self, user_notes):
        """
        Mark review as resolved with user notes.
        
        Args:
            user_notes: User-provided resolution notes
        """
        self.log_data["review_status"] = "RESOLVED"
        self.log_data["user_notes"] = user_notes
        
        # Remove needs_review flag file
        needs_review_dir = self.log_dir.parent / "needs_review"
        flag_file = needs_review_dir / f"{self.site_code}_{self.start_yymm}.txt"
        if flag_file.exists():
            flag_file.unlink()
        
        self.save()
    
    def save(self):
        """Save log to JSON file."""
        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2)
    
    def get_log(self):
        """Return the complete log data."""
        return self.log_data
    
    @staticmethod
    def load_log(log_file):
        """
        Load an existing log file.
        
        Args:
            log_file: Path to log file
            
        Returns:
            Log data dict or None if file doesn't exist
        """
        log_path = Path(log_file)
        if log_path.exists():
            with open(log_path, 'r') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def find_log_for_file(filename, log_dir):
        """
        Find the log file for a given input/output filename.
        
        Args:
            filename: Filename to search for
            log_dir: Directory containing log files
            
        Returns:
            Path to log file or None
        """
        log_dir = Path(log_dir)
        if not log_dir.exists():
            return None
        
        # Extract site code and start date from filename
        # Format: BT_SITECODE_YYMM_... or BT_SITECODE_YYMM_YYMM.csv
        import re
        match = re.match(r'BT_([A-Z]+\d*)_(\d{4})', filename)
        if match:
            site_code = match.group(1)
            start_yymm = match.group(2)
            log_file = log_dir / f"{site_code}_{start_yymm}.json"
            if log_file.exists():
                return log_file
        
        return None


def get_logger(site_code, start_yymm, log_dir, config=None):
    """
    Convenience function to get or create a ProcessingLogger.
    
    Args:
        site_code: Site code
        start_yymm: Start year-month
        log_dir: Log directory
        config: CONFIG dict
        
    Returns:
        ProcessingLogger instance
    """
    return ProcessingLogger(site_code, start_yymm, log_dir, config)

