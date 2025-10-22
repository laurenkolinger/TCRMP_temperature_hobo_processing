#!/usr/bin/env python3
"""
Configuration File for Automated Temperature Monitoring Framework
================================================================

Update this configuration file before running the setup script.
The setup script will read these parameters to:
1. Create the directory structure
2. Set up virtual environment
3. Install dependencies
4. Generate a config snapshot

INSTRUCTIONS:
1. Update the BASE_DIRECTORY to where you want the framework installed
2. Modify YEARS to include the monitoring years you need
3. Update MONITORING_TYPES if you have different monitoring categories
4. Adjust processing parameters as needed
5. Run: python src/setup.py
"""

import os
from datetime import datetime

# Base directory relative to src folder (parent of src)
#BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

"""
BASE DIRECTORY CHANGE - TBA
"""
# Instead of basing off src, locate SCRIPTED_WORKFLOW and replace with SCRIPTED_OUTPUTS
WORKFLOW_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(os.path.dirname(WORKFLOW_DIR), "SCRIPTED_OUTPUTS")

CONFIG = {
    # Directory setup
    'BASE_DIRECTORY': BASE_DIR,
    'WORKFLOW_DIRECTORY': WORKFLOW_DIR,
    'YEARS': ['LaurenTest_21Oct2025'],
    'MONITORING_TYPES': ['annual'],
    
    # Subdirectories matching 2025/PBL structure
    'AUTO_SUBDIRECTORIES': [
        '01_HOBO_OUT',
        '02_PLOTS/pretrimmed',
        '02_PLOTS/posttrimmed',
        '02_PLOTS/ready', 
        '03_TRIMMED_CSVS',
        '04_TOREVIEW',
        '05_READY',
        '06_NETCDF',
        '07_METADATA/processing_logs',
        '07_METADATA/needs_review',
        'deployment_logs',
        'config_snapshots'
    ],
    
    # Virtual environment
    'VENV_NAME': 'temp_monitoring_env',
    'PYTHON_VERSION_REQUIRED': '3.8',
    'REQUIREMENTS_FILE': 'requirements.txt',
    
    # Processing parameters
    'TEMPERATURE_DIFFERENCE_THRESHOLD': 0.2,
    'TEMPERATURE_ANOMALY_THRESHOLD': 0.4,
    'DEPLOYMENT_BUFFER_HOURS': 1,
    'TRIM_START_POINTS': 4,
    'TRIM_END_POINTS': 5,
    'EXPECTED_TIMEZONE': 'GMT-04:00',
    
    # File validation
    # This is a regular expression pattern used to validate or extract information from filenames. It matches CSV files named like BT_<SITE><digits>_<YEAR>_<a|b>.csv, where:
    # BT_ is a fixed prefix,
    # ([A-Z]+\d*) captures the site code (letters, possibly followed by digits),
    # (\d{4}) captures a 4-digit year,
    # ([ab]?) optionally captures a single 'a' or 'b' (for replicate or version),
    # .csv is the file extension.
    # This ensures files follow a strict naming convention for processing.
    'FILENAME_PATTERN': r'BT_([A-Z]+\d*)_(\d{4})_?([ab]?)\.csv',

    'REQUIRED_CSV_COLUMNS': [
        'Date Time, GMT-04:00',
        'Temp, °C',
        '#'
    ],
    'REQUIRED_DEPLOYMENT_COLUMNS': [
        'Offloaded Filename',
        'Date In',
        'Time In', 
        'Date Out',
        'Time Out',
        'Site Name'
    ],
    
    # Site codes
    'SITE_CODES': [
        "TCCORB", "TCFSHB", "TCMERI", "TCBKPT", "TCBOTB", "TCBRWB", "TCBKIT",
        "TCCORK", "TCCLGE", "TCFLTC", "TCGMKT", "TCHB40", "TCMAGB", "TCSAVA",
        "TCSHCS", "TCSCAP", "TCSC35", "TCSWAT", "TCLSTJ", "TCBKIX", "TCBX33", 
        "TCCB08", "TCCB40", "TCCB67", "TCCSTL", "TCEAGR", "TCGRPD", "TCJCKB", 
        "TCKNGC", "TCLBREM", "TCLBRH", "TCMT24", "TCMT40", "TCSR30", "TCSR41", 
        "TCSR67", "TCSPTH", "TCLE67"
    ],
    
    # Framework metadata
    'FRAMEWORK_VERSION': '1.0',
    'CREATED_DATE': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'CREATED_BY': os.getenv('USER', 'unknown'),
    
    # Export paths for final outputs (leave blank for test runs, set paths for production exports)
    # These paths are used to copy final processed files to a separate location (e.g., database folder)
    'EXPORT_READY_PATH': '',  # Path to export final CSV files from 05_READY/ (e.g., 'path/to/TCRMP_temperature_database')
    'EXPORT_NETCDF_PATH': '',  # Path to export NetCDF files from 06_NETCDF/ (e.g., 'path/to/TCRMP_temperature_nc')
    'EXPORT_METADATA_PATH': '',  # Path to export DATASET files from 07_METADATA/ (e.g., 'path/to/metadata_archive')
    
    # Note: Files flagged for review (04_TOREVIEW) are NEVER exported to these paths
    # Only QC-passed files are exported when paths are configured
}

# Monitoring type configurations
MONITORING_TYPE_CONFIGS = {
    'annual': {
        'DESCRIPTION': 'Annual coral reef monitoring program',
        'EXPECTED_DEPLOYMENT_DURATION_DAYS': (30, 365),
    },
    'PBL': {
        'DESCRIPTION': 'Post-bleaching event monitoring',
        'EXPECTED_DEPLOYMENT_DURATION_DAYS': (7, 180),
        'TEMPERATURE_DIFFERENCE_THRESHOLD': 0.15,
    }
}

def get_directory_structure():
    """Generate the complete directory structure that will be created."""
    structure = {}
    base = CONFIG['BASE_DIRECTORY']
    
    for year in CONFIG['YEARS']:
        for monitoring_type in CONFIG['MONITORING_TYPES']:
            for subdir in CONFIG['AUTO_SUBDIRECTORIES']:
                path = os.path.join(base, str(year), monitoring_type, subdir)
                structure[path] = subdir
    
    return structure

if __name__ == "__main__":
    print("Temperature Monitoring Framework Configuration")
    print("=" * 50)
    print(f"Base Directory: {CONFIG['BASE_DIRECTORY']}")
    print(f"Years: {', '.join(map(str, CONFIG['YEARS']))}")
    print(f"Monitoring Types: {', '.join(CONFIG['MONITORING_TYPES'])}")
    print(f"Virtual Environment: {CONFIG['VENV_NAME']}")
    
    structure = get_directory_structure()
    print(f"\nWill create {len(structure)} directories")
    print("Run: python src/setup.py")


# This function is to be used in scripts to pull the folder paths created by the config file
def get_path_for(subfolder: str, year=None, monitoring_type=None):
    """
    Returns the full path to a given subfolder based on year and monitoring type.
    Defaults to the first year and monitoring type in CONFIG if not specified.
    """
    year = year or CONFIG['YEARS'][0]
    monitoring_type = monitoring_type or CONFIG['MONITORING_TYPES'][0]
    return os.path.join(CONFIG['BASE_DIRECTORY'], year, monitoring_type, subfolder)
