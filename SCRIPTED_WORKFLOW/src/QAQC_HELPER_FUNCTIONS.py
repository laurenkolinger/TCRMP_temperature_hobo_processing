# QAQC HELPER FUNCTIONS

# Imports
import os
import pandas as pd
import glob
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta
import copy
import matplotlib.dates as mdates
import numpy as np
from config import CONFIG, resolve_path

# Load site metadata CSV for location name mapping
_metadata_df = None

def _load_metadata_df():
    """Lazy load the metadata dataframe."""
    global _metadata_df
    if _metadata_df is None:
        metadata_csv_path = resolve_path(CONFIG['SITE_METADATA_CSV'])
        _metadata_df = pd.read_csv(metadata_csv_path, dtype=str)
        _metadata_df.set_index("6LetterCode", inplace=True)
    return _metadata_df

def get_location_from_code(site_code):
    """
    Return location name for a given 6-letter site code from metadata CSV.
    Converts location name to folder-safe format (underscores instead of spaces).
    
    Parameters:
        site_code (str): 6-letter site code (e.g., 'TCBKPT')
    
    Returns:
        str: Folder-safe location name (e.g., 'Black_Point') or site code if not found
    """
    metadata_df = _load_metadata_df()
    try:
        location = metadata_df.loc[site_code, "Location"]
        return location.replace(" ", "_")  # safe folder name
    except KeyError:
        print(f"Warning: Site code {site_code} not found in metadata CSV.")
        return site_code  # fallback to site code

#
def get_csv_files(folder_path, file_pattern='*.csv'):
    """
    Get a list of CSV file paths in the given folder.

    Parameters:
        folder_path (str): Path to the folder containing CSV files.
        file_pattern (str): File matching pattern (default is '*.csv').

    Returns:
        list: List of CSV file paths.
    """
    csv_files = glob.glob(f"{folder_path}/{file_pattern}")
    print(f"Found {len(csv_files)} CSV files.")
    return csv_files


def get_usvi_site_codes():
    """
    Returns a list of predefined USVI site codes.

    Returns:
        list: List of USVI site codes.
    """
    return [
        "TCCORB","TCFSHB","TCMERI","TCBKPT","TCBOTB","TCBRWB","TCBKIT",
        "TCCORK","TCCLGE","TCFLTC","TCGB63","TCGMKT","TCHB40","TCHB30",
        "TCHB20","TCMAGB","TCSAVA","TCSHCS","TCSCAP","TCSC35","TCSWAT",
        "TCLSTJ","TCBKIX","TCBX33","TCCB08","TCCB40","TCCB99","TCCB67",
        "TCCSTL","TCEAGR","TCGRPD","TCJCKB","TCKNGC","TCLBEM","TCLB99",
        "TCLB67","TCLBRH","TCMT24","TCMT40","TCSR30","TCSR99","TCSR41",
        "TCSR67","TCSR10","TCSPTH","TCLE67"
    ]
    # Note: site code TCCB60 is not included


def get_panama_site_codes():
    """
    Returns a list of predefined Panama site codes.

    Returns:
        list: List of Panama site codes.
    """
    return [
        "PCAR04","PCAW10","PDG4X5","PDG20M","PUVCCP","PUVGC",
        "PUVM18","PUVR10","PUVR20","PUVR30","PAUVGC","PCAR03",
        "PCO3M","PCT18M","PDG10M","PIG10M","PIG20M","PSA3M",
        "PSA11M","PUVF10","PUVFLT","PCT3M","PUV3M"
    ]


