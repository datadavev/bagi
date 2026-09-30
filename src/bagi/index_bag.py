"""
Create a parquet index of a bagit zip file.
"""

import io
import json
import logging
import os
import os.path
import tempfile
import zipfile
from datetime import datetime

import duckdb
from PIL import Image
from PIL.ExifTags import GPSTAGS, IFD


def get_logger():
    return logging.getLogger()


def convert_to_degrees(value):
    """Helper to convert GPS coordinate tuples to decimal degrees."""
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def get_gps_coordinates(gps_info):
    """Extracts and converts latitude and longitude from GPS info dictionary."""
    lat, lon = None, None
    lat_ref, lon_ref = None, None

    for key, val in gps_info.items():
        name = GPSTAGS.get(key, key)
        if name == "GPSLatitude":
            lat = convert_to_degrees(val)
        elif name == "GPSLatitudeRef":
            lat_ref = val
        elif name == "GPSLongitude":
            lon = convert_to_degrees(val)
        elif name == "GPSLongitudeRef":
            lon_ref = val

    # Adjust based on hemisphere references
    if lat and lat_ref and lat_ref.upper() == "S":
        lat = -lat
    if lon and lon_ref and lon_ref.upper() == "W":
        lon = -lon

    return lat, lon


def get_image_metadata_from_zip(zip_path):
    image_records = []
    image_extensions = (".jpg", ".jpeg", ".tiff", ".png")

    with zipfile.ZipFile(zip_path, "r") as zf:
        for file_info in zf.infolist():
            # Skip directories and non-image files
            if file_info.is_dir() or not file_info.filename.lower().endswith(
                image_extensions
            ):
                continue

            try:
                # Read image in memory without extracting to disk
                with zf.open(file_info) as f:
                    img_bytes = f.read()
                    with Image.open(io.BytesIO(img_bytes)) as img:
                        exif = img.getexif()

                        date_taken = None
                        lat, lon = None, None
                        gps_info = None

                        if exif:
                            # Retrieve DateTimeOriginal from the Exif IFD
                            # (or fallback to IFD0)
                            date_str = None
                            try:
                                exif_ifd = exif.get_ifd(IFD.Exif)
                                date_str = exif_ifd.get(36867)  # DateTimeOriginal
                            except KeyError:
                                pass

                            if not date_str:
                                date_str = exif.get(306)  # DateTime fallback in IFD0
                                if date_str:
                                    try:
                                        date_taken = datetime.strptime(
                                            date_str, "%Y:%m:%d %H:%M:%S"
                                        )
                                    except (ValueError, TypeError):
                                        date_taken = None

                            # Retrieve GPS Info from the GPS IFD
                            try:
                                gps_info = exif.get_ifd(IFD.GPSInfo)
                                if gps_info:
                                    lat, lon = get_gps_coordinates(gps_info)
                            except KeyError:
                                pass

                            if gps_info:
                                lat, lon = get_gps_coordinates(gps_info)

                        image_records.append(
                            {
                                "path": file_info.filename,
                                "date_created": date_taken.isoformat()
                                if date_taken
                                else None,
                                "latitude": lat,
                                "longitude": lon,
                            }
                        )
            except Exception as e:
                print(f"Could not read metadata for {file_info.filename}: {e}")

    return image_records


def create_parquet_index(zip_file) -> int:
    _L = get_logger()
    nrecords = 0
    records = get_image_metadata_from_zip(zip_file)
    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        delete_on_close=False,
        encoding="utf-8",
        suffix=".ndjson",
    ) as ndtemp:
        temp_ndjson_path = ndtemp.name
        for entry in records:
            ndtemp.write(json.dumps(entry, ensure_ascii=False) + "\n")
            nrecords += 1

    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, delete_on_close=False, suffix=".parquet"
    ) as tmp_index:
        temp_parquet_path = tmp_index.name

    conn = duckdb.connect()
    longitude_col = "longitude"
    latitude_col = "latitude"
    geometry_crs = "EPSG:4326"
    conn.execute("INSTALL spatial;")
    conn.execute("LOAD spatial;")
    query = f"""
    COPY (
      SELECT
        * EXCLUDE ({longitude_col}, {latitude_col}),
        CASE
          WHEN
            {longitude_col} IS NOT NULL AND {latitude_col} IS NOT NULL
          THEN
            ST_SetCRS(
              ST_Point({longitude_col}::DOUBLE, {latitude_col}::DOUBLE),
              '{geometry_crs}')
          ELSE NULL
        END AS geometry
      FROM read_json_auto('{temp_ndjson_path}')
    )
    TO '{temp_parquet_path}'
    (FORMAT PARQUET, COMPRESSION ZSTD);
    """
    _L.debug(query)
    conn.execute(query)

    # clean up the temporary json file
    if os.path.exists(temp_ndjson_path):
        os.unlink(temp_ndjson_path)

    # Insert the parquet file into the
    with zipfile.ZipFile(zip_file, "a") as catalog:
        catalog.write(temp_parquet_path, arcname="index.parquet")

    # clean up the temporary json file
    if os.path.exists(temp_parquet_path):
        os.unlink(temp_parquet_path)
    return nrecords
