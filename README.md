# Radar Data Processing Tool

This repository contains a Python script (`check_coordinates.py`) for processing meteorological radar data from the official Hail Suppression Agency of Bulgaria (server IP: 83.228.89.166).

## Overview

The `check_coordinates.py` script provides functionality to:

1. Download H5 format radar files for specific dates
2. Convert geographic coordinates (latitude/longitude) to radar image pixel coordinates (row/column)
3. Extract and convert raw radar values to dBZ (decibel relative to Z) values
4. Filter and display radar data based on dBZ thresholds

## Coordinate Conversion

The script converts WGS84 geographic coordinates (latitude/longitude) to pixel coordinates in the radar image through the following process:

### 1. Coordinate System Transformation

First, the geographic coordinates are transformed from WGS84 (EPSG:4326) to the projection used in the radar data:

```python
# Set up coordinate systems
source_crs = CRS("EPSG:4326")  # WGS84 lat/lon
target_crs = CRS(projdef)      # Projection defined in the file

# Create transformer
transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

# Transform coordinates from lat/lon to projected meters
# Note: pyproj expects (longitude, latitude) order
x_target, y_target = transformer.transform(lon, lat)
x_ul, y_ul = transformer.transform(ul_lon, ul_lat)
```

### 2. Pixel Coordinate Calculation

The projected coordinates (in meters) are then converted to pixel indices using the following formulas:

```
col = (x_target - x_ul) / x_scale
row = (y_ul - y_target) / y_scale
```

Where:
- `x_target`, `y_target`: The projected coordinates of the target point
- `x_ul`, `y_ul`: The projected coordinates of the upper-left corner of the image
- `x_scale`, `y_scale`: The pixel size in meters (from the metadata)

Note that the y-axis for pixels goes down, but for geographic coordinates it goes up, which is why we subtract the target y from the origin's y.

## dBZ Value Calculation

The script converts raw radar values to dBZ using gain and offset parameters from the metadata:

```
dBZ = (raw_value * gain) + offset
```

This conversion follows the standard formula for radar reflectivity as described in the [OPERA Weather Radar Information Model](https://www.eumetnet.eu/wp-content/uploads/2021/07/OPERA_ODIM_H5_v2.4.pdf) (page 27).

The gain and offset values are specific to each radar dataset and are stored in the H5 file metadata under the "what" attributes group.

## Special Values

The script handles special values in the radar data:
- `nodata_val`: Indicates pixels outside the scan area
- `undetect_val`: Indicates clear air with no return signal

## Usage

### Prerequisites

- Python 3.6+
- Required packages: h5py, numpy, pyproj, requests, beautifulsoup4, zoneinfo

### Configuration

Edit the following variables at the top of the script to customize behavior:

```python
H5_DATADIR = './datafiles/'  # Directory for H5 files
TARGET_LAT = 43.492543       # Target latitude
TARGET_LON = 25.500355       # Target longitude
```

### Running the Script

1. To download radar files for a specific date:
   ```python
   download_radar_files_for_date('YYYY-MM-DD')
   ```

2. To process all H5 files in the data directory and display values above 40 dBZ:
   ```
   python check_coordinates.py
   ```

## Data Source

The radar data is provided by the official Hail Suppression Agency of Bulgaria and can be accessed at http://83.228.89.166/.


## Sample output (with real data)

```csv
TARGET_LAT = 43.492543
TARGET_LON = 25.500355

Time (UTC): 2024-05-12 18:36:39          Value: 41.00 dBZ        File: Composite.20240512183639.CAP.7370.h5
Time (UTC): 2024-05-12 18:40:30          Value: 41.00 dBZ        File: Composite.20240512184030.CAP.7371.h5
Time (UTC): 2024-05-12 18:41:18          Value: 46.00 dBZ        File: Composite.20240512184118.CAP.7372.h5
Time (UTC): 2024-05-12 18:45:18          Value: 49.00 dBZ        File: Composite.20240512184518.CAP.7373.h5
Time (UTC): 2024-05-12 18:49:21          Value: 52.00 dBZ        File: Composite.20240512184921.CAP.7374.h5
Time (UTC): 2024-05-12 18:53:20          Value: 50.50 dBZ        File: Composite.20240512185320.CAP.7375.h5
Time (UTC): 2024-05-12 18:55:51          Value: 51.00 dBZ        File: Composite.20240512185551.CAP.7376.h5
Time (UTC): 2024-05-12 18:59:40          Value: 53.50 dBZ        File: Composite.20240512185940.CAP.7377.h5
Time (UTC): 2024-05-12 19:01:20          Value: 53.50 dBZ        File: Composite.2024051219120.CAP.7378.h5
Time (UTC): 2024-05-12 19:05:20          Value: 50.50 dBZ        File: Composite.2024051219520.CAP.7379.h5
Time (UTC): 2024-05-12 19:09:20          Value: 53.50 dBZ        File: Composite.2024051219920.CAP.7380.h5
Time (UTC): 2024-05-12 19:13:19          Value: 54.00 dBZ        File: Composite.20240512191319.CAP.7381.h5
Time (UTC): 2024-05-12 19:17:18          Value: 53.50 dBZ        File: Composite.20240512191718.CAP.7382.h5
Time (UTC): 2024-05-12 19:21:18          Value: 52.00 dBZ        File: Composite.20240512192118.CAP.7383.h5
Time (UTC): 2024-05-12 19:25:17          Value: 55.00 dBZ        File: Composite.20240512192517.CAP.7384.h5
Time (UTC): 2024-05-12 19:29:19          Value: 55.00 dBZ        File: Composite.20240512192919.CAP.7385.h5
Time (UTC): 2024-05-12 19:33:20          Value: 47.50 dBZ        File: Composite.20240512193320.CAP.7386.h5
Time (UTC): 2024-05-12 19:37:55          Value: 42.50 dBZ        File: Composite.20240512193755.CAP.7388.h5
Time (UTC): 2024-05-12 19:37:55          Value: 44.50 dBZ        File: Composite.20240512193755.CAP.7387.h5
Time (UTC): 2024-05-12 19:41:25          Value: 42.50 dBZ        File: Composite.20240512194125.CAP.7389.h5
Time (UTC): 2024-05-12 19:45:26          Value: 41.00 dBZ        File: Composite.20240512194526.CAP.7390.h5
Time (UTC): 2024-05-22 05:53:57          Value: 40.00 dBZ        File: Composite.20240522055357.CAP.1114.h5
Time (UTC): 2024-05-22 05:57:58          Value: 40.50 dBZ        File: Composite.20240522055758.CAP.1115.h5
```