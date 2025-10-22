# TRIM/PLOT.PY

# suggested additions - robust to timezones, completion prompt at end, suppress warnings 

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Set paths from config
from config import CONFIG, get_path_for
from processing_logger import get_logger
import re
import glob

folder_path = get_path_for("01_HOBO_OUT")
pretrimmed_path = get_path_for("02_PLOTS/pretrimmed")
posttrimmed_path = get_path_for("02_PLOTS/posttrimmed")
trimmed_csv = get_path_for("03_TRIMMED_CSVS")
log_dir = get_path_for("07_METADATA/processing_logs")
deployment_log_path = os.path.join(os.path.dirname(CONFIG['BASE_DIRECTORY']),"Temperature_UVI_deployment_log.csv")


#IMPORT FUNCTIONS
from QAQC_HELPER_FUNCTIONS import (
    get_csv_files,
    get_usvi_site_codes,
    get_panama_site_codes,
    ensure_utf8_encoding,
    load_structured_dataframes,
    clean_plot_title_headers,
    convert_panama_times,
    normalize_sio_file_names,
    report_missing_a_identifiers,
    reassign_offset_identifiers,
    filter_deployment_log,
    check_unmatched_filenames,
    validate_time_columns,
    convert_deployment_log_datetime,
    create_deployment_data_dict,
    format_deployment_datetimes,
    plot_pre_trimmed,
    parse_deployment_datetime_strings,
    trim_dataframes_by_date,
    final_trim_dataframe_edges,
    check_data_lengths,
    plot_post_trimmed,
    export_trimmed_csvs,
    print_start_end_times
)


# 1. Get CSV files in folder_path
csv_files = get_csv_files(folder_path)

# 2. Get site codes lists
usvi_codes = get_usvi_site_codes()
panama_codes = get_panama_site_codes()

# 3. Ensure UTF-8 encoding for all CSV files in folder_path
ensure_utf8_encoding(folder_path)

# 4. Load CSVs into nested dict structure
df_files = load_structured_dataframes(csv_files, usvi_codes, panama_codes)

# 5. Clean plot title headers in df_files if needed
clean_plot_title_headers(df_files)

# 6. Convert Panama site times (GMT-04:00 to GMT-05:00)
convert_panama_times(df_files, panama_codes)

# 7. Normalize SIO file names, rename files in folder_path
normalize_sio_file_names(df_files, folder_path)

# 8. Report missing 'a' identifiers in df_files
report_missing_a_identifiers(df_files)

# 9. Reassign offset identifiers 'a' and 'b' to 'c' and 'd' if needed
reassign_offset_identifiers(df_files, panama_codes)

# 10. Import and Filter deployment log to only files matching CSVs
deployment_df = pd.read_csv(deployment_log_path)

filtered_deployment_df, csv_file_names = filter_deployment_log(deployment_df, csv_files)

# 11. Check unmatched filenames in deployment log vs CSV files
check_unmatched_filenames(filtered_deployment_df, csv_file_names)

# 12. Validate time columns in filtered deployment log
validated_deployment_df = validate_time_columns(filtered_deployment_df)

# 13. Convert deployment log date/time columns
converted_deployment_df = convert_deployment_log_datetime(validated_deployment_df)

# 14. Create a deployment data dictionary for quick lookups
deployment_data_dict = create_deployment_data_dict(converted_deployment_df)

# 15. Format deployment datetime strings for readability
format_deployment_datetimes(deployment_data_dict)

# 16. Plot pre-trimmed data for QC and save
plot_pre_trimmed(df_files, panama_codes, pretrimmed_path)

# 17. Parse deployment datetime strings back into datetime objects (after formatting)
parse_deployment_datetime_strings(deployment_data_dict)

# 18. Trim df_files by deployment date/time ranges
trim_dataframes_by_date(df_files, deployment_data_dict, panama_codes)

# 19. Final trim edges of each dataframe (defaults: drop first 4 and last 5 rows)
final_trim_dataframe_edges(df_files)

# 20. Check if pairs ('a' & 'b', 'c' & 'd', etc.) have same data lengths
check_data_lengths(df_files)

# 21. Plot post-trimmed data for QC and save
plot_post_trimmed(df_files, panama_codes, posttrimmed_path)

# 22. export trimmed files
export_trimmed_csvs(df_files, trimmed_csv)

# 23. Print start and end times for each dataframe and matching deployment data
print_start_end_times(df_files, panama_codes, deployment_data_dict)

# 24. Initialize processing logs for each file
print("\n[LOG] Initializing processing logs...")
for site_code in df_files:
    for file_number in df_files[site_code]:
        # Get file info
        file_dict = df_files[site_code][file_number]
        
        # Extract start_yymm from file_number
        start_yymm = str(file_number)
        
        # Initialize logger for this site/deployment
        logger = get_logger(site_code, start_yymm, log_dir, CONFIG)
        
        # Add each input file (a, b, c, d, etc.)
        for identifier in file_dict:
            if identifier in ['a', 'b', 'c', 'd']:
                df = file_dict[identifier]
                filename = f"BT_{site_code}_{start_yymm}_{identifier}.csv"
                
                # Get serial number from Details file if available
                details_pattern = os.path.join(folder_path, f"BT_{site_code}_{start_yymm}_{identifier}_Details.txt")
                details_files = glob.glob(details_pattern)
                serial_number = None
                if details_files:
                    try:
                        with open(details_files[0], 'r') as f:
                            content = f.read()
                            serial_match = re.search(r'Serial Number:\s*(\d+)', content)
                            if serial_match:
                                serial_number = serial_match.group(1)
                    except:
                        pass
                
                # Get sample counts
                samples_trimmed = len(df) if df is not None else 0
                
                # Add to log
                logger.add_input_file(
                    filename=filename,
                    serial_number=serial_number,
                    samples_original=None  # Will be updated if we track this
                )
                
                # Update with trimmed count
                logger.update_input_file(
                    filename=filename,
                    samples_trimmed=samples_trimmed
                )
        
        # Add processing step for trimming
        total_files = len([k for k in file_dict.keys() if k in ['a', 'b', 'c', 'd']])
        logger.add_processing_step(
            step_name="TRIM_PLOT",
            action="Trimmed to deployment period",
            details=f"Matched deployment log. Added {CONFIG.get('DEPLOYMENT_BUFFER_HOURS', 1)} hour buffer. Trimmed {CONFIG.get('TRIM_START_POINTS', 4)} start and {CONFIG.get('TRIM_END_POINTS', 5)} end points.",
            outputs=["pretrimmed plot", "posttrimmed plot", "trimmed CSV"]
        )
        
        print(f"  [OK] Log created: {site_code}_{start_yymm}.json")

print("\n[OK] Processing logs initialized!")