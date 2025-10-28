# HOBO Temperature Data Processing Workflow

**Automated Quality Assurance/Quality Control (QAQC) Framework for Temperature Monitoring Data**

Version 1.0 | TCRMP Temperature Monitoring Program

Code Authors: Cole Sheeley, Travis Hamlin (UVI)

Code Reviewer: Lauren Olinger (UVI)


---

## Table of Contents


1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
   * [System Requirements](#system-requirements)
   * [Software Installation](#software-installation)
   * [Initial Setup](#initial-setup)
3. [Quick Start Guide](#quick-start-guide)
4. [Detailed Workflow](#detailed-workflow)
   * [Step 1: Configuration](#step-1-configuration)
   * [Step 2: Framework Setup](#step-2-framework-setup)
   * [Step 3: Data Preparation](#step-3-data-preparation)
   * [Step 4: Data Processing](#step-4-data-processing)
   * [Step 5: Final Export](#step-5-final-export)
5. [Testing with Example Data](#testing-with-example-data)
6. [Troubleshooting](#troubleshooting)
7. [Technical Appendix](#technical-appendix)


---

## Overview

This framework provides an automated system for processing HOBO temperature logger data through quality control checks, trimming, averaging, and NetCDF conversion. The workflow is designed for the Territorial Coral Reef Monitoring Program (TCRMP) but can be adapted for other temperature monitoring projects.

**What This Framework Does:**

* Validates and organizes raw HOBO data files
* Cross-references data with deployment logs
* Trims data to deployment periods
* Averages duplicate loggers
* Detects temperature drift between paired sensors
* Generates quality control plots
* Creates standardized NetCDF files with metadata

**Directory Structure Created:**

```
SCRIPTED_OUTPUTS/
├── [Year]/                     # e.g., 2025, LaurenTest_21Oct2025
│   └── [MonitoringType]/       # e.g., annual, PBL
│       ├── 01_HOBO_OUT/        # Raw HOBO data files
│       ├── 02_PLOTS/           # QC visualization plots
│       │   ├── pretrimmed/     # Plots before trimming
│       │   ├── posttrimmed/    # Plots after trimming
│       │   └── ready/          # Final plots
│       ├── 03_TRIMMED_CSVS/    # Data trimmed to deployment dates
│       ├── 04_TOREVIEW/        # Files flagged for manual review
│       ├── 05_READY/           # Processed, QC-passed data
│       ├── 06_NETCDF/          # Final NetCDF files
│       ├── 07_METADATA/        # DATASET and DETAILS files
│       ├── deployment_logs/    # Deployment metadata
│       └── config_snapshots/   # Configuration backups
```


---

## Prerequisites

### System Requirements

* **Operating System**: macOS, Windows, or Linux
* **Python Version**: 3.8 or higher
* **Disk Space**: At least 500 MB for dependencies and data processing
* **Memory**: 4 GB RAM minimum (8 GB recommended)

### Software Installation

#### 1. Install Python

**Check if Python is installed:**

```bash
python3 --version
```

If Python is not installed or version is below 3.8:

* **macOS**: Download from [python.org](https://www.python.org/downloads/) or use Homebrew:

  ```bash
  brew install python3
  ```
* **Windows**: Download from [python.org](https://www.python.org/downloads/)
  * During installation, check "Add Python to PATH"
* **Linux**: Install via package manager:

   ```bash
  sudo apt-get install python3 python3-pip  # Ubuntu/Debian
  sudo yum install python3 python3-pip      # CentOS/RHEL
  ```

#### 2. Install a Python IDE (Recommended)

**Visual Studio Code (VS Code)** - Recommended for beginners

* Download: [code.visualstudio.com](https://code.visualstudio.com/)
* After installation, install the Python extension:

  
  1. Open VS Code
  2. Click Extensions icon (left sidebar)
  3. Search for "Python"
  4. Install the extension by Microsoft

**Alternative IDEs:**

* PyCharm: [jetbrains.com/pycharm](https://www.jetbrains.com/pycharm/)
* Jupyter Notebook: `pip install jupyter`

#### 3. Install Dropbox Desktop App

For easier file access and automatic syncing:

* Download: [dropbox.com/install](https://www.dropbox.com/install)
* Sign in with the account that has access to the [Smith lab temperature processing folder](https://www.dropbox.com/scl/fo/dgrnk4cig12exudmjo09d/AIsUfaH4tC53NMz-6pO2Cug?rlkey=r6bkb3hbetgf2quc25qbjdss4&dl=0).
* Synchronize the files in that temperature processing folder to your local directory.

  \


:::warning
Ensure that Step 1 and Step 2 in the [SOP](https://www.dropbox.com/scl/fi/ijaqis7qcdjjoi6jagq14/SOP-Temperature-TCRMP-QAQC.docx?rlkey=7c1j06o35lfoulgw6z17ax7u1&dl=0) have been completed before proceeding!

:::

#### Navigate to the Project Directory


1. **Open Terminal/Command Prompt**
   * macOS: Applications → Utilities → Terminal
   * Windows: Press `Win + R`, type `cmd`, press Enter
   * Linux: Use your distribution's terminal application

     \
2. **Navigate to the SCRIPTED_WORKFLOW directory**

   The general path structure is:

   ```
   Dropbox/SMITH LAB TEAM FOLDER/TCRMP/TCRMP_temperature/TCRMP_temperature_hobo_processing/SCRIPTED_WORKFLOW
   ```

   **On macOS:**

   ```bash
   cd ~/Dropbox/SMITH\ LAB\ TEAM\ FOLDER/TCRMP/TCRMP_temperature/TCRMP_temperature_hobo_processing/SCRIPTED_WORKFLOW
   ```

   **On Windows:**

   ```cmd
   cd %USERPROFILE%\Dropbox\SMITH LAB TEAM FOLDER\TCRMP\TCRMP_temperature\TCRMP_temperature_hobo_processing\SCRIPTED_WORKFLOW
   ```

   **Tips:**
   * Use `Tab` key for auto-completion
   * Use `ls` (macOS/Linux) or `dir` (Windows) to list directory contents
   * Use `pwd` (macOS/Linux) or `cd` (Windows) to show current directory
3. **Verify you're in the correct directory**

   ```bash
   ls src/  # Should show: config.py, setup.py, TRIM_PLOT.py, etc.
   ```


---

## Quick Start Guide

For experienced users or subsequent runs:

   ```bash
# 1. Navigate to project directory
cd path/to/SCRIPTED_WORKFLOW

# 2. Edit configuration 
nano src/config.py  # or use your preferred editor
# Set YEARS, MONITORING_TYPES, and optionally configure export paths.
# Leave export paths blank for test runs.

# 3. Run setup
python3 src/setup.py
# Creates directory structure and virtual environment (removes old venv if exists).

# 4. Copy HOBO files to appropriate directory
# Place .csv and _Details.txt files exported from HOBOware into:
# SCRIPTED_OUTPUTS/[year]/[monitoring_type]/01_HOBO_OUT/

# 5. Activate virtual environment
source temp_monitoring_env/bin/activate  # macOS/Linux
   # OR
   temp_monitoring_env\Scripts\activate     # Windows

# 6. Run processing scripts in order
python3 src/TRIM_PLOT.py          # Trims data to deployment periods
python3 src/AVERAGING.py          # Averages duplicates, flags issues (exports CSVs if configured)
python3 src/NCPLOT.py             # Generates NetCDF and plots (exports if configured)
python3 src/GENERATE_METADATA.py  # Creates DATASET files (exports if configured)

# 7. Review outputs
# Check 04_TOREVIEW for flagged files (NEVER exported)
# QC-passed files in 05_READY, 06_NETCDF, 02_PLOTS/ready/, 07_METADATA
# If export paths configured, files automatically organized into site subfolders
```


---

## Detailed Workflow

### Step 1: Configuration

**Purpose**: Set up the framework parameters for your specific monitoring season and data.

#### 1.1 Edit the Configuration File

Open the configuration file in your text editor or IDE:

```bash
code src/config.py  # VS Code
# OR
nano src/config.py  # Terminal editor
```

#### 1.2 Update Required Parameters

**Years** - Set the year(s) or custom identifier for your monitoring period:

```python
'YEARS': ['2025'],  # For calendar year
# OR
'YEARS': ['LaurenTest_21Oct2025'],  # For custom test runs
```

**Monitoring Types** - Specify the type of monitoring:

```python
'MONITORING_TYPES': ['annual'],  # Options: 'annual', 'PBL'
```


1. `annual`: Long-term annual monitoring (30-365 days)
2. `PBL`: Post-bleaching monitoring (7-180 days)
3. other monitoring types can be added, and exist in the TCRMP data.

   \

**Site Codes** - Usually no changes needed. The list includes all valid TCRMP sites:

```python
'SITE_CODES': [
    "TCCORB", "TCFSHB", "TCMERI", "TCBKPT", "TCBOTB", ...
]
```

#### 1.3 Optional Parameters

Not to be changed unless you know what youre doing! For TCRMP regular processing should remain at default values.

**Processing Thresholds**

```python
'TEMPERATURE_DIFFERENCE_THRESHOLD': 0.2,  # Max acceptable difference (°C) between duplicate loggers
'DEPLOYMENT_BUFFER_HOURS': 1,              # Hours to add before/after deployment times
'TRIM_START_POINTS': 4,                    # Number of points to trim from start
'TRIM_END_POINTS': 5,                      # Number of points to trim from end
```

#### 1.4 Export Paths (Optional - For Production Runs)

**Purpose**: Control where final processed files are exported for database integration.

By default, all export paths are blank (empty strings), which means files stay only in `SCRIPTED_OUTPUTS/` - perfect for test runs. For production runs, set these paths to export files organized by site name into subfolders.

```python
# Leave blank for test runs (default)
'EXPORT_READY_PATH': '',
'EXPORT_NETCDF_PATH': '',
'EXPORT_METADATA_PATH': '',
'EXPORT_PLOT_PATH': '',

# For production runs, use relative paths (../ = parent directory):
'EXPORT_READY_PATH': '../TCRMP_temperature_database_csv',
'EXPORT_NETCDF_PATH': '../TCRMP_temperature_nc',
'EXPORT_METADATA_PATH': '../TCRMP_temperature_metadata',
'EXPORT_PLOT_PATH': '../TCRMP_temperature_database_plot',

# Or use absolute paths:
'EXPORT_READY_PATH': '/full/path/to/TCRMP_temperature_database_csv',
```

**Site-Specific Organization:**
All exports are organized into subfolders by site location name (from metadata CSV):
```
TCRMP_temperature_database_csv/
  Black_Point/
    BT_TCBKPT_2410_2503.csv
  Buck_Island_STT/
    BT_TCBKIT_2410_2503.csv

TCRMP_temperature_nc/
  Black_Point/
    BT_TCBKPT_2410_2503.nc

TCRMP_temperature_database_plot/
  Black_Point/
    BT_TCBKPT_2410_2503_plot.png

TCRMP_temperature_metadata/
  Black_Point/
    DATASET_BT_TCBKPT_2410_2503.txt
```

**Critical QC Policy:**
- **ONLY QC-passed files are exported** (from `05_READY/`, `06_NETCDF/`, `02_PLOTS/ready/`, `07_METADATA/`)
- **Files in `04_TOREVIEW/` are NEVER exported** - they must be reviewed and reprocessed first

**Path Requirements:**
- Export directories must exist before running - create them manually or export will be skipped with a warning
- Relative paths (`../folder`) resolve from parent of `SCRIPTED_OUTPUTS/`
- Site subfolders are created automatically

#### 1.5 Preview Configuration

Check your configuration before running setup:

```bash
python3 src/config.py
```

This displays:

* Base directory path
* Years to process
* Monitoring types
* Number of directories to create


---

### Step 2: Framework Setup

**Purpose**: Create the directory structure and set up the Python environment.

#### 2.1 Run the Setup Script

```bash
python3 src/setup.py
```

**What This Does:**


1. Creates a virtual environment (`temp_monitoring_env`)
2. Installs all required Python packages
3. Generates the complete directory structure
4. Creates configuration snapshot files

**Expected Output:**

```
Temperature Monitoring Framework - Setup
========================================
Creating virtual environment: .../temp_monitoring_env
Installing dependencies...
Creating directory structure...
Created 10 directories

SETUP COMPLETE
Framework Location: .../SCRIPTED_OUTPUTS
Virtual Environment: .../temp_monitoring_env

To activate:
  source temp_monitoring_env/bin/activate

Next Steps:
1. Activate virtual environment
2. Place HOBO files in year/monitoring_type/01_HOBO_OUT/
3. Run processing scripts
```

#### 2.2 Verify Directory Structure

Check that directories were created:

```bash
ls ../SCRIPTED_OUTPUTS/[your_year]/[monitoring_type]/
```

You should see:

* `01_HOBO_OUT/`
* `02_PLOTS/` (with subdirectories)
* `03_TRIMMED_CSVS/`
* `04_TOREVIEW/`
* `05_READY/`
* `06_NETCDF/`
* `config_snapshots/`
* `deployment_logs/`


---

### Step 3: Data Preparation

**Purpose**: Place HOBO data files in the correct location for processing.

#### 3.1 Required Files

For each deployment, you need:


1. **CSV file** - Temperature data exported from HOBOware
   * Example: `BT_TCBKPT_2410_a.csv`
2. **Details file** - Metadata text file
   * Example: `BT_TCBKPT_2410_a_Details.txt`
3. **HOBO binary file** (optional, for archiving)
   * Example: `BT_TCBKPT_2410_a.hobo`

#### 3.2 File Naming Convention

Files must follow this pattern:

```
BT_[SITECODE]_[YYMM]_[identifier].csv
```

**Components:**

* `BT_` - Fixed prefix (Bottom Temperature)
* `[SITECODE]` - Site code (e.g., TCBKPT, TCBKIT)
* `[YYMM]` - Year and month deployed (e.g., 2410 = October 2024)
* `[identifier]` - Optional suffix:
  * `_a` / `_b` - Duplicate loggers at same location (will be averaged)
  * `_c` / `_d` - Offset loggers (different depths, will be merged)
  * No suffix - Single logger

**Examples:**

* `BT_TCBKPT_2410_a.csv` - Black Point, Oct 2024, logger A
* `BT_TCBKPT_2410_b.csv` - Black Point, Oct 2024, logger B (duplicate)
* `BT_TCBKIT_2410.csv` - Buck Island STT, Oct 2024, single logger

#### 3.3 Place Files

Copy all files to the `01_HOBO_OUT` directory:

```bash
cp /path/to/your/hobo/files/*.csv ../SCRIPTED_OUTPUTS/[year]/[monitoring_type]/01_HOBO_OUT/
cp /path/to/your/hobo/files/*_Details.txt ../SCRIPTED_OUTPUTS/[year]/[monitoring_type]/01_HOBO_OUT/
```

#### 3.4 Verify Deployment Log

Ensure the deployment log is up to date:

```bash
# Located at:
# TCRMP_temperature_hobo_processing/Temperature_UVI_deployment_log.csv
```

**Required columns in deployment log:**

* `Offloaded Filename` - Must match CSV filename
* `Date In` - Deployment date
* `Time In` - Deployment time
* `Date Out` - Retrieval date
* `Time Out` - Retrieval time
* `Site Name` - Site identifier


---

### Step 4: Data Processing

**Purpose**: Process HOBO data through quality control, trimming, averaging, and NetCDF conversion.

#### 4.1 Activate Virtual Environment

Before running scripts, activate the environment:

**macOS/Linux:**

```bash
source temp_monitoring_env/bin/activate
```

**Windows:**

```cmd
temp_monitoring_env\Scripts\activate
```

You'll see `(temp_monitoring_env)` in your command prompt.


---

#### 4.2 Script 1: TRIM_PLOT.py

**Purpose**: Validate files, cross-check with deployment log, and trim data to deployment periods.

   ```bash
   python3 src/TRIM_PLOT.py
   ```

**Input:**

* Files in `01_HOBO_OUT/`
* `Temperature_UVI_deployment_log.csv`

**Process:**


1. **File Validation**
   * Checks UTF-8 encoding in
   * Validates file naming conventions
   * Verifies required CSV columns exist
   * Identifies duplicate (a/b) and merged (c/d) files
2. **Deployment Log Cross-Reference**
   * Matches CSV files with deployment log entries
   * Validates date/time formats
   * Flags missing or mismatched entries
   * Reports any discrepancies
3. **Data Trimming**
   * Trims data to deployment period (Date In to Date Out)
   * Adds buffer time (default: 1 hour before/after)
   * Removes extra data points at edges
   * Validates trimmed data length
4. **Visualization**
   * Creates pre-trimmed plots (showing full dataset)
   * Creates post-trimmed plots (showing final dataset)
   * Highlights deployment period

**Output:**

* `02_PLOTS/pretrimmed/` - Full data plots
* `02_PLOTS/posttrimmed/` - Trimmed data plots
* `03_TRIMMED_CSVS/` - Trimmed CSV files

**What to Check:**

* Console output shows "✅ All file names matched with deployment log"
* No error messages about missing deployment log entries
* Number of trimmed files matches input files
* Visual inspection of plots shows appropriate trimming

**Example Output:**

```
Found 3 CSV files.
✅ Already UTF-8: BT_TCBKPT_2410_a.csv
✅ Already UTF-8: BT_TCBKPT_2410_b.csv
✅ Already UTF-8: BT_TCBKIT_2410.csv
📥 Reading CSV for site: TCBKPT, file: BT_TCBKPT_2410_a.csv
📥 Reading CSV for site: TCBKPT, file: BT_TCBKPT_2410_b.csv
📥 Reading CSV for site: TCBKIT, file: BT_TCBKIT_2410.csv
✅ All file names matched with deployment log.
Saving trimmed CSV: .../03_TRIMMED_CSVS/BT_TCBKPT_2410_a.csv
Saving trimmed CSV: .../03_TRIMMED_CSVS/BT_TCBKPT_2410_b.csv
Saving trimmed CSV: .../03_TRIMMED_CSVS/BT_TCBKIT_2410.csv
```


---

#### 4.3 Script 2: AVERAGING.py

**Purpose**: Average duplicate loggers and detect temperature drift between merged loggers.

```bash
python3 src/AVERAGING.py
```

**Input:**

* Files in `03_TRIMMED_CSVS/`

**Process:**


1. **Identify File Types**
   * Single files (no identifier or just `_a`)
   * Duplicate files (`_a` and `_b` pairs)
   * Merged files (`_c` and `_d` pairs)
2. **Duplicate Logger Averaging** (for `_a` and `_b` pairs)
   * Compares temperature readings at each timestamp
   * Calculates difference between loggers
   * **If difference ≤ 0.2°C**: Averages the values → `05_READY/`
   * **If difference > 0.2°C**: Flags for review → `04_TOREVIEW/`
   * Creates comparison plots
3. **Merged Logger Drift Detection** (for `_c` and `_d` pairs)
   * Creates agreement plots (logger A vs logger B)
   * Counts points above/below 1:1 line
   * **If balanced**: Merges files → `05_READY/`
   * **If imbalanced** (indicates drift): Flags → `04_TOREVIEW/`
4. **Single File Processing**
   * Passes directly to `05_READY/`
   * No averaging or merging needed

**Output:**

* `05_READY/` - QC-passed files ready for NetCDF conversion
* `04_TOREVIEW/` - Files with issues requiring manual review

**Filename Changes:**

* Input: `BT_TCBKPT_2410_a.csv`, `BT_TCBKPT_2410_b.csv`
* Output: `BT_TCBKPT_2410_2503.csv` (averaged, with end date YYMM)

**What to Check:**

* Verify output files in `05_READY/`
* Check `04_TOREVIEW/` directory for flagged files, review and consult with Tyler (Step 4.4)
* If no files in `04_TOREVIEW/`, proceed to step 4.5.


---

#### 4.4 Manual Review (If Needed)

If files are flagged in `04_TOREVIEW/`:


1. **Review the Plots**
   * Look for systematic bias
   * Check for sensor malfunction
   * Identify outliers or drift
2. **Consult Data Manager**
   * Email flagged files and plots to data manager (Tyler)
   * Describe the issue observed
   * Wait for instructions on how to proceed
3. **Apply Corrections**
   * Follow data manager's instructions
   * May involve:
     * Using only one logger
     * Manual trimming
     * Adjusting thresholds
   * ==Move corrected files to== `05_READY/`
4. **==Re-run if Necessary==**
   * ==If you modify files in== `03_TRIMMED_CSVS/`==, re-run AVERAGING.py==
   * ==If you modify files in== `01_HOBO_OUT/`==, start from TRIM_PLOT.py==


---

#### 4.5 Script 3: NCPLOT.py

**Purpose**: Generate final plots and convert data to NetCDF format with metadata.

```bash
python3 src/NCPLOT.py
```

**Input:**

* Files in `05_READY/`
* ==Site metadata YAML files (==`SCRIPTED_WORKFLOW/Site_Metadata/`==)==
* ==Site metadata CSV (==`TCRMP_TempSiteMetadata.csv`==)==

**Process:**


1. **Load Ready Files**
   * Reads all CSV files from `05_READY/`
   * Parses site codes and date ranges
2. **Generate Final Plots**
   * Creates publication-quality time series plots
   * Includes site name, date range, statistics
   * Saves to `02_PLOTS/ready/`
3. **Prepare Metadata**
   * Loads site-specific YAML metadata
   * Extracts latitude, longitude, depth
   * Adds deployment information
   * Includes data provenance
4. **Create NetCDF Files**
   * Converts CSV to NetCDF format
   * Embeds all metadata as attributes
   * Creates dimensions: time, latitude, longitude
   * Variables: temperature, time
   * Saves to two locations:
     * `06_NETCDF/` (within workflow)
     * `TCRMP_temperature_nc/[Site_Name]/` (external database)

**Output:**

* `02_PLOTS/ready/` - Final publication-quality plots
* `06_NETCDF/` - NetCDF files for archiving
* `TCRMP_temperature_nc/` - NetCDF files organized by site

**NetCDF Metadata Includes:**

* Site coordinates (latitude, longitude)
* Deployment depth
* Time zone (GMT-04:00)
* Data creator and institution
* Processing history
* Quality control flags

**What to Check:**

* Verify NetCDF files created for each site
* Check final plots for accuracy
* Ensure metadata is complete

**Example Output:**

```
Found 2 CSV files.
📥 Reading CSV for site: TCBKPT
📥 Reading CSV for site: TCBKIT
Processing site: TCBKPT
Saved: .../06_NETCDF/BT_TCBKPT_2410_2503.nc
Saved: .../TCRMP_temperature_nc/Black_Point/BT_TCBKPT_2410_2503.nc
Processing site: TCBKIT
Saved: .../06_NETCDF/BT_TCBKIT_2410_2503.nc
Saved: .../TCRMP_temperature_nc/Buck_Island_STT/BT_TCBKIT_2410_2503.nc
```


---

#### 4.6 Script 4: GENERATE_METADATA.py

**Purpose**: Automatically generate DATASET and DETAILS metadata files for database integration.

   ```bash 
python3 src/GENERATE_METADATA.py
```

**Input:**
- Files in `05_READY/`
- Details files from `01_HOBO_OUT/`
- Site metadata YAML files (`SCRIPTED_WORKFLOW/Site_Metadata/`)
- Deployment log (`Temperature_UVI_deployment_log.csv`)
- Template file (`misc/templates/DATASET-BT_Template.txt`)

**Process:**
1. **Locate Files**
   - Finds all processed CSV files in `05_READY/`
   - Matches each CSV with corresponding Details files
   - Extracts site codes and deployment dates

2. **Extract Information**
   - Reads site metadata (coordinates, depth, description) from YAML files
   - Parses Details files for serial numbers and deployment info
   - Reads CSV files for actual date ranges and statistics
   - Retrieves deployment information from deployment log

3. **Generate DATASET Files**
   - Loads template and fills in all placeholders:
     - Site name and location
     - Date range
     - Coordinates and depth
     - Serial numbers
     - Processing notes (merge status)
   - Embeds complete Details file content
   - Prompts for any missing information

4. **Rename DETAILS Files**
   - Copies Details files with proper naming convention
   - Follows format: `DETAILS_BT_[SITE]_[YYMM]_[YYMM].txt`

**User Prompts:**

During execution, you may be prompted for:
- **Sensor deployment info**: Additional context about sensor placement (press Enter to skip if not available)
- **Your name**: For the "Created by" field (defaults to system username)

Any information already available in metadata files will be used automatically.

**Output:**
- `07_METADATA/DATASET_*.txt` - DATASET description files
- `07_METADATA/DETAILS_*.txt` - Renamed Details files

**Files Generated:**
For each processed dataset (e.g., `BT_TCBKPT_2410_2503.csv`):
- `DATASET_BT_TCBKPT_2410_2503.txt` - Complete metadata description
- `DETAILS_BT_TCBKPT_2410_a.txt` - First logger details
- `DETAILS_BT_TCBKPT_2410_b.txt` - Second logger details (if duplicate)

**What to Check:**
- Verify all CSV files have corresponding DATASET files
- Review generated DATASET files for accuracy
- Ensure coordinates and depth are correct
- Check that serial numbers match your loggers
- Verify merge note is present for duplicate/offset loggers

**Example Output:**
```
============================================================
METADATA GENERATION - DATASET and DETAILS Files
============================================================

✅ Loaded deployment log: 1149 entries
✅ Found 2 file(s) to process

============================================================
Generating metadata for: BT_TCBKPT_2410_2503.csv
============================================================
✅ Found 2 Details file(s)

--- Verify/Update Information ---
Enter sensor deployment info (or press Enter to skip): 
Enter your name [laurenkay]: Lauren Kay
✅ Saved: DATASET_BT_TCBKPT_2410_2503.txt
✅ Saved: DETAILS_BT_TCBKPT_2410_a.txt
✅ Saved: DETAILS_BT_TCBKPT_2410_b.txt

============================================================
COMPLETE: Generated metadata for 2/2 file(s)
============================================================
```

**DATASET File Contents:**
The generated DATASET file includes:
- Site information and coordinates
- Deployment period
- Sensor specifications and serial numbers
- Site description
- Data processing notes
- Complete Details file content
- Creator and date information

---

### Step 5: Final Export

**Purpose**: Export QC-passed data to external locations for database integration and archiving.

#### 5.1 Automated Export System

If export paths are configured in `config.py` (Step 1.4), final files are automatically exported during processing:

- **AVERAGING.py** exports CSV files from `05_READY/`
- **NCPLOT.py** exports NetCDF files from `06_NETCDF/` and plots from `02_PLOTS/ready/`
- **GENERATE_METADATA.py** exports DATASET files from `07_METADATA/`

**All exports are organized by site location name into subfolders:**

```
../TCRMP_temperature_database/
  Black_Point/
    BT_TCBKPT_2410_2503.csv
  Buck_Island_STT/
    BT_TCBKIT_2410_2503.csv

../TCRMP_temperature_nc/
  Black_Point/
    BT_TCBKPT_2410_2503.nc

../TCRMP_temperature_database_plot/
  Black_Point/
    BT_TCBKPT_2410_2503_plot.png

../TCRMP_temperature_metadata/
  Black_Point/
    DATASET_BT_TCBKPT_2410_2503.txt
```

#### 5.2 QC-Only Export Policy

**CRITICAL:** Only quality-controlled files are exported:

✅ **Exported:**
- Files in `05_READY/` (passed QC)
- NetCDF files from `06_NETCDF/` (generated from READY files)
- Plots from `02_PLOTS/ready/` (finalized plots)
- DATASET files from `07_METADATA/` (completed metadata)

❌ **NEVER Exported:**
- Files in `04_TOREVIEW/` (flagged for review)
- Pre-trimmed or post-trimmed plots
- Partial or incomplete data

Files flagged for review must be manually inspected and reprocessed before they will be exported.

#### 5.3 Verification

After processing, verify exports (if configured):

1. Check that site subfolders were created correctly
2. Verify file naming follows convention: `BT_SITECODE_YYMM_YYMM.*`
3. Confirm all expected files are present
4. Check that no TOREVIEW files were exported


---

## Testing with Example Data

The framework includes example data for testing and training.

### Example Files Location

```
misc/example_data/
├── BT_TCBKPT_2410_a.csv
├── BT_TCBKPT_2410_a_Details.txt
├── BT_TCBKPT_2410_b.csv
├── BT_TCBKPT_2410_b_Details.txt
├── BT_TCBKIT_2410.csv
└── BT_TCBKIT_2410_Details.txt
```

### Running the Example


1. **Configure for testing:**

   ```python
   # In src/config.py:
   'YEARS': ['ExampleTest'],
   'MONITORING_TYPES': ['annual'],
   ```
2. **Run setup:**

   ```bash
   python3 src/setup.py
   ```
3. **Copy example data:**

   ```bash
   cp misc/example_data/*.csv ../SCRIPTED_OUTPUTS/ExampleTest/annual/01_HOBO_OUT/
   cp misc/example_data/*_Details.txt ../SCRIPTED_OUTPUTS/ExampleTest/annual/01_HOBO_OUT/
   ```
4. **Process data:**

   ```bash
   source temp_monitoring_env/bin/activate
   python3 src/TRIM_PLOT.py
   python3 src/AVERAGING.py
   python3 src/NCPLOT.py
   ```

### Expected Results

**After TRIM_PLOT.py:**

* 3 CSV files trimmed
* 6 plots created (3 pre, 3 post)
* No errors

**After AVERAGING.py:**

* TCBKPT: 2 files averaged into 1
* TCBKIT: 1 file passes through
* 2 files in `05_READY/`
* 0 files in `04_TOREVIEW/`

**After NCPLOT.py:**

* 2 NetCDF files created
* 2 final plots generated


---

## Troubleshooting

### Common Errors and Solutions

#### Error: "File not found" or "No such file or directory"

**Problem**: Script cannot find input files.

**Solutions:**


1. Check you're in correct directory: `pwd` (should show SCRIPTED_WORKFLOW)
2. Verify files exist: `ls ../SCRIPTED_OUTPUTS/[year]/[monitoring_type]/01_HOBO_OUT/`
3. Check filename spelling and format
4. Ensure you ran previous steps in order

#### Error: "Filename does not match deployment log"

**Problem**: CSV filename not found in deployment log.

**Solutions:**


1. Open `Temperature_UVI_deployment_log.csv`
2. Check "Offloaded Filename" column
3. Verify filename exactly matches (including case)
4. Add deployment log entry if missing
5. Correct filename if misspelled

#### Error: "Column not found" or "KeyError"

**Problem**: CSV file missing required columns.

**Solutions:**


1. Open CSV in Excel or text editor
2. Check header row has:
   * `Date Time, GMT-04:00`
   * `Temp, °C`
   * `#`
3. Re-export from HOBOware if necessary
4. Ensure no extra spaces in column names

#### Error: "No module named..."

**Problem**: Python package not installed.

**Solutions:**


1. Activate virtual environment:

   ```bash
   source temp_monitoring_env/bin/activate
   ```
2. If still fails, reinstall:

   ```bash
   pip install -r src/requirements.txt
   ```
3. Check Python version: `python3 --version` (need 3.8+)

#### Warning: "SettingWithCopyWarning"

**Problem**: Pandas warning (not an error).

**Solution**: This warning can be ignored. The code works correctly. To suppress:

```bash
export PYTHONWARNINGS="ignore"
python3 src/TRIM_PLOT.py
```

#### Files Sent to TOREVIEW

**Problem**: Files flagged during AVERAGING.py.

**Solutions:**


1. Check plots in `02_PLOTS/` for visual inspection
2. Common causes:
   * **Duplicate loggers differ by >0.2°C**: One logger may be malfunctioning
   * **Drift detected in merged loggers**: Systematic bias between sensors
3. Contact data manager (Tyler) with:
   * Flagged filename
   * Associated plots
   * Brief description
4. Follow instructions for corrections

#### Virtual Environment Won't Activate (Windows)

**Problem**: "Scripts\\activate is not recognized"

**Solution**: Use PowerShell activation:

```powershell
.\temp_monitoring_env\Scripts\Activate.ps1
```

Or enable script execution:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Getting Help


1. **Check console output** for specific error messages
2. **Review plots** in `02_PLOTS/` for visual data inspection
3. **Contact data manager** (Tyler Smith) for data-related questions
4. **Check GitHub issues** (if repository available) for known problems


---

## Technical Appendix

### A. Virtual Environment (venv)

**What it is:**
A virtual environment is an isolated Python environment that keeps packages and dependencies separate from your system Python installation.

**Why we use it:**

* Prevents conflicts between different projects
* Ensures consistent package versions
* Makes the project portable
* Easy to recreate on different machines

**How to use:**

```bash
# Activate (macOS/Linux)
source temp_monitoring_env/bin/activate

# Activate (Windows)
temp_monitoring_env\Scripts\activate

# Deactivate (all systems)
deactivate
```

**What happens when activated:**

* Your command prompt shows `(temp_monitoring_env)`
* Python packages are installed to this environment only
* `python` and `pip` commands use this environment


---

### B. Configuration File (config.py)

**Purpose:**
Centralized configuration for all processing scripts.

**Key Parameters:**

| Parameter | Description | Default |
|----|----|----|
| `YEARS` | Year or identifier for output directories | `['2025']` |
| `MONITORING_TYPES` | Type of monitoring program | `['annual', 'PBL']` |
| `TEMPERATURE_DIFFERENCE_THRESHOLD` | Max °C difference for duplicate averaging | `0.2` |
| `DEPLOYMENT_BUFFER_HOURS` | Hours added to trim buffer | `1` |
| `EXPECTED_TIMEZONE` | Time zone for data | `'GMT-04:00'` |

**How scripts use it:**

```python
from config import CONFIG, get_path_for

# Get configured path
hobo_path = get_path_for("01_HOBO_OUT")

# Access parameter
threshold = CONFIG['TEMPERATURE_DIFFERENCE_THRESHOLD']
```


---

### C. CSV File Format

**Required Structure:**

```csv
"#","Date Time, GMT-04:00","Temp, °C","Coupler Detached","Coupler Attached",...
1,10/10/24 08:00:00,24.195,Logged,,
2,10/10/24 08:15:00,24.195,,,
3,10/10/24 08:30:00,24.171,,,
```

**Required Columns:**

* `#` - Row number
* `Date Time, GMT-04:00` - Timestamp (must match timezone in config)
* `Temp, °C` - Temperature in Celsius

**Common Issues:**

* Wrong timezone format in header
* Temperature column name differs (`Temp, *C` vs `Temp, °C`)
* Extra rows before header
* Missing or corrupted timestamps


---

### D. NetCDF Format

**What it is:**
Network Common Data Form (NetCDF) is a self-describing, machine-independent data format for array-oriented scientific data.

**Why we use it:**

* Includes metadata with data
* Widely used in climate/ocean science
* Efficient storage and access
* CF Convention compliant
* Compatible with analysis tools (Python, R, MATLAB)

**Structure:**

```
Dimensions: (time: 15928)
Coordinates:
  * time        (time) datetime64[ns]
    latitude    float64
    longitude   float64
Data variables:
    temperature (time) float64
Attributes:
    site_name:   "Black Point"
    depth:       "10m"
    ...
```

**How to read:**

```python
import xarray as xr
ds = xr.open_dataset('BT_TCBKPT_2410_2503.nc')
print(ds.temperature.values)
```


---

### E. Deployment Log

**Purpose:**
Master record of all logger deployments and retrievals.

**Required Fields:**

| Field | Description | Format |
|----|----|----|
| `Offloaded Filename` | Name of CSV file | `BT_TCBKPT_2410_a` |
| `Date In` | Deployment date | `10/11/2024` |
| `Time In` | Deployment time | `9:36:00` |
| `Date Out` | Retrieval date | `3/26/2025` |
| `Time Out` | Retrieval time | `9:45:00` |
| `Site Name` | Full site name | `Black Point` |

**Validation Checks:**

* Filename must match exactly (case-sensitive)
* Dates must be valid and in order (Date In < Date Out)
* Times must be in HH:MM:SS format
* No `?` characters in time fields


---

### F. Quality Assurance/Quality Control (QAQC)

**QA/QC Steps in This Workflow:**


1. **File Validation**
   * Encoding check (UTF-8)
   * Naming convention compliance
   * Required columns present
2. **Temporal Validation**
   * Deployment period matches logger data
   * No large data gaps
   * Consistent time intervals
3. **Temperature Validation**
   * Duplicate loggers agree (within 0.2°C)
   * No extreme outliers
   * Drift detection for merged loggers
4. **Visual Inspection**
   * Pre/post trim plots
   * Agreement plots for merged files
   * Final time series plots
5. **Metadata Validation**
   * Site coordinates present
   * Deployment info complete
   * NetCDF attributes populated


---

### G. File Identifiers

**Naming Suffix Meanings:**

| Identifier | Meaning | Processing | Example |
|----|----|----|----|
| `_a` | Single or first duplicate | Average with `_b` if exists | `BT_TCBKPT_2410_a.csv` |
| `_b` | Second duplicate logger | Average with `_a` | `BT_TCBKPT_2410_b.csv` |
| `_c` | First offset logger | Merge with `_d` | `BT_TCCB08_2410_c.csv` |
| `_d` | Second offset logger | Merge with `_c` | `BT_TCCB08_2410_d.csv` |
| (none) | Single logger | Pass through | `BT_TCBKIT_2410.csv` |

**Processing Differences:**

**Duplicate (_a/_b):**

* Same location, same depth
* Should read same temperature
* Averaged if within 0.2°C
* Provides measurement redundancy

**Offset (_c/_d):**

* Same location, different depths
* Expected to differ
* Checked for drift (systematic bias)
* Merged if no drift detected

**Single (no suffix):**

* One logger at location
* No averaging or merging
* Passes directly to ready


---

### H. Dependencies

**Required Python Packages:**

```
pandas>=1.5.0          # Data manipulation
numpy>=1.21.0          # Numerical operations
matplotlib>=3.5.0      # Plotting
seaborn>=0.11.0        # Statistical visualizations
scipy>=1.8.0           # Scientific computing
xarray>=2024.1.2       # NetCDF handling
pyyaml>=6.0.2          # YAML metadata parsing
glob2>=0.7             # File pattern matching
argparse>=1.4.0        # Command-line arguments
python-dateutil>=2.8.2 # Date parsing
pytz>=2020.1           # Timezone handling
```

**Installation:**
All dependencies are automatically installed by `setup.py`. To manually reinstall:

```bash
pip install -r src/requirements.txt
```


---

### I. Directory Structure Details

```
TCRMP_temperature_hobo_processing/
├── SCRIPTED_WORKFLOW/              # Main workflow directory
│   ├── README.md                   # This file
│   ├── src/                        # Python scripts
│   │   ├── config.py               # Configuration
│   │   ├── setup.py                # Setup script
│   │   ├── TRIM_PLOT.py            # Trimming and plotting
│   │   ├── AVERAGING.py            # Averaging and drift detection
│   │   ├── NCPLOT.py               # NetCDF conversion
│   │   ├── GENERATE_METADATA.py    # Metadata generation
│   │   ├── QAQC_HELPER_FUNCTIONS.py # Helper functions
│   │   └── requirements.txt        # Package dependencies
│   ├── Site_Metadata/              # Site YAML files
│   │   ├── TCBKPT.yaml
│   │   ├── TCBKIT.yaml
│   │   └── ...
│   └── temp_monitoring_env/        # Virtual environment (created by setup)
├── SCRIPTED_OUTPUTS/               # Processing outputs (created by setup)
│   └── [Year]/                     # Year or identifier
│       └── [MonitoringType]/       # annual or PBL
│           ├── 01_HOBO_OUT/        # Input files
│           ├── 02_PLOTS/           # Visualizations
│           ├── 03_TRIMMED_CSVS/    # Trimmed data
│           ├── 04_TOREVIEW/        # Flagged files
│           ├── 05_READY/           # QC-passed files
│           ├── 06_NETCDF/          # NetCDF outputs
│           ├── 07_METADATA/        # DATASET and DETAILS files
│           ├── deployment_logs/    # Deployment metadata
│           └── config_snapshots/   # Configuration backups
├── misc/                           # Miscellaneous files
│   ├── example_data/               # Example test data
│   └── templates/                  # DATASET template file
├── Temperature_UVI_deployment_log.csv  # Master deployment log
└── TCRMP_TempSiteMetadata.csv     # Site metadata
```


---

## Contacts and Support

**Data Manager**: Tyler Smith**Institution**: University of the Virgin Islands, Center for Marine and Environmental Studies

**For questions about:**

* **Data issues**: Contact data manager
* **Technical problems**: Check Troubleshooting section
* **Workflow modifications**: Consult with data manager before making changes


---

## Version History

**v1.0** - October 2025

* Initial comprehensive documentation
* Added prerequisites and detailed workflow
* Included example data and troubleshooting
* Added technical appendix


---

*End of Documentation*