def ensure_utf8_encoding(folder_path):
    """
    Walks through all CSV files in a folder and ensures they are UTF-8 encoded.
    Converts files to UTF-8 if necessary (e.g., from Latin-1).

    Parameters:
        folder_path (str): Root folder containing CSV files.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.csv'):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read()
                    print(f"[OK] Already UTF-8: {file_path}")

                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file_path, encoding='latin1')
                        df.to_csv(file_path, index=False, encoding='utf-8')
                        print(f"🔁 Converted to UTF-8: {file_path}")
                    except Exception as e:
                        print(f"[ERROR] Error processing {file_path}: {e}")


def load_structured_dataframes(csv_files, site_codes, panama_codes):
    """
    Loads and structures CSV files into a nested dictionary:
    df_files[site_code][file_number][file_identifier] = {'DataFrame': df, 'File Name': base_file_name}

    Parameters:
        csv_files (list): List of CSV file paths.
        site_codes (list): List of valid USVI site codes.
        panama_codes (list): List of valid Panama site codes.

    Returns:
        dict: Structured dictionary of DataFrames.
    """
    df_files = {}

    for csv_file in csv_files:
        file_name = os.path.basename(csv_file).split('.')[0]
        parts = file_name.split('_')

        if len(parts) < 3:
            print(f"[WARN] Skipping improperly named file: {file_name}")
            continue

        site_code = parts[1]
        file_number = parts[2]
        file_identifier = parts[-1] if len(parts) > 3 and parts[-1] != '' else "a"
        base_file_name = os.path.splitext(os.path.basename(csv_file))[0]

        print(f"[LOAD] Reading CSV for site: {site_code}, file: {csv_file}")
        df = pd.read_csv(csv_file)

        if site_code not in df_files:
            df_files[site_code] = {}

        if file_number not in df_files[site_code]:
            df_files[site_code][file_number] = {}

        if file_identifier in df_files[site_code][file_number]:
            print(f"[WARN] Duplicate identifier '{file_identifier}' for site {site_code}, file number {file_number}")
        else:
            df_files[site_code][file_number][file_identifier] = {
                'DataFrame': df,
                'File Name': base_file_name
            }

        if site_code not in site_codes and site_code not in panama_codes:
            raise ValueError(f"[ERROR] Invalid site code '{site_code}' in {csv_file}.")

    return df_files


def clean_plot_title_headers(df_files):
    """
    Detects and removes rows with 'Plot Title' in any cell, and replaces the header
    row with the first data row in such cases.

    Modifies df_files in place.
    """
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                file_name = file_info['File Name']
                df = file_info['DataFrame']

                if any('plot title' in col.lower() for col in df.columns):
                    print(f"Cleaning File: {file_name}")

                    df = df[~df.apply(
                        lambda row: row.astype(str).str.lower().str.contains('plot title').any(),
                        axis=1
                    )].reset_index(drop=True)

                    # Reassign header and reindex
                    new_header = df.iloc[0]
                    df = df[1:].reset_index(drop=True)
                    df.columns = new_header

                    file_info['DataFrame'] = df

                    print(f"  [OK] Cleaned and reheadered: {file_name}")
                    print(f"  📊 New Columns: {df.columns.tolist()}")
                    print("-" * 50)
                else:
                    print(f"  No 'Plot Title' header in: {file_name}")


def convert_panama_times(df_files, panama_codes):
    """
    Converts 'Date Time, GMT-04:00' to 'Date Time, GMT-05:00' for Panama files
    by subtracting one hour. Modifies df_files in place.
    """
    for site_code, files in df_files.items():
        if site_code in panama_codes:
            for file_number, file_versions in files.items():
                for identifier, file_data in file_versions.items():
                    df = file_data['DataFrame']
                    datetime_col = "Date Time, GMT-04:00"

                    if datetime_col in df.columns:
                        df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')
                        df[datetime_col] = df[datetime_col] - timedelta(hours=1)
                        df.rename(columns={datetime_col: "Date Time, GMT-05:00"}, inplace=True)
                        print(f"⏱️ Converted time for: {file_data['File Name']}")
                    else:
                        print(f"[WARN] '{datetime_col}' not found in {file_data['File Name']}")


def normalize_sio_file_names(df_files, folder_path, csv_file_names=None):
    """
    Removes 'SIO' from file names and updates file numbers and names accordingly.
    Optionally updates a global csv_file_names list and renames CSV files on disk.

    Parameters:
        df_files (dict): The dictionary of structured dataframes.
        folder_path (str): Path to folder containing CSV files.
        csv_file_names (list, optional): List of file names to update in place.
    """
    for site_code, site_data in df_files.items():
        updated_files = {}

        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                file_name = file_info['File Name']
                file_name_parts = file_name.split("_")
                new_file_name_parts = [part for part in file_name_parts if part != "SIO"]
                new_file_name = "_".join(new_file_name_parts)

                file_info['File Name'] = new_file_name
                new_file_number = new_file_name_parts[2] if len(new_file_name_parts) > 2 else file_number

                if new_file_number not in updated_files:
                    updated_files[new_file_number] = {}
                updated_files[new_file_number][file_identifier] = file_info

                if csv_file_names is not None and file_name in csv_file_names:
                    csv_file_names[csv_file_names.index(file_name)] = new_file_name

                old_path = os.path.join(folder_path, file_name + ".csv")
                new_path = os.path.join(folder_path, new_file_name + ".csv")

                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                    print(f"[FILE] Renamed File: {old_path} → {new_path}")
                else:
                    print(f"[WARN] File not found, skipping: {old_path}")

        df_files[site_code] = updated_files


def report_missing_a_identifiers(df_files):
    """
    Reports files that do not have an 'a' identifier. These may need to be renamed
    to 'a' to be properly processed.
    """
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            if 'a' not in file_data:
                print(f"[WARN]  Missing 'a' identifier for site: {site_code}, file number: {file_number}")
            else:
                file_name = file_data['a']['File Name']
                print(f"[OK] Found 'a' identifier for {site_code}, file number {file_number}: {file_name}")


def reassign_offset_identifiers(df_files, panama_codes):
    """
    If 'a' and 'b' files for a site are more than 10 minutes apart at the first timestamp,
    rename them to 'c' and 'd'. Modifies df_files in place.
    """
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            if 'a' not in file_data or 'b' not in file_data:
                print(f"[SKIP] Skipping {site_code}, file {file_number}: only one file present.")
                continue

            df_a = file_data['a']['DataFrame']
            df_b = file_data['b']['DataFrame']

            # Use appropriate datetime column
            datetime_col = "Date Time, GMT-05:00" if site_code in panama_codes else "Date Time, GMT-04:00"

            if datetime_col not in df_a.columns or datetime_col not in df_b.columns:
                print(f"⛔ Skipping {site_code}, file {file_number}: '{datetime_col}' not found.")
                continue

            try:
                first_time_a = pd.to_datetime(df_a.iloc[0][datetime_col], errors='coerce').time()
                first_time_b = pd.to_datetime(df_b.iloc[0][datetime_col], errors='coerce').time()

                today = datetime.today().date()
                dt_a = datetime.combine(today, first_time_a)
                dt_b = datetime.combine(today, first_time_b)

                time_diff = abs(dt_a - dt_b)
            except Exception as e:
                print(f"[ERROR] Error processing {site_code}, file {file_number}: {e}")
                continue

            if time_diff > timedelta(minutes=10):
                file_data['c'] = file_data.pop('a')
                file_data['d'] = file_data.pop('b')
                print(f"🔁 Renamed identifiers at {site_code}, file {file_number}: 'a' → 'c', 'b' → 'd' (offset: {time_diff})")
            else:
                print(f"[OK] Time offset OK for {site_code}, file {file_number}: {time_diff}")


def filter_deployment_log(deployment_df, csv_files):
    """
    Filters the deployment log to only include rows matching file names in csv_files.

    Returns:
        filtered_deployment_df (DataFrame): Filtered deployment log
        csv_file_names (list): Extracted list of file names (no extension)
    """
    csv_file_names = [os.path.splitext(os.path.basename(file))[0] for file in csv_files]
    filtered_df = deployment_df[deployment_df['Offloaded Filename'].isin(csv_file_names)]
    print("[OK] Filtered deployment log:")
    print(filtered_df)
    return filtered_df, csv_file_names


def check_unmatched_filenames(deployment_df, csv_file_names):
    """
    Reports any filenames in csv_files that were not found in the deployment log.
    """
    matched_files = deployment_df['Offloaded Filename'].tolist()
    unmatched_files = [f for f in csv_file_names if f not in matched_files]

    if unmatched_files:
        print("‼️ WARNING: The following files were not found in the deployment log:")
        for f in unmatched_files:
            print(f"  - {f}")
        print("[NOTE] Suggestion: Fix filename in Google Sheet and re-download.")
    else:
        print("[OK] All file names matched with deployment log.")


def validate_time_columns(filtered_df):
    """
    Checks for '?' in Time In or Time Out columns and prints warnings.
    """
    filtered_df['Time In'] = filtered_df['Time In'].astype(str)
    filtered_df['Time Out'] = filtered_df['Time Out'].astype(str)

    rows_with_q = filtered_df[
        filtered_df['Time In'].str.contains(r'\?', na=False) |
        filtered_df['Time Out'].str.contains(r'\?', na=False)
    ]

    if not rows_with_q.empty:
        print("‼️ WARNING: '?' found in time columns for:")
        print(rows_with_q['Offloaded Filename'].tolist())
    else:
        print("[OK] No '?' found in time columns.")

    return filtered_df


def convert_deployment_log_datetime(filtered_df):
    """
    Converts Time and Date columns to datetime objects and creates combined datetime columns.
    """
    # Convert to datetime
    filtered_df['Time In'] = pd.to_datetime(filtered_df['Time In'], format='%H:%M:%S', errors='coerce')
    filtered_df['Time Out'] = pd.to_datetime(filtered_df['Time Out'], format='%H:%M:%S', errors='coerce')
    filtered_df['Date In'] = pd.to_datetime(filtered_df['Date In'], errors='coerce')
    filtered_df['Date Out'] = pd.to_datetime(filtered_df['Date Out'], errors='coerce')

    # Combine into full datetime columns
    filtered_df['Date In Time In'] = pd.to_datetime(
        filtered_df['Date In'].astype(str) + ' ' + filtered_df['Time In'].dt.time.astype(str),
        errors='coerce'
    )
    filtered_df['Date Out Time Out'] = pd.to_datetime(
        filtered_df['Date Out'].astype(str) + ' ' + filtered_df['Time Out'].dt.time.astype(str),
        errors='coerce'
    )

    print("🗓️ Converted date/time columns:")
    print(filtered_df[['Offloaded Filename', 'Date In Time In', 'Date Out Time Out']])
    return filtered_df


def create_deployment_data_dict(filtered_deployment_df):
    deployment_data_dict = {}
    for _, row in filtered_deployment_df.iterrows():
        file_info = {
            'Date In': row['Date In'],
            'Time In': row['Time In'],
            'Date Full': row['Date Full'],
            'Date Out': row['Date Out'],
            'Time Out': row['Time Out'],
            'Date In Time In': row['Date In Time In'],
            'Date Out Time Out': row['Date Out Time Out'],
            'Offloaded Filename': row['Offloaded Filename']
        }
        deployment_data_dict[row['Offloaded Filename']] = file_info
    return deployment_data_dict


def format_deployment_datetimes(deployment_data_dict):
    for file_info in deployment_data_dict.values():
        file_info['Date In Time In'] = file_info['Date In Time In'].strftime('%m/%d/%y %H:%M:%S')
        file_info['Date Out Time Out'] = file_info['Date Out Time Out'].strftime('%m/%d/%y %H:%M:%S')


def plot_pre_trimmed(df_files, panama_codes, save_path):
    os.makedirs(save_path, exist_ok=True)

    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']

                date_column = "Date Time, GMT-05:00" if site_code in panama_codes else "Date Time, GMT-04:00"
                if df[date_column].dtype == 'object':
                    df[date_column] = pd.to_datetime(df[date_column], format='%m/%d/%y %H:%M:%S')

                plt.figure(figsize=(12, 6))
                plt.plot(df[date_column], df['Temp, °C'], color='blue', marker='o', linestyle='-')
                plt.title(f'Pre-Trimmed Temperature: {site_code}_{file_number}_{file_identifier}')
                plt.xlabel('Date Time')
                plt.ylabel('Temp, °C')
                plt.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()

                filename = f"{site_code}_{file_number}_{file_identifier}_pretrimmed.png"
                plt.savefig(os.path.join(save_path, filename))
                plt.close()


def parse_deployment_datetime_strings(deployment_data_dict):
    for file_info in deployment_data_dict.values():
        if isinstance(file_info['Date In Time In'], str):
            file_info['Date In Time In'] = datetime.strptime(file_info['Date In Time In'], '%m/%d/%y %H:%M:%S')
        if isinstance(file_info['Date Out Time Out'], str):
            file_info['Date Out Time Out'] = datetime.strptime(file_info['Date Out Time Out'], '%m/%d/%y %H:%M:%S')


def trim_dataframes_by_date(df_files, deployment_data_dict, panama_codes):
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']
                date_column = "Date Time, GMT-05:00" if site_code in panama_codes else "Date Time, GMT-04:00"

                df[date_column] = pd.to_datetime(df[date_column], format='%m/%d/%y %H:%M:%S')
                file_name = file_info['File Name']
                time_in = deployment_data_dict[file_name]['Date In Time In']
                time_out = deployment_data_dict[file_name]['Date Out Time Out']

                df = df[(df[date_column] >= time_in) & (df[date_column] <= time_out)]
                file_info['DataFrame'] = df


def final_trim_dataframe_edges(df_files, start_cut=4, end_cut=5):
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']
                trimmed_df = df.iloc[start_cut:-end_cut]
                file_info['DataFrame'] = trimmed_df


def check_data_lengths(df_files):
    """
    Checks if each pair of files ('a' and 'b', 'c' and 'd', etc.) for each site_code and file_number
    have the same number of data points.
    """
    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            if len(identifiers) > 1:
                num_rows = {identifier: info['DataFrame'].shape[0] for identifier, info in identifiers.items()}
                if len(set(num_rows.values())) != 1:
                    print(f"Site code: {site_code}, File number: {file_number} have files with different numbers of data points:")
                    for identifier, count in num_rows.items():
                        print(f"  - {identifier}: {count} data points")
                else:
                    print(f"Site code: {site_code}, File number: {file_number} have same data points: {next(iter(num_rows.values()))}.")

def plot_post_trimmed(df_files, panama_codes, save_path):
    os.makedirs(save_path, exist_ok=True)

    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']

                date_column = "Date Time, GMT-05:00" if site_code in panama_codes else "Date Time, GMT-04:00"
                if df[date_column].dtype == 'object':
                    df[date_column] = pd.to_datetime(df[date_column], format='%m/%d/%y %H:%M:%S')

                plt.figure(figsize=(12, 6))
                plt.plot(df[date_column], df['Temp, °C'], color='green', marker='o', linestyle='-')
                plt.title(f'Post-Trimmed Temperature: {site_code}_{file_number}_{file_identifier}')
                plt.xlabel('Date Time')
                plt.ylabel('Temp, °C')
                plt.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()

                filename = f"{site_code}_{file_number}_{file_identifier}_posttrimmed.png"
                plt.savefig(os.path.join(save_path, filename))
                plt.close()

def export_trimmed_csvs(df_files, export_path):
    os.makedirs(export_path, exist_ok=True)
    
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']
                filename = file_info.get('File Name', f"{site_code}_{file_number}_{file_identifier}.csv")
                if not filename.lower().endswith('.csv'):
                    filename += '.csv'
                
                export_filepath = os.path.join(export_path, filename)
                
                # Save trimmed dataframe to CSV
                df.to_csv(export_filepath, index=False)
                print(f"Saving trimmed CSV: {export_filepath}")

def import_trimmed(trimmed_csv, file_pattern='*.csv'):
    """
    Get a list of CSV file paths in the given folder.

    Parameters:
        folder_path (str): Path to the folder containing CSV files.
        file_pattern (str): File matching pattern (default is '*.csv').

    Returns:
        list: List of CSV file paths.
    """
    csv_files = glob.glob(f"{trimmed_csv}/{file_pattern}")
    print(f"Found {len(csv_files)} CSV files.")
    return csv_files



def compute_temperature_difference(df_files):
    """
    Computes temperature difference between 'a' and 'b' files and adds a new column to the 'a' dataframe.
    """
    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers and 'b' in identifiers:
                df_a = identifiers['a']['DataFrame']
                df_b = identifiers['b']['DataFrame']
                if 'Temp, °C' in df_a.columns and 'Temp, °C' in df_b.columns:
                    df_a['Temperature_Difference'] = df_a['Temp, °C'] - df_b['Temp, °C']
                else:
                    print(f"Temp column missing: {site_code}, File Number: {file_number}")
            else:
                print(f"Only one file exists: {site_code}, File Number: {file_number}")


def identify_calculations(df_files):
    """
    Returns a dictionary of calculations that should be flagged for temperature difference issues.
    """
    calculations = {}

    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers:
                df_a = identifiers['a']['DataFrame']
                if 'Temperature_Difference' in df_a.columns:
                    high = df_a[df_a['Temperature_Difference'] > 0.4]
                    moderate = df_a[df_a['Temperature_Difference'] > 0.2]
                    if not high.empty or len(moderate) >= 68:
                        calculations[(site_code, file_number)] = identifiers['a']['File Name']
    return calculations


def build_calc_df_subset(df_files, calculations):
    """
    Builds a dictionary of DataFrames from `df_files` limited to the keys present in `calculations`.
    """
    calc_df_files = {}

    for (site_code, file_number), file_name in calculations.items():
        if site_code in df_files and file_number in df_files[site_code]:
            for identifier in ['a', 'b']:
                df_entry = df_files[site_code][file_number].get(identifier)
                if df_entry:
                    calc_df_files.setdefault(site_code, {}).setdefault(file_number, {})[identifier] = df_entry
    return calc_df_files


def add_comparison_columns(calc_df_files):
    """
    Adds 'Temp A', 'Temp B', 'Average_temp', and 'Flag' columns to 'a' DataFrames.
    """
    for site_code, file_numbers in calc_df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers and 'b' in identifiers:
                df_a = identifiers['a']['DataFrame']
                df_b = identifiers['b']['DataFrame']

                df_a["Temp A"] = df_a["Temp, °C"]
                df_a["Temp B"] = df_b["Temp, °C"]
                df_a["Average_temp"] = (df_a["Temp A"] + df_a["Temp B"]) / 2
                df_a["Flag"] = df_a["Temperature_Difference"].apply(lambda x: "SUPER FLAG" if x > 0.4 else ("FLAG" if x > 0.2 else ""))



def report_flags(calc_df_files):
    """
    Reports flag counts and temperature difference violations for each 'a' file.
    """
    for site_code, file_numbers in calc_df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers:
                df = identifiers['a']['DataFrame']
                true_count = df['Flag'].value_counts().get('FLAG', 0)
                over_0_4 = df[df['Temperature_Difference'] > 0.4]['Temperature_Difference'].round(4).tolist()

                print(f"{site_code} {file_number}, FLAG count: {true_count}, >0.4 count: {len(over_0_4)}")
                if over_0_4:
                    print(f"  >0.4 values: {over_0_4}")


def save_flagged_files(calc_df_files, review_folder):
    """
    Saves filtered and flagged 'a' files as CSVs to the specified output folder.
    """
    if not os.path.exists(review_folder):
        os.makedirs(review_folder)

    for site_code, file_numbers in calc_df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers:
                df = identifiers['a']['DataFrame']
                
                # Convert date column to datetime just once for this dataframe
                df['Date Time, GMT-04:00'] = pd.to_datetime(df['Date Time, GMT-04:00'], errors='coerce')

                first = df['Date Time, GMT-04:00'].iloc[0]
                last = df['Date Time, GMT-04:00'].iloc[-1]
                base_name = f"BT_{site_code}_{first.strftime('%y%m')}_{last.strftime('%y%m')}"

                out_file = os.path.join(review_folder, f"PD_{base_name}.csv")

                df = df[['#', 'Date Time, GMT-04:00', 'Temp A', 'Temp B', 'Temperature_Difference', 'Average_temp', 'Flag']]
                df.rename(columns={'Date Time, GMT-04:00': 'Date Time, UTC-04:00'}, inplace=True)
                df.to_csv(out_file, index=False)
                print(f"Saved: {out_file}")



def average_temperature_if_close(df_files, threshold=0.2):
    """
    Averages temperatures between 'a' and 'b' files if their difference is within the threshold.
    Updates the 'a' DataFrame with the new averaged 'Temp, °C' values.
    """
    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'a' in identifiers and 'b' in identifiers:
                df_a = identifiers['a']['DataFrame']
                df_b = identifiers['b']['DataFrame']

                if 'Temp, °C' in df_a.columns and 'Temp, °C' in df_b.columns:
                    df_a['Temperature_Difference'] = (df_a['Temp, °C'] - df_b['Temp, °C']).abs()
                    df_a['Average_Temperature'] = df_a.apply(
                        lambda row: (row['Temp, °C'] + df_b.loc[row.name, 'Temp, °C']) / 2
                        if row['Temperature_Difference'] <= threshold else None,
                        axis=1
                    )
                    df_a.drop(columns=['Temp, °C', 'Temperature_Difference'], inplace=True)
                    df_a.rename(columns={'Average_Temperature': 'Temp, °C'}, inplace=True)
                else:
                    print(f"Temperature columns not found for Site: {site_code}, File Number: {file_number}")
            else:
                print(f"Averaging skipped: Missing 'a' or 'b' file for Site: {site_code}, File Number: {file_number}")


def report_nan_temperature_differences(df_files, calculations):
    """
    Prints the number of NaNs (temperature mismatches > 0.2°C) in the 'a' DataFrames.
    """
    for (site_code, file_number), file_name in calculations.items():
        if 'a' in df_files[site_code][file_number]:
            df_a = df_files[site_code][file_number]['a']['DataFrame']
            if 'Temp, °C' in df_a.columns:
                nan_count = df_a['Temp, °C'].isna().sum()
                print(f"For file {file_name}: {nan_count} temperature mismatches > 0.2°C")
                print()


def drop_extra_columns(df_files, panama_codes):
    """
    Retains only ['#', date_col, 'Temp, °C'] in all DataFrames.
    Adjusts for different date column names based on site_code.
    """
    for site_code, file_numbers in df_files.items():
        date_col = 'Date Time, GMT-05:00' if site_code in panama_codes else 'Date Time, GMT-04:00'
        columns_to_keep = ['#', date_col, 'Temp, °C']

        for file_number, identifiers in file_numbers.items():
            for file_letter in ['a', 'b', 'c', 'd']:
                if file_letter in identifiers:
                    df = identifiers[file_letter]['DataFrame']
                    if all(col in df.columns for col in columns_to_keep):
                        df = df[columns_to_keep]
                        df_files[site_code][file_number][file_letter]['DataFrame'] = df
                    else:
                        print(f"Missing expected columns in {site_code} {file_number} {file_letter}")

def import_ready(ready_folder, file_pattern='*.csv'):
    """
    Get a list of CSV file paths in the given folder.

    Parameters:
        folder_path (str): Path to the folder containing CSV files.
        file_pattern (str): File matching pattern (default is '*.csv').

    Returns:
        list: List of CSV file paths.
    """
    csv_files = glob.glob(f"{ready_folder}/{file_pattern}")
    print(f"Found {len(csv_files)} CSV files.")
    return csv_files

def plot_temperature_time_series(df_files, panama_codes):
    """
    Plots temperature over time for each DataFrame in df_files.
    Time is displayed as datetime on the x-axis.
    
    Parameters:
    - df_files: nested dict with structure {site_code: {file_number: {identifier: {'DataFrame': df}}}}
    - panama_codes: list or set of site_codes for Panama (to determine date column)
    """
    for site_code, site_data in df_files.items():
        date_col = 'Date Time, UTC-05:00' if site_code in panama_codes else 'Date Time, UTC-04:00'

        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']

                # Ensure date column is datetime type
                df[date_col] = pd.to_datetime(df[date_col])

                # Plot temperature over time
                plt.figure(figsize=(12, 6))
                plt.plot(df[date_col], df['Temperature'], color='blue', marker='o', linestyle='-')
                plt.title(f'Temperature Over Time - Site: {site_code}, File: {file_number}, ID: {file_identifier}')
                plt.xlabel('Date Time')
                plt.ylabel('Temp, °C')
                plt.grid(True)
                plt.xticks(rotation=45)
                plt.tight_layout()
                #plt.show()


def merge_offset_files(df_files, panama_codes):
    """
    Merge 'c' and 'd' DataFrames by datetime for each site and file number.
    Returns a dictionary of merged DataFrames keyed by site_code.
    """
    merged_dict = {}

    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            if 'c' in identifiers and 'd' in identifiers:
                df_c = identifiers['c']['DataFrame']
                df_d = identifiers['d']['DataFrame']

                date_col = "Date Time, GMT-05:00" if site_code in panama_codes else "Date Time, GMT-04:00"

                if date_col not in df_c.columns or date_col not in df_d.columns:
                    print(f"Skipping merge for {site_code}, file {file_number}: Missing datetime column.")
                    continue

                df_c[date_col] = pd.to_datetime(df_c[date_col], errors='coerce')
                df_d[date_col] = pd.to_datetime(df_d[date_col], errors='coerce')

                df_c = df_c[['#', date_col, 'Temp, °C']].rename(columns={'Temp, °C': 'Temp_c'})
                df_d = df_d[['#', date_col, 'Temp, °C']].rename(columns={'Temp, °C': 'Temp_d'})

                merged_df = pd.merge(df_c, df_d, on=date_col, how='outer', suffixes=('_c', '_d'))

                merged_df['Temp, °C'] = merged_df['Temp_c'].combine_first(merged_df['Temp_d'])

                # Merge hash columns if present
                for col_pair in [('#_c', '#_d'), ('#_x', '#_y')]:
                    c_col, d_col = col_pair
                    if c_col in merged_df.columns and d_col in merged_df.columns:
                        merged_df['#'] = merged_df[c_col].combine_first(merged_df[d_col])
                        merged_df.drop(columns=[c_col, d_col], inplace=True)
                        break
                else:  # if no pairs found, check singular hash columns
                    for col in ['#_c', '#_d', '#_x', '#_y']:
                        if col in merged_df.columns:
                            merged_df['#'] = merged_df[col]
                            merged_df.drop(columns=[col], inplace=True)
                            break

                merged_df = merged_df[['#', date_col, 'Temp, °C']]

                merged_dict[site_code] = merged_df
                print(f"Merged Data for Site: {site_code}, File Number: {file_number}")

    # Reassign sequential '#' columns starting from first valid value per site
    for site_code, merged_df in merged_dict.items():
        merged_df['#'] = pd.to_numeric(merged_df['#'], errors='coerce')
        merged_df = merged_df.dropna(subset=['#']).reset_index(drop=True)

        start_value = int(merged_df['#'].iloc[0]) if not merged_df.empty else 1
        merged_df['#'] = range(start_value, start_value + len(merged_df))

        merged_dict[site_code] = merged_df
        print(f"Updated '#' column for Site: {site_code}")

    return merged_dict

def merged_dict_add(df_files):
    """
    Create a merged_dict by collecting DataFrames from df_files where
    the filename or identifier contains 'merged' (case-insensitive).
    
    Returns:
        merged_dict: dict keyed by site_code, value is the merged DataFrame.
    """
    merged_dict = {}

    for site_code, file_numbers in df_files.items():
        for file_number, identifiers in file_numbers.items():
            for identifier, file_info in identifiers.items():
                # Check if 'merged' is in the file name or the identifier key
                filename = file_info.get('File Name', '').lower()
                if 'merged' in filename or 'merged' in identifier.lower():
                    merged_dict[site_code] = file_info['DataFrame']
                    print(f"Added merged file for site {site_code}, file {file_number}, id {identifier}")

    return merged_dict


def plot_offset_agreement(df_files, panama_codes):
    """
    Generate scatter plots comparing 'c' and 'd' logger temperature readings.
    Returns:
        offset_stats: dict of above/below counts for drift inspection.
        drifting: dict of files where agreement fails.
    """

    offset_compare = copy.deepcopy(df_files)
    offset_stats = {}
    drifting = {}

    for site_code, site_data in offset_compare.items():
        date_col = 'Date Time, GMT-05:00' if site_code in panama_codes else 'Date Time, GMT-04:00'

        for file_number, file_data in site_data.items():
            df_c = None
            df_d = None

            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']
                df[date_col] = pd.to_datetime(df[date_col])

                if file_identifier == 'c':
                    df_c = df
                elif file_identifier == 'd':
                    df_d = df

            if df_c is not None and df_d is not None:
                min_len = min(len(df_c), len(df_d))
                temp_c = df_c['Temp, °C'].iloc[:min_len].reset_index(drop=True)
                temp_d = df_d['Temp, °C'].iloc[:min_len].reset_index(drop=True)

                blue_above = sum(tc > td for tc, td in zip(temp_c, temp_d))
                blue_below = sum(tc < td for tc, td in zip(temp_c, temp_d))
                red_above = sum(td > tc for tc, td in zip(temp_c, temp_d))
                red_below = sum(td < tc for tc, td in zip(temp_c, temp_d))

                # Store stats
                offset_stats.setdefault(site_code, {})[file_number] = {
                    'blue_above': blue_above,
                    'blue_below': blue_below,
                    'red_above': red_above,
                    'red_below': red_below
                }

                # Drift agreement check
                if not (blue_above == red_below and blue_below == red_above):
                    drifting.setdefault(site_code, {})[file_number] = {
                        'c': file_data.get('c'),
                        'd': file_data.get('d')
                    }

                # Print + Plot
                print(f"Site: {site_code}, File Number: {file_number}")
                print(f"  Blue points above 1:1 line: {blue_above}")
                print(f"  Blue points below 1:1 line: {blue_below}")
                print(f"  Red points above 1:1 line: {red_above}")
                print(f"  Red points below 1:1 line: {red_below}")

                plt.figure(figsize=(8, 8))
                plt.scatter(temp_c, temp_d, c='blue', s=10, alpha=0.7, label='Logger c')
                plt.scatter(temp_d, temp_c, c='red', s=10, alpha=0.7, label='Logger d')
                min_temp = min(temp_c.min(), temp_d.min())
                max_temp = max(temp_c.max(), temp_d.max())
                plt.plot([min_temp, max_temp], [min_temp, max_temp], color='black', linestyle='--', label='1:1 Line')
                plt.xlabel('Logger c Temp (°C)')
                plt.ylabel('Logger d Temp (°C)')
                plt.title(f'Temperature Agreement - Site: {site_code}, File: {file_number}')
                plt.legend()
                plt.grid(True)
                plt.tight_layout()
                plt.show()

    return offset_stats, drifting

def offload_drifting_files(drifting_dict, review_folder):
    """
    Save 'c' and 'd' files from drifting_dict into review_folder.
    """
    os.makedirs(review_folder, exist_ok=True)

    for site_code, file_numbers in drifting_dict.items():
        for file_number, file_data in file_numbers.items():
            for identifier in ['c', 'd']:
                df = file_data[identifier]['DataFrame']
                original_name = file_data[identifier].get('FileName', f"{site_code}_{file_number}_{identifier}.csv")
                save_name = f"{site_code}_{file_number}_{identifier}_DRIFT.csv"
                save_path = os.path.join(review_folder, save_name)

                df.to_csv(save_path, index=False)
                print(f"Offloaded: {save_name}")

def plot_merged_temperatures(merged_dict, panama_codes):
    """
    Plot merged temperature time series for each site.
    """
    for site_code, merged_df in merged_dict.items():
        date_col = 'Date Time, UTC-05:00' if site_code in panama_codes else 'Date Time, UTC-04:00'

        merged_df[date_col] = pd.to_datetime(merged_df[date_col])

        plt.figure(figsize=(10, 5))
        plt.plot(merged_df[date_col], merged_df['Temperature'], label=f'Site {site_code}', color='b')

        plt.xlabel('Month')
        plt.ylabel('Temperature (°C)')
        plt.title(f'Temperature Time Series for {site_code}')
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator())
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))

        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        #plt.show()


def print_start_end_times(df_files, panama_codes, deployment_data_dict):
    """
    Prints start and end times for each DataFrame in df_files along with deployment data times.
    Also lists any empty DataFrames.
    """
    empty_dataframes = []

    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            for file_identifier, file_info in file_data.items():
                df = file_info['DataFrame']
                date_col = 'Date Time, GMT-05:00' if site_code in panama_codes else 'Date Time, GMT-04:00'

                if not df.empty:
                    print(f"DataFrame Start Time ({site_code}_{file_number}_{file_identifier}):", df[date_col].iloc[0])
                    print(f"DataFrame End Time ({site_code}_{file_number}_{file_identifier}):", df[date_col].iloc[-1])

                    offloaded_file_name = file_info.get('File Name')
                    deployment_data = deployment_data_dict.get(offloaded_file_name)

                    if deployment_data:
                        print(f"Deployment Data Start Time ({offloaded_file_name}):", deployment_data['Date In Time In'])
                        print(f"Deployment Data End Time ({offloaded_file_name}):", deployment_data['Date Out Time Out'])
                    else:
                        print(f"No deployment data found for {offloaded_file_name}")
                    print()
                else:
                    empty_dataframes.append(f"{site_code}_{file_number}_{file_identifier}")

    if empty_dataframes:
        print("Names of empty DataFrames:")
        for name in empty_dataframes:
            print(name)
    else:
        print("No empty DataFrames found.")


def generate_trimmed_filenames(df_files, merged_dict, panama_codes):
    """
    Generates and prints trimmed filenames with date metadata for 'a' files and merged files.
    Does not save files but prints intended filenames.
    """
    # For 'a' files
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            if 'a' in file_data:
                df_a = file_data['a']['DataFrame']
                date_col = 'Date Time, GMT-05:00' if site_code in panama_codes else 'Date Time, UTC-04:00'
                df_a[date_col] = pd.to_datetime(df_a[date_col])

                first_date = df_a[date_col].iloc[0]
                last_date = df_a[date_col].iloc[-1]
                year_month_first = first_date.strftime("%y %m %d")
                year_month_last = last_date.strftime("%y %m %d")

                base_name = f"BT_{site_code}_{year_month_first}_{year_month_last}"
                if (site_code, file_number) in calculations:
                    filename = f"{base_name}_calculations.csv"
                else:
                    filename = f"{base_name}.csv"

                print(f"Intended to save: {filename}")

    # For merged files
    for site_code, df in merged_dict.items():
        date_col = 'Date Time, UTC-05:00' if site_code in panama_codes else 'Date Time, UTC-04:00'
        df[date_col] = pd.to_datetime(df[date_col])

        first_date = df[date_col].iloc[0]
        last_date = df[date_col].iloc[-1]
        year_month_first = first_date.strftime("%y %m %d")
        year_month_last = last_date.strftime("%y %m %d")

        filename = f"BT_{site_code}_{year_month_first}_{year_month_last}.csv"
        print(f"Intended to save: {filename}")


def save_offload_files(df_files, merged_dict, panama_codes, output_folder):
    """
    Saves 'a' version files and merged files as CSVs to the output_folder.
    Adjusts date columns and temperature column names for saving.
    """
    # Save 'a' files
    for site_code, site_data in df_files.items():
        for file_number, file_data in site_data.items():
            if 'a' in file_data:
                df_a = file_data['a']['DataFrame'].copy()
                if site_code in panama_codes:
                    date_col = 'Date Time, GMT-05:00'
                    new_date_col = 'Date Time, UTC-05:00'
                else:
                    date_col = 'Date Time, GMT-04:00'
                    new_date_col = 'Date Time, UTC-04:00'

                df_a.rename(columns={'Temp, °C': 'Temperature'}, inplace=True)
                if date_col in df_a.columns:
                    df_a.rename(columns={date_col: new_date_col}, inplace=True)
                else:
                    print(f"Warning: {date_col} not found in DataFrame for {site_code}. Skipping rename.")
                    continue

                if new_date_col not in df_a.columns:
                    print(f"Error: {new_date_col} column missing after renaming for {site_code}. Skipping file.")
                    continue

                # Convert date column to datetime before using strftime
                df_a[new_date_col] = pd.to_datetime(df_a[new_date_col], errors='coerce')

                first_date = df_a[new_date_col].iloc[0]
                last_date = df_a[new_date_col].iloc[-1]
                year_month_first = first_date.strftime("%y%m")
                year_month_last = last_date.strftime("%y%m")

                base_name = f"BT_{site_code}_{year_month_first}_{year_month_last}"
                filename = f"{base_name}.csv"
                filepath = os.path.join(output_folder, filename)

                decimals = 5
                df_a.to_csv(filepath, index=False, float_format=f"%.{decimals}f")
                print(f"File saved: {filepath}")

    # Save merged files
    for site_code, df in merged_dict.items():
        df = df.copy()
        if site_code in panama_codes:
            date_col = 'Date Time, GMT-05:00'
            new_date_col = 'Date Time, UTC-05:00'
        else:
            date_col = 'Date Time, GMT-04:00'
            new_date_col = 'Date Time, UTC-04:00'

        df.rename(columns={'Temp, °C': 'Temperature'}, inplace=True)
        if date_col in df.columns:
            df.rename(columns={date_col: new_date_col}, inplace=True)
        else:
            print(f"Warning: {date_col} not found in DataFrame for {site_code}. Skipping rename.")
            continue

        if new_date_col not in df.columns:
            print(f"Error: {new_date_col} column missing after renaming for {site_code}. Skipping file.")
            continue

        # Convert date column to datetime before using strftime
        df[new_date_col] = pd.to_datetime(df[new_date_col], errors='coerce')

        first_date = df[new_date_col].iloc[0]
        last_date = df[new_date_col].iloc[-1]
        year_month_first = first_date.strftime("%y%m")
        year_month_last = last_date.strftime("%y%m")

        base_name = f"BT_{site_code}_{year_month_first}_{year_month_last}_merged"
        filename = f"{base_name}.csv"
        filepath = os.path.join(output_folder, filename)

        df.to_csv(filepath, index=False)
        print(f"Merged File saved: {filepath}")


def create_and_save_offload_plots(ready_folder, save_dir, panama_codes):
    """
    Reads exported CSV files from `exported_folder_path`, plots temperature time series,
    and saves plots as PNG files to `plots_path`.

    Args:
        ready_folder (str): Folder path containing exported CSV files.
        plots_path (str): Folder path where plot images will be saved.
        panama_codes (set or list): Set or list of Panama site codes.
    """
    file_pattern = '*.csv'
    csv_files = glob.glob(os.path.join(ready_folder, file_pattern))
    
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        
        # Extract site code from file name (assumes second part of name after split('_'))
        site_code = os.path.basename(csv_file).split('_')[1]

        if site_code in panama_codes:
            date_col = 'Date Time, UTC-05:00'
        else:
            date_col = 'Date Time, UTC-04:00'

        if date_col not in df.columns:
            print(f"Warning: {date_col} not found in DataFrame for {site_code}. Skipping file.")
            continue
        
        # Convert date column to datetime
        try:
            df[date_col] = pd.to_datetime(df[date_col], format='%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error converting date for {site_code} in file {csv_file}: {e}")
            continue

        # Plot temperature over time
        plt.figure(figsize=(12, 6))
        plt.plot(df[date_col], df['Temperature'], color='blue', marker='o', linestyle='-')
        plt.title(f'Temperature Over Time for Site: {site_code}')
        plt.xlabel('Date Time')
        plt.ylabel('Temp, °C')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save plot
        plot_file_name = os.path.splitext(os.path.basename(csv_file))[0] + '_plot.png'
        plot_path = os.path.join(save_dir, plot_file_name)
        plt.savefig(plot_path)
        #plt.show()
        
def trim_dataframe(df_files, site_code, file_number, file_identifier, panama_codes, cutoff_datetime):
    # Check if the file identifier exists for the specified site code and file number
    if file_identifier not in df_files[site_code][file_number]:
        raise KeyError(f"'{file_identifier}' not found for site code '{site_code}' and file number '{file_number}'")
    
    # Access the DataFrame using the site_code, file_number, and file_identifier
    df = df_files[site_code][file_number][file_identifier]['DataFrame']
    
    # Determine the correct date column based on the site code
    date_col = 'Date Time, GMT-05:00' if site_code in panama_codes else 'Date Time, GMT-04:00'
    
    # Trim the DataFrame based on the cutoff datetime
    # > for front end. < for back end.
    trimmed_df = df[df[date_col] <= cutoff_datetime]
    
    # Assign the trimmed DataFrame back to the dictionary
    df_files[site_code][file_number][file_identifier]['DataFrame'] = trimmed_df



# %%
