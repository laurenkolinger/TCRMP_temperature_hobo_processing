# NCPLOT.PY

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
import xarray as xr
import yaml

# Set paths from config
from config import CONFIG, get_path_for
from processing_logger import ProcessingLogger
import re

ready_folder = get_path_for("05_READY")
save_dir = get_path_for("02_PLOTS/ready")
nc_folder = get_path_for("06_NETCDF")
log_dir = get_path_for("07_METADATA/processing_logs")
metadata_folder = os.path.join(CONFIG['WORKFLOW_DIRECTORY'], "Site_Metadata")
metadata_csv = os.path.join(os.path.dirname(CONFIG['BASE_DIRECTORY']),"TCRMP_TempSiteMetadata.csv")


#%% IMPORT FUNCTIONS
from QAQC_HELPER_FUNCTIONS import (
    import_ready,
    get_usvi_site_codes,
    get_panama_site_codes,
    load_structured_dataframes,
    plot_temperature_time_series,
    merged_dict_add,
    plot_merged_temperatures,
    generate_trimmed_filenames,
    create_and_save_offload_plots
    
)

# 1. Get ready files
csv_files = import_ready(ready_folder)

# 2. Get site codes lists
usvi_codes = get_usvi_site_codes()
panama_codes = get_panama_site_codes()

# 4. Load CSVs into nested dict structure
df_files = load_structured_dataframes(csv_files, usvi_codes, panama_codes)

# 30. Plot temperature time series for all data (post-trim and cleaning)
plot_temperature_time_series(df_files, panama_codes)

# 32. Add the files that have "merged" in the name to merged dict
merged_offset_data = merged_dict_add(df_files)

# 33. Plot merged temperature time series for each site from merged data
plot_merged_temperatures(merged_offset_data, panama_codes)

# 35. Generate and print trimmed filenames for 'a' files and merged files (no saving)
generate_trimmed_filenames(df_files, merged_offset_data, panama_codes)

# 37. Create and save plots from exported CSV files in exported_folder_path to save_dir
create_and_save_offload_plots(ready_folder, save_dir, panama_codes)


def load_site_metadata(metadata_folder, site_code):
    filepath = os.path.join(metadata_folder, f"{site_code}.yaml")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Metadata file not found for site: {site_code}")
    with open(filepath, 'r') as f:
        full_yaml = yaml.safe_load(f)
    if site_code not in full_yaml:
        raise KeyError(f"Site code {site_code} not found in YAML file")
    return full_yaml[site_code]

def extract_site_code(filename):
    parts = os.path.basename(filename).split('_')
    return parts[1] if len(parts) > 1 else os.path.splitext(filename)[0]

def make_netcdf(df, site_code, global_attrs, var_attrs, *output_paths):
    """
    Create and save a NetCDF file for the given dataframe and site metadata.

    Parameters:
        df (pd.DataFrame): DataFrame with 'Time' and measurement columns.
        site_code (str): Site code for metadata lookup.
        global_attrs (dict): Global attributes for the NetCDF.
        var_attrs (dict): Variable-specific attributes.
        *output_paths (str): One or more paths to save the NetCDF file.
    """
    df = df.copy()  # ensure original df isn't modified
    df['Time'] = pd.to_datetime(df['Time'])
    df.set_index('Time', inplace=True)

    ds = xr.Dataset.from_dataframe(df)
    ds = ds.assign_coords(Time=("Time", df.index.astype("datetime64[s]").astype(int)))
    if 'Time' in var_attrs:
        ds['Time'].attrs.update(var_attrs['Time'])

    # Handle latitude and longitude strings
    latlon_str = global_attrs.get('geospatial_lat_max', '')
    if ',' in latlon_str:
        lat_str, lon_str = latlon_str.split(',')
        lat = float(lat_str)
        lon = float(lon_str)
    else:
        lat = float(global_attrs.get('geospatial_lat_max', 0))
        lon = float(global_attrs.get('geospatial_lon_max', 0))

    depth_val = float(global_attrs['depth'].split()[0])

    ds['latitude'] = xr.DataArray([lat], dims="latitude", attrs={
        'standard_name': 'latitude',
        'units': 'degrees_north',
        'axis': 'Y'
    })

    ds['longitude'] = xr.DataArray([lon], dims="longitude", attrs={
        'standard_name': 'longitude',
        'units': 'degrees_east',
        'axis': 'X'
    })

    ds['depth'] = xr.DataArray([depth_val], dims="depth", attrs=var_attrs.get('depth', {
        'standard_name': 'depth',
        'units': 'm',
        'positive': 'down',
        'axis': 'Z'
    }))

    start_time = df.index.min().isoformat()
    end_time = df.index.max().isoformat()
    date_created = pd.Timestamp.utcnow().isoformat()

    global_attrs_copy = global_attrs.copy()
    global_attrs_copy['time_coverage_start'] = start_time
    global_attrs_copy['time_coverage_end'] = end_time
    global_attrs_copy['date_created'] = date_created

    ds.attrs.update(global_attrs_copy)

    for var, attrs in var_attrs.items():
        if var in ds.variables:
            ds[var].attrs.update(attrs)

    # Save to all specified output paths
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ds.to_netcdf(path)
        print(f"Saved: {path}")

