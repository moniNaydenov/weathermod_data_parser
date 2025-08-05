import h5py
import numpy as np
from datetime import datetime, timezone
from pyproj import CRS, Transformer
import os
from zoneinfo import ZoneInfo # Import ZoneInfo for timezone conversion
import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path
import sys


# --- User Configuration ---
H5_DATADIR = './datafiles/'  # Directory where the HDF5 file is located
DATASET_PATH = '/dataset1/data1/data'  # Path to the actual data array
WHERE_GROUP_PATH = '/where'  # Path to the 'where' group with geo-info
WHAT_GROUP_PATH = '/dataset1/what' # Path to the 'what' group for metadata
HOW_GROUP_PATH = '/how'

# Target coordinate to get data for (Example: Sofia, Bulgaria)
TARGET_LAT = 43.492543
TARGET_LON = 25.500355
SERVER_URL = "http://83.228.89.166/"
sofia_tz = ZoneInfo("Europe/Sofia")


def download_radar_files_for_date(date_str: str):
    """
    Downloads all composite H5 files for a specific date from the server.

    Args:
        date_str: The date in "YYYY-MM-DD" format.
    """
    print(f"--- Starting process for date: {date_str} ---")

    # 1. Prepare directory and date format
    download_path = Path(H5_DATADIR)
    download_path.mkdir(parents=True, exist_ok=True)

    try:
        # Convert "YYYY-MM-DD" to "YYYYMMDD" for the filename pattern
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        filename_date_prefix = date_obj.strftime('%Y%m%d')
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD.")
        return

    # 2. Fetch the main page from the server
    try:
        print(f"Fetching link list from {SERVER_URL}...")
        response = requests.get(SERVER_URL)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the server page: {e}")
        return

    # 3. Parse HTML and find all matching file links
    soup = BeautifulSoup(response.text, 'html.parser')

    # Regex to find files for the specific date, e.g., "Composite.20240512...*.h5"
    # It looks for "Composite." + "YYYYMMDD" + any characters + ".h5"
    file_pattern = re.compile(r"Composite\." + filename_date_prefix + r".*\.h5")

    links_to_download = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and file_pattern.match(href):
            links_to_download.append(href)

    if not links_to_download:
        print(f"No files found for date {date_str} with pattern '{file_pattern.pattern}'")
        return

    print(f"Found {len(links_to_download)} files to potentially download.")

    # 4. Download each file
    for filename in links_to_download:
        file_url = SERVER_URL + filename
        local_file_path = download_path / filename

        # Skip if the file already exists
        if local_file_path.exists():
            print(f"Skipping {filename}, already exists.")
            continue

        try:
            print(f"Downloading {filename}...")
            # Use stream=True for large files to avoid loading all content into memory
            with requests.get(file_url, stream=True) as r:
                r.raise_for_status()
                with open(local_file_path, 'wb') as f:
                    # Write the file in chunks
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"Successfully downloaded {filename}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {filename}: {e}")

    print("\n--- Process finished. ---")

def get_radar_value_at_coord(h5_file, lat, lon):
    """
    Extracts a data value from a projected HDF5 file for a given lat/lon.
    """
    rawfilename = h5_file
    h5_file = os.path.join(H5_DATADIR, h5_file)
    with h5py.File(h5_file, 'r') as f:
        what_attrs = f[WHAT_GROUP_PATH].attrs
        date_str = what_attrs['enddate'].decode('ascii')  # e.g., '20240512'
        time_str = what_attrs['endtime'].decode('ascii')  # e.g., '221009'
        how_attrs = f[HOW_GROUP_PATH].attrs

        # Combine and parse into a datetime object
        timestamp_str = date_str + time_str
        dt_object = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')

        # Conversion and special value metadata (NEW)
        gain = what_attrs['gain']
        offset = what_attrs['offset']
        nodata_val = what_attrs['nodata']
        undetect_val = what_attrs['undetect']

        # Assume the parsed time is UTC and make it timezone-awarevv
        end_epoch = how_attrs['endepochs']
        dt_utc = datetime.fromtimestamp(end_epoch, tz=timezone.utc)

        # 1. Read metadata from the 'where' group
        where_attrs = f[WHERE_GROUP_PATH].attrs
        projdef = where_attrs['projdef'].decode('ascii')
        ul_lon = where_attrs['UL_lon']
        ul_lat = where_attrs['UL_lat']
        x_scale = where_attrs['xscale']
        y_scale = where_attrs['yscale']

        dset = f[DATASET_PATH]
        ysize, xsize = dset.shape

        # 2. Set up coordinate systems
        # The source is standard WGS84 latitude/longitude
        source_crs = CRS("EPSG:4326")
        # The target is the projection defined in the file
        target_crs = CRS(projdef)

        # Create a transformer to convert from lat/lon to the projection's x/y
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

        # 3. Transform coordinates from lat/lon to projected meters
        # Note: pyproj expects (longitude, latitude)
        x_target, y_target = transformer.transform(lon, lat)
        x_ul, y_ul = transformer.transform(ul_lon, ul_lat)

        # 4. Calculate pixel indices from meter offsets
        # The y-axis for pixels goes down, but for coordinates it goes up.
        # So we subtract the target y from the origin's y.
        col = (x_target - x_ul) / x_scale
        row = (y_ul - y_target) / y_scale

        # Round to the nearest integer pixel
        col_idx = int(round(col))
        row_idx = int(round(row))


        #print(f"Target      (Lat, Lon): ({lat:.4f}, {lon:.4f})")
        #print(f"Projected   (X, Y) m: ({x_target:.2f}, {y_target:.2f})")
        print(f"Calculated Pixel (Y, X): ({row_idx}, {col_idx})")

        # 5. Validate and extract data
        realvalue = "Not in data"
        real_dbz = 0.0
        if 0 <= row_idx < ysize and 0 <= col_idx < xsize:
            raw_value = dset[row_idx, col_idx]

            if raw_value == nodata_val:
                realvalue = "No Data (pixel is outside the scan area)"
            elif raw_value == undetect_val:
                realvalue = "Undetected (clear air, no return signal)"
            else:
                # Apply the conversion formula
                real_dbz = (raw_value * gain) + offset
                realvalue = f"{real_dbz:.2f} dBZ"
            #print(f"Time (UTC):   {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} \t Value: {realvalue}")
        else:
            #print("\nERROR: The specified coordinate is outside the radar image bounds.")
            pass
        return (end_epoch, realvalue, real_dbz, rawfilename)


# --- Run the function ---
if __name__ == "__main__":
    #download_radar_files_for_date('2024-05-22')
    #sys.exit(0)
    parseddata = []
    for filename in os.listdir(H5_DATADIR):
        if filename.endswith('.h5'):
            result = get_radar_value_at_coord(filename, TARGET_LAT, TARGET_LON)
            parseddata.append(result)

    # sort by time
    parseddata.sort(key=lambda x: x[0])
    # Print results
    for (epoch, value, dbz, filename) in parseddata:
        if dbz >= 40:
            dt_utc = datetime.fromtimestamp(epoch, tz=timezone.utc)
            print(f"Time (UTC): {dt_utc.strftime('%Y-%m-%d %H:%M:%S')} \t Value: {value} \t File: {filename}")