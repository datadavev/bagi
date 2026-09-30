from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Import functions from your main script
from bagi.index_bag import (
    convert_to_degrees,
    get_gps_coordinates,
    get_image_metadata_from_zip,
)


def test_convert_to_degrees():
    """Test conversion of degrees, minutes, seconds tuple to decimal degrees."""
    val = (38, 58, 0)
    # 38 + 58/60 = 38.96666...
    assert convert_to_degrees(val) == pytest.approx(38.966666, rel=1e-5)


def test_get_gps_coordinates_north_east():
    """Test GPS coordinate parsing for Northern and Eastern hemispheres."""
    # Tag 2 = GPSLatitude, 1 = GPSLatitudeRef, 4 = GPSLongitude, 3 = GPSLongitudeRef
    gps_info = {
        2: (38, 0, 0),
        1: "N",
        4: (75, 0, 0),
        3: "E",
    }
    lat, lon = get_gps_coordinates(gps_info)
    assert lat == 38.0
    assert lon == 75.0


def test_get_gps_coordinates_south_west():
    """Test GPS coordinate parsing for Southern and Western hemispheres
    (negative values)."""
    gps_info = {
        2: (33, 51, 0),
        1: "S",
        4: (151, 12, 0),
        3: "W",
    }
    lat, lon = get_gps_coordinates(gps_info)
    assert lat == pytest.approx(-33.85, rel=1e-2)
    assert lon == pytest.approx(-151.2, rel=1e-2)


@patch("zipfile.ZipFile")
@patch("PIL.Image.open")
def test_get_image_metadata_success(mock_image_open, mock_zip_file):
    mock_file_info = MagicMock()
    mock_file_info.filename = "subfolder/vacation.jpg"
    mock_file_info.is_dir.return_value = False

    # Mock the file-like object returned by zf.open()
    mock_file_obj = MagicMock()
    mock_file_obj.read.return_value = b"fake-image-bytes"

    mock_zf = MagicMock()
    mock_zf.infolist.return_value = [mock_file_info]
    mock_zf.open.return_value.__enter__.return_value = mock_file_obj
    mock_zip_file.return_value.__enter__.return_value = mock_zf

    # Mock modern getexif() object and its sub-IFDs via get_ifd()
    mock_exif = MagicMock()

    def mock_get_ifd(ifd_id):
        if ifd_id == 34665:  # IFD.Exif
            return {36867: "2026:06:15 14:20:00"}
        if ifd_id == 34853:  # IFD.GPSInfo
            return {2: (38, 0, 0), 1: "N", 4: (76, 0, 0), 3: "W"}
        return {}

    mock_exif.get_ifd.side_effect = mock_get_ifd

    mock_img = MagicMock()
    mock_img.getexif.return_value = mock_exif
    # Ensure the image object acts correctly as a context manager
    # (`with Image.open(...) as img:`)
    mock_img.__enter__.return_value = mock_img

    mock_image_open.return_value = mock_img

    results = get_image_metadata_from_zip("dummy.zip")

    assert len(results) == 1
    print(results[0])
    assert results[0]["path"] == "subfolder/vacation.jpg"
    assert isinstance(results[0]["date_created"], datetime)
    assert results[0]["date_created"] == datetime(2026, 6, 15, 14, 20, 0)
    assert results[0]["latitude"] == 38.0
    assert results[0]["longitude"] == -76.0


@patch("zipfile.ZipFile")
@patch("PIL.Image.open")
def test_get_image_metadata_invalid_date_and_no_gps(mock_image_open, mock_zip_file):
    """Test graceful handling of malformed EXIF dates and missing GPS data."""
    mock_file_info = MagicMock()
    mock_file_info.filename = "images/test.png"
    mock_file_info.is_dir.return_value = False

    # Mock the file-like object returned by zf.open()
    mock_file_obj = MagicMock()
    mock_file_obj.read.return_value = b"fake-image-bytes"

    mock_zf = MagicMock()
    mock_zf.infolist.return_value = [mock_file_info]
    mock_zf.open.return_value.__enter__.return_value = mock_file_obj
    mock_zip_file.return_value.__enter__.return_value = mock_zf

    mock_exif = MagicMock()

    def mock_get_ifd(ifd_id):
        if ifd_id == 34665:  # IFD.Exif
            return {
                36867: "invalid-date-format"
            }  # Should trigger ValueError and fallback to None
        raise KeyError()  # No GPS info or other IFDs

    mock_exif.get_ifd.side_effect = mock_get_ifd

    mock_img = MagicMock()
    mock_img.getexif.return_value = mock_exif
    mock_img.__enter__.return_value = mock_img
    mock_image_open.return_value = mock_img

    results = get_image_metadata_from_zip("dummy.zip")

    assert len(results) == 1
    assert results[0]["path"] == "images/test.png"
    assert results[0]["date_created"] is None
    assert results[0]["latitude"] is None
    assert results[0]["longitude"] is None


@patch("zipfile.ZipFile")
def test_skip_non_image_files(mock_zip_file):
    """Test that non-image files or directories are correctly ignored."""
    txt_file = MagicMock()
    txt_file.filename = "notes.txt"
    txt_file.is_dir.return_value = False

    dir_file = MagicMock()
    dir_file.filename = "subfolder/"
    dir_file.is_dir.return_value = True

    mock_zf = MagicMock()
    mock_zf.infolist.return_value = [txt_file, dir_file]
    mock_zip_file.return_value.__enter__.return_value = mock_zf

    results = get_image_metadata_from_zip("dummy.zip")
    assert results == []
