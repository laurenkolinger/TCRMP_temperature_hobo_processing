"""
Update combined raw files with new data from the READY folder.
- Uses site metadata CSV to map 6-letter codes to location names.
- Reads READY CSVs and appends only new records to combined files.
- Splits datetime into separate Date and Time columns.
- Sorts all data oldest to newest.
- Preserves the Location,Date,Time,Temperature column format.
"""

import os
import glob
import re
import pandas as pd

from config import CONFIG, get_path_for, resolve_path

# Paths from config
ready_folder = get_path_for("05_READY")
combined_path = resolve_path(CONFIG.get('EXPORT_COMBINED_PATH', ''))
metadata_csv_path = resolve_path(CONFIG['SITE_METADATA_CSV'])


def load_site_code_to_location():
    """Load site metadata CSV and return a dict mapping 6-letter code to location name."""
    metadata_df = pd.read_csv(metadata_csv_path, dtype=str)
    mapping = {}
    for _, row in metadata_df.iterrows():
        code = row['6LetterCode']
        location = row['Location']
        if pd.isna(code) or pd.isna(location):
            continue
        mapping[code] = location.replace(' ', '_')
    return mapping


def get_panama_codes():
    """Return set of Panama site codes (use helper if available, else empty)."""
    try:
        from QAQC_HELPER_FUNCTIONS import get_panama_site_codes
        return set(get_panama_site_codes())
    except ImportError:
        return set()


def read_ready_csv(filepath, panama_codes):
    """Read a READY CSV and return a DataFrame with _datetime and Temperature columns."""
    df = pd.read_csv(filepath, dtype=str)

    # Determine date column
    site_code = os.path.basename(filepath).split('_')[1]
    if site_code in panama_codes:
        date_col = 'Date Time, UTC-05:00'
    else:
        date_col = 'Date Time, UTC-04:00'

    if date_col not in df.columns:
        print(f"  WARNING: {date_col} not found in {filepath}")
        return pd.DataFrame()

    df['_datetime'] = pd.to_datetime(df[date_col], format='mixed', dayfirst=False)

    # Find temperature column
    temp_col = None
    for col in df.columns:
        if 'temp' in col.lower():
            temp_col = col
            break

    if temp_col is None:
        print(f"  WARNING: No temperature column found in {filepath}")
        return pd.DataFrame()

    result = pd.DataFrame()
    result['_datetime'] = df['_datetime']
    result['Temperature'] = df[temp_col]
    return result


def read_combined_raw(filepath):
    """Read an existing combined raw CSV and parse dates."""
    try:
        df = pd.read_csv(filepath, dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, dtype=str, encoding='latin-1')

    df['_datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='mixed', dayfirst=False)
    return df


def process_site(site_code, location_name, ready_files, panama_codes):
    """Process a single site: read combined raw, read READY CSVs, merge, sort, write."""
    print(f"\nProcessing: {location_name} ({site_code})")

    combined_filename = f"TCRMP_temp_{location_name}_raw.csv"
    combined_filepath = os.path.join(combined_path, combined_filename)

    # Read existing combined file if it exists
    if os.path.exists(combined_filepath):
        raw_df = read_combined_raw(combined_filepath)
        raw_max_date = raw_df['_datetime'].max()
        print(f"  Existing records: {len(raw_df)}, latest: {raw_max_date}")
    else:
        print(f"  No existing combined file, skipping.")
        return

    # Read all READY CSVs for this site
    existing_dates = set(raw_df['_datetime'].dropna())
    new_rows = []
    for ready_file in ready_files:
        ready_df = read_ready_csv(ready_file, panama_codes)
        if ready_df.empty:
            continue
        # Keep rows whose datetime doesn't already exist in the combined file
        new_data = ready_df[~ready_df['_datetime'].isin(existing_dates)]
        if not new_data.empty:
            new_rows.append(new_data)
            print(f"  {os.path.basename(ready_file)}: {len(new_data)} new records")

    if not new_rows:
        print(f"  No new data to add.")
        return

    new_df = pd.concat(new_rows, ignore_index=True)
    new_df['Location'] = location_name.replace('_', ' ')
    print(f"  Total new records to add: {len(new_df)}")

    # Combine existing data with new data
    combined = pd.concat([
        raw_df[['Location', '_datetime', 'Temperature']],
        new_df[['Location', '_datetime', 'Temperature']]
    ], ignore_index=True)

    # Fill any blank/missing Location values
    loc_name_display = location_name.replace('_', ' ')
    combined['Location'] = combined['Location'].fillna(loc_name_display)
    combined['Location'] = combined['Location'].replace('', loc_name_display)

    # Drop duplicates based on datetime and temperature
    combined = combined.drop_duplicates(subset=['_datetime', 'Temperature']).reset_index(drop=True)

    # Sort oldest to newest
    combined = combined.sort_values('_datetime').reset_index(drop=True)

    # Format Date and Time columns
    combined['Date'] = combined['_datetime'].dt.strftime('%Y-%m-%d')
    combined['Time'] = combined['_datetime'].dt.strftime('%H:%M')

    # Write output
    combined[['Location', 'Date', 'Time', 'Temperature']].to_csv(combined_filepath, index=False)
    print(f"  Updated! Total records: {len(combined)}, latest: {combined['_datetime'].max()}")


def main():
    if not combined_path or not os.path.exists(combined_path):
        print(f"[ERROR] Combined path not configured or does not exist: {combined_path}")
        print("Set EXPORT_COMBINED_PATH in config.py and ensure the folder exists.")
        return

    # Load site code to location mapping
    code_to_location = load_site_code_to_location()
    panama_codes = get_panama_codes()

    # Find all READY CSVs
    ready_files = glob.glob(os.path.join(ready_folder, 'BT_*.csv'))
    if not ready_files:
        print(f"[WARN] No READY files found in {ready_folder}")
        return

    # Group READY files by site code
    site_files = {}
    for ready_file in ready_files:
        basename = os.path.basename(ready_file)
        match = re.match(r'BT_([A-Z]+\d*)_', basename)
        if match:
            site_code = match.group(1)
            site_files.setdefault(site_code, []).append(ready_file)

    print(f"Found {len(ready_files)} READY file(s) across {len(site_files)} site(s)")
    print(f"Combined output folder: {combined_path}\n")

    processed = 0
    skipped = 0
    for site_code, files in sorted(site_files.items()):
        location_name = code_to_location.get(site_code)
        if not location_name:
            print(f"\n[WARN] No location name found for {site_code}, skipping")
            skipped += 1
            continue
        process_site(site_code, location_name, files, panama_codes)
        processed += 1

    print(f"\n{'='*60}")
    print(f"Done! Processed {processed} sites, skipped {skipped} sites.")


if __name__ == '__main__':
    main()
