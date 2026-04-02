# Averaging.py

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Set paths from config
from config import CONFIG, get_path_for, resolve_path
from processing_logger import ProcessingLogger
import re

review_folder = get_path_for("04_TOREVIEW")
trimmed_csv = get_path_for("03_TRIMMED_CSVS")
deployment_log_path = resolve_path(CONFIG['DEPLOYMENT_LOG_CSV'])
output_folder = get_path_for("05_READY")
log_dir = get_path_for("07_METADATA/processing_logs")

#%% IMPORT FUNCTIONS
from QAQC_HELPER_FUNCTIONS import (
    import_trimmed,
    get_usvi_site_codes,
    get_panama_site_codes,
    compute_temperature_difference,
    load_structured_dataframes,
    report_missing_a_identifiers,
    reassign_offset_identifiers,
    identify_calculations,
    build_calc_df_subset,
    add_comparison_columns,
    get_location_from_code,
    report_flags,
    save_flagged_files,
    average_temperature_if_close,
    report_nan_temperature_differences,
    drop_extra_columns,
    plot_temperature_time_series,
    merge_offset_files,
    plot_offset_agreement,
    offload_drifting_files,
    print_start_end_times,
    generate_trimmed_filenames,
    save_offload_files,
    create_and_save_offload_plots
)

#%%
# 1. Get the trimmed csvs
csv_files = import_trimmed(trimmed_csv)

# 2. Get site codes lists
usvi_codes = get_usvi_site_codes()
panama_codes = get_panama_site_codes()

# 4. Load CSVs into nested dict structure
df_files = load_structured_dataframes(csv_files, usvi_codes, panama_codes)

# 8. Report missing 'a' identifiers in df_files
report_missing_a_identifiers(df_files)

# 9. Reassign offset identifiers 'a' and 'b' to 'c' and 'd' if needed
reassign_offset_identifiers(df_files, panama_codes)

# 21. Compute temperature difference between 'a' and 'b' files
compute_temperature_difference(df_files)

# 22. Identify calculations (sites/files needing attention due to temp diffs)
calculations = identify_calculations(df_files)

# 23. Build subset dict for those calculations
calc_df_files = build_calc_df_subset(df_files, calculations)

# 24. Add comparison columns (Temp A, Temp B, Average, Flag) to 'a' dfs
add_comparison_columns(calc_df_files)

# 25. Report flagged temperature differences
report_flags(calc_df_files)

# 28. Report NaN counts in 'a' dfs for flagged calculations
report_nan_temperature_differences(df_files, calculations)

# 31. Merge offset files 'c' and 'd' for each site, file number, returning merged dict
merged_offset_data = merge_offset_files(df_files, panama_codes)

# 32. Plot offset agreement scatter plots comparing 'c' and 'd' logger temperatures
offset_stats, drifting = plot_offset_agreement(df_files, panama_codes)

# offloading the merged files that are drifting for review
offload_drifting_files(drifting, review_folder)

# 26. Save flagged files as CSV to your calculations_folder output
save_flagged_files(calc_df_files, review_folder)

# 27. Average temperature between 'a' and 'b' files if difference below threshold (0.2°C)
average_temperature_if_close(df_files, calculations=calculations)

# 29. Drop extra columns, keep only necessary ones (#, date_col, Temp)
drop_extra_columns(df_files, panama_codes)

# 36. Save 'a' files and merged files as CSVs to output folder with adjusted columns
saved_files = save_offload_files(df_files, merged_offset_data, panama_codes, output_folder, calculations=calculations, drifting=drifting)

