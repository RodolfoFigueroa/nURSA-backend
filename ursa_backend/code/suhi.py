import ee
import os

import matplotlib.colors as mcol
import numpy as np
import rasterio as rio

from ursa_backend.code.constants import LST_CAT_NODATA
from ursa_backend.code.world_cover import load_cover_and_masks


def fmask(image: ee.Image) -> ee.Image:
    """Calculates the cloud mask for a Landsat image.

    Parameters
    ----------
    image : ee.Image
        The image to analyze. Must have valid cloud bands.

    Returns
    -------
    ee.Image
        The resultant cloud mask image with binary values. A 0 indicates that a cloud was present.
    """

    qa = image.select("QA_PIXEL")

    dilated_cloud_bit = 1
    cloud_bit = 3
    cloud_shadow_bit = 4

    mask = qa.bitwiseAnd(1 << dilated_cloud_bit).eq(0)
    mask = mask.And(qa.bitwiseAnd(1 << cloud_bit).eq(0))
    mask = mask.And(qa.bitwiseAnd(1 << cloud_shadow_bit).eq(0))

    return image.updateMask(mask)


def get_lst(bbox_ee: ee.Geometry.Polygon, start_date: str, end_date: str) -> ee.Image:
    """Calculates the average Land Surface Temperature for a given region and date range.

    Parameters
    ----------
    bbox_ee: ee.Geometry.Polygon
        Region of interest.

    start_date: str
        Start date.

    end_date: str
        End date.

    Returns
    -------
    ee.Image
        LST image.
    """

    filtered: ee.ImageCollection = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start_date, end_date)
        .filterBounds(bbox_ee)
    )

    if filtered.size().getInfo() == 0:
        raise ValueError("No measurements for given date and location found.")

    return (
        filtered.map(fmask)
        .select("ST_B10")
        .mean()
        .multiply(0.00341802)
        .add(149 - 273.15)
        .clip(bbox_ee)
    )


def get_raster_stats(data: np.ndarray) -> tuple[float, float]:
    data_notna = data[np.bitwise_not(np.isnan(data))]
    mu = np.mean(data_notna)
    sigma = np.std(data_notna)
    return mu, sigma


def discretize_array(
    arr: np.ndarray, n_pairs: int, *, nodata: float
) -> np.ndarray[int]:
    mu, sigma = get_raster_stats(arr)

    bounds = []
    labels = []
    for i in range(n_pairs):
        scale = i + 0.5
        bounds.append(mu + sigma * scale)
        bounds.append(mu - sigma * scale)
        labels.append(i + 1)
        labels.append(-(i + 1))

    bounds = sorted(bounds)

    # Do not change order
    labels.append(0)
    labels = sorted(labels)
    labels.append(nodata)

    nan_color = 2 * n_pairs
    colors = (
        [-1]  # below
        + list(range(1, (n_pairs - 1) * 2 + 2))
        + [2 * n_pairs + 1]  # above
        + [nan_color]  # nodata
    )

    norm = mcol.BoundaryNorm(bounds, 2 * n_pairs + 1, extend="both")
    arr_normalized = norm(arr)

    out = np.zeros_like(arr, dtype=np.int8)
    for label, color in zip(labels, colors):
        out += (arr_normalized == color) * label

    return out


def generate_categorical_raster(
    cont_raster_path: os.PathLike, cat_raster_path: os.PathLike
) -> None:
    n_color_pairs = 3

    with rio.open(cont_raster_path) as ds:
        data = np.squeeze(ds.read(1))
        profile = ds.profile
    data[data == profile["nodata"]] = np.nan

    data_cat = discretize_array(data, n_color_pairs, nodata=LST_CAT_NODATA)

    profile.update(nodata=LST_CAT_NODATA, dtype="int8")
    with rio.open(cat_raster_path, "w", **profile) as ds:
        ds.write(data_cat, 1)


def calculate_rural_temperature(
    cont_raster_path: os.PathLike, wc_raster_path: os.PathLike
) -> float:
    data_map = load_cover_and_masks(wc_raster_path)
    rural_mask = data_map["rural"]

    with rio.open(cont_raster_path) as ds:
        temp = ds.read(1)

    masked = np.where(rural_mask, temp, np.nan)
    return np.nanmean(masked)