# Load the metadata CSV once
metadata_df = pd.read_csv(metadata_csv, dtype=str)
metadata_df.set_index("6LetterCode", inplace=True)

def get_location_from_code(site_code):
    """Return Location name for a given 6-letter site code from metadata CSV."""
    try:
        location = metadata_df.loc[site_code, "Location"]
        return location.replace(" ", "_")  # safe folder name
    except KeyError:
        print(f"Warning: Site code {site_code} not found in metadata CSV.")
        return site_code  # fallback to site code

def main():
    os.makedirs(nc_folder, exist_ok=True)
    csv_files = glob.glob(os.path.join(ready_folder, '*.csv'))

    for csv_file in csv_files:
        site_code = extract_site_code(csv_file)
        print(f"Processing site: {site_code}")

        df = pd.read_csv(csv_file)
        df.rename(columns={
            '#': 'Number',
            'Date Time, UTC-04:00': 'Time',
            'Temp, °C': 'Temperature'
        }, inplace=True)

        site_metadata = load_site_metadata(metadata_folder, site_code)
        global_attrs = site_metadata.get('global_attributes', {})
        var_attrs = site_metadata.get('variable_attributes', {})

        base_name = os.path.splitext(os.path.basename(csv_file))[0]

        # Path for standard NC folder (always save here)
        output_path = os.path.join(nc_folder, f"{base_name}.nc")
        
        # Collect all output paths
        output_paths = [output_path]
        
        # Check if export path is configured
        export_nc_path = CONFIG.get('EXPORT_NETCDF_PATH', '')
        if export_nc_path and os.path.exists(export_nc_path):
            # Path for NC export folder (site-specific subfolder)
            location_name = get_location_from_code(site_code)
            site_nc_folder = os.path.join(export_nc_path, location_name)
            os.makedirs(site_nc_folder, exist_ok=True)
            export_output_path = os.path.join(site_nc_folder, f"{base_name}.nc")
            output_paths.append(export_output_path)
            print(f"  [EXPORT] Will export to: {location_name}/")

        # Save to all configured locations
        make_netcdf(df, site_code, global_attrs, var_attrs, *output_paths)
        
        # Update processing log
        match = re.match(r'BT_([A-Z]+\d*)_(\d{4})', base_name)
        if match:
            site = match.group(1)
            start_yymm = match.group(2)
            log_file = os.path.join(log_dir, f"{site}_{start_yymm}.json")
            if os.path.exists(log_file):
                logger = ProcessingLogger(site, start_yymm, log_dir)
                logger.add_processing_step(
                    step_name="NCPLOT",
                    action="Generated NetCDF and final plot",
                    details=f"CF-1.6 compliant, metadata from {site_code}.yaml",
                    outputs=["NetCDF file", "final plot"]
                )
                print(f"  [OK] Log updated: {site}_{start_yymm}.json")

if __name__ == '__main__':
    main()