# 37. Update processing logs with averaging/merging decisions
print("\n[LOG] Updating processing logs...")
for site_code in df_files:
    for file_number in df_files[site_code]:
        start_yymm = str(file_number)
        
        # Load existing log
        log_file = os.path.join(log_dir, f"{site_code}_{start_yymm}.json")
        if not os.path.exists(log_file):
            print(f"  [WARN] Log not found for {site_code}_{start_yymm}, skipping")
            continue
        
        logger = ProcessingLogger(site_code, start_yymm, log_dir)
        file_dict = df_files[site_code][file_number]
        
        # Determine if this was averaged, merged, or single
        has_a_b = 'a' in file_dict and 'b' in file_dict
        has_c_d = 'c' in file_dict and 'd' in file_dict
        
        # Check if file was flagged
        was_flagged = False
        flag_reason = None
        
        # Check if in calculations (flagged for temperature difference)
        if site_code in calculations and file_number in calculations[site_code]:
            was_flagged = True
            flag_reason = f"Temperature difference exceeded {CONFIG.get('TEMPERATURE_DIFFERENCE_THRESHOLD', 0.2)}°C threshold"
        
        # Check if in drifting (flagged for drift)
        if site_code in drifting and file_number in drifting[site_code]:
            was_flagged = True
            flag_reason = "Drift detected between offset loggers"
        
        if was_flagged:
            # Flag for review
            logger.flag_for_review(flag_reason)
            logger.add_processing_step(
                step_name="AVERAGING",
                action="Flagged for review",
                details=flag_reason,
                method="review_needed"
            )
            print(f"  [FLAG] Flagged: {site_code}_{start_yymm} - {flag_reason}")
        elif has_a_b:
            # Averaged duplicates
            max_diff = None
            if 'a' in file_dict:
                df_a = file_dict['a']
                if isinstance(df_a, pd.DataFrame):
                    temp_diff_col = [col for col in df_a.columns if 'Temperature Difference' in col]
                    if temp_diff_col and temp_diff_col[0] in df_a.columns:
                        max_diff = df_a[temp_diff_col[0]].max()
            
            details = f"Max temperature difference: {max_diff:.3f}°C (below {CONFIG.get('TEMPERATURE_DIFFERENCE_THRESHOLD', 0.2)}°C threshold)" if max_diff else "Duplicate loggers averaged"
            logger.add_processing_step(
                step_name="AVERAGING",
                action="Averaged duplicate loggers",
                details=details,
                method="duplicate_average"
            )
            print(f"  [OK] Averaged: {site_code}_{start_yymm}")
        elif has_c_d:
            # Merged offsets
            logger.add_processing_step(
                step_name="AVERAGING",
                action="Merged offset loggers",
                details="Offset loggers passed drift detection",
                method="offset_merge"
            )
            print(f"  [OK] Merged: {site_code}_{start_yymm}")
        else:
            # Single file
            logger.add_processing_step(
                step_name="AVERAGING",
                action="Single logger - passed through",
                details="No averaging or merging needed",
                method="single"
            )
            print(f"  [OK] Single: {site_code}_{start_yymm}")
        
        # Set final filename if file was saved (not flagged)
        if not was_flagged:
            # Try to find the output file
            output_pattern = os.path.join(output_folder, f"BT_{site_code}_{start_yymm}_*.csv")
            import glob
            output_files = glob.glob(output_pattern)
            if output_files:
                final_filename = os.path.basename(output_files[0])
                logger.set_final_filename(final_filename)
                print(f"    → {final_filename}")

print("\n[OK] Processing logs updated!")

# 38. Export READY files to external location if configured
export_path = resolve_path(CONFIG.get('EXPORT_READY_PATH', ''))
if export_path and os.path.exists(export_path):
    print(f"\n[EXPORT] Exporting READY files to: {export_path}")
    import shutil
    
    ready_files = glob.glob(os.path.join(output_folder, "BT_*.csv"))
    exported_count = 0
    
    for ready_file in ready_files:
        # Get site name from filename to create site-specific subfolder
        basename = os.path.basename(ready_file)
        match = re.match(r'BT_([A-Z]+\d*)_', basename)
        
        if match:
            site_code = match.group(1)
            # Get full location name from site code for folder name
            location_name = get_location_from_code(site_code)
            site_export_folder = os.path.join(export_path, location_name)
            os.makedirs(site_export_folder, exist_ok=True)
            
            dest_path = os.path.join(site_export_folder, basename)
            shutil.copy2(ready_file, dest_path)
            exported_count += 1
            print(f"  [OK] Exported: {basename} -> {location_name}/")
    
    print(f"\n[OK] Exported {exported_count} READY file(s)")
elif export_path:
    print(f"\n[WARN] Export path configured but does not exist: {export_path}")
    print("   Skipping export. Create the directory to enable export.")
else:
    print("\n[SKIP] No export path configured for READY files (test mode)")

