import ee
import os
import rasterio.mask  # pylint: disable=unused-import
import shapely

import geopandas as gpd
import matplotlib.colors as mcol
import numpy as np
import rasterio as rio

from affine import Affine
from rasterio.io import MemoryFile
from scipy.interpolate import make_smoothing_spline
from typing import Sequence
from ursa_backend.code.constants import LST_CAT_NODATA
from ursa_backend.code.fs import raster_generator
from ursa_backend.code.geometry import (
    generate_circles,
    generate_rings,
    overlay_geometries,
)
from ursa_backend.code.world_cover import load_cover_and_masks
from ursa_backend.models import RasterResponseModel


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


def generate_suhi_raster(
    temp: np.ndarray, rural_mask: np.ndarray, urban_mask: np.ndarray
) -> np.ndarray:
    rural_pixels = temp[rural_mask]
    rural_pixels = rural_pixels[~np.isnan(rural_pixels)]

    urban_pixels = temp[urban_mask]
    urban_pixels = urban_pixels[~np.isnan(urban_pixels)]

    rural_temp = np.mean(rural_pixels)
    urban_temp = np.mean(urban_pixels)

    if urban_temp >= rural_temp:
        offset_temp = rural_temp
    else:
        offset_temp = np.percentile(urban_pixels, 5)

    return temp - offset_temp


def generate_mean_suhi_raster(
    raster_paths: Sequence[os.PathLike], world_cover_path: os.PathLike
) -> RasterResponseModel:
    mask_map = load_cover_and_masks(world_cover_path, rural=True, urban=True)

    mean_suhi_raster = np.zeros(mask_map["rural"].shape, dtype=float)
    counter = 0
    crs, transform = None, None
    for elem in raster_generator(raster_paths, nan_thresh=0.15):
        if elem is None:
            continue

        arr = np.array(elem.data)
        suhi_raster = generate_suhi_raster(arr, mask_map["rural"], mask_map["urban"])
        suhi_raster[np.isnan(suhi_raster)] = 0
        mean_suhi_raster += suhi_raster
        counter += 1

        if crs is not None:
            assert crs == elem.crs

        if transform is not None:
            assert transform == elem.transform

        crs = elem.crs
        transform = elem.transform

    return RasterResponseModel(
        data=mean_suhi_raster / counter, crs=crs, transform=transform
    )


def get_rural_temps(
    raster_paths: Sequence[os.PathLike], world_cover_path: os.PathLike
) -> list[float]:
    rural_mask = load_cover_and_masks(world_cover_path, rural=True)["rural"]
    rural_temps = []
    for temp in raster_generator(raster_paths, nan_thresh=0.10):
        if temp is None:
            rural_temps.append(np.nan)
        else:
            data = np.array(temp.data)
            rural_temps.append(np.nanmean(data[rural_mask]))
    return rural_temps


def get_radial_cdf(
    raster_response: RasterResponseModel, center: tuple[float, float]
) -> list[float]:
    arr = np.array(raster_response.data)
    center_mollweide = (
        gpd.GeoSeries([shapely.Point(*center)], crs="EPSG:4326")
        .to_crs("ESRI:54009")
        .item()
    )

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=arr.shape[0],
            width=arr.shape[1],
            count=1,
            dtype=float,
            crs=raster_response.crs,
            transform=Affine(*raster_response.transform),
        ) as ds:
            ds.write(arr, 1)
            bbox = shapely.box(*ds.bounds)
            bbox_mollweide = (
                gpd.GeoSeries([bbox], crs="EPSG:4326").to_crs("ESRI:54009").item()
            )
            xmin, ymin, xmax, ymax = bbox_mollweide.bounds

            max_radius = np.sqrt((xmin - xmax) ** 2 + (ymin - ymax) ** 2)

            radii, circles_mollweide = generate_circles(
                center_mollweide, 250, max_radius
            )

            circle_intersection_area_frac = np.array(
                [
                    circle.intersection(bbox_mollweide).area / bbox_mollweide.area
                    for circle in circles_mollweide
                ]
            )
            first_full_circle_idx = np.argmax(
                np.isclose(circle_intersection_area_frac, 1.0)
            )
            circles_mollweide = circles_mollweide[: first_full_circle_idx + 1]
            radii = radii[:first_full_circle_idx]

            rings_mollweide = generate_rings(circles_mollweide)
            rings_latlon = gpd.GeoSeries(rings_mollweide, crs="ESRI:54009").to_crs(
                "EPSG:4326"
            )

            res = overlay_geometries(ds, rings_latlon.values, np.nanmean)
            print(radii, res)
            return radii, res


def get_radial_pdf(radii: list[float], cdf: list[float]) -> list[float]:
    spline = make_smoothing_spline(radii, cdf, lam=0.05)
    pdf = spline.derivative()(radii)
    return radii, pdf
