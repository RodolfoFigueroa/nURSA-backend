import ee
import os
import rasterio.features  # pylint: disable=unused-import
import shapely

import geopandas as gpd
import numpy as np
import rasterio as rio

from affine import Affine
from rasterio.crs import CRS  # pylint: disable=no-name-in-module


def dilate_binary_array(
    arr: np.ndarray, *, transform: Affine, crs: CRS, buffer_size: float
) -> np.ndarray:
    """Dilates a georeferenced binary array.

    Parameters
    ----------
    arr: np.ndarray
        Array to dilate.

    transform: affine.Affine
        Geographic transform of the original raster.

    crs: rasterio.crs.CRS
        Crs of the original raster.

    buffer_size: float
        Buffer size (in meters) to dilate the array.


    Returns
    -------
    np.ndarray
        Dilated array.
    """
    shapes = [
        shapely.geometry.shape(s[0])
        for s in rio.features.shapes(arr.astype(np.uint8), transform=transform)
        if s[1] == 1
    ]
    df = (
        gpd.GeoDataFrame(geometry=shapes, crs=crs)
        .to_crs("ESRI:54009")
        .assign(geometry=lambda df: df.geometry.buffer(buffer_size, resolution=32))
        .to_crs(crs)
    )
    burnt = rio.features.rasterize(
        df["geometry"].to_numpy().tolist(), out_shape=arr.shape, transform=transform
    )
    return burnt


def get_masks(
    wc_arr: np.ndarray, *, transform: Affine, crs: CRS
) -> dict[str, np.ndarray]:
    """Calculates urban, rural and unwanted masks from a WorldCover image.

    Parameters
    ----------
    wc_arr: np.ndarray
        Data extracted from WorldCover raster.

    Returns
    -------
    dict[str, np.ndarray]:
        A dictionary with values corresponding to the resultant masks. The keys are as follow:
            - urban: Urban mask. All pixels with a value of 1 are urban.
            - rural: Rural mask. All pixels with a value of 1 are rural.
            - unwanted: Unwanted mask. All pixels with a value of 0 are not valid and shouldn't be used.
    """
    urban_mask = wc_arr == 50
    rural_mask = np.bitwise_not(
        dilate_binary_array(urban_mask, transform=transform, crs=crs, buffer_size=500)
    )

    snow_mask = wc_arr != 70
    water_mask = wc_arr != 80
    unwanted_mask = np.bitwise_and(snow_mask, water_mask)
    rural_mask = np.bitwise_and(rural_mask, unwanted_mask)

    return {"urban": urban_mask, "rural": rural_mask, "unwanted": unwanted_mask}


def get_world_cover(bbox: ee.Geometry) -> ee.Image:
    lc_cover = ee.ImageCollection("ESA/WorldCover/v200").mode().clip(bbox)
    return lc_cover


def load_cover_and_masks(wc_path: os.PathLike) -> dict[str, np.ndarray]:
    with rio.open(wc_path) as ds:
        data = ds.read(1)
        crs = ds.crs
        transform = ds.transform

    masks = get_masks(data, transform=transform, crs=crs)
    masks["cover"] = data
    return masks


# def get_temps(lst: ee.Image, masks: dict[str, ee.Image]) -> dict[str, dict[str, float]]:
#     t_dict = {}

#     reducer = ee.Reducer.mean().combine(
#         ee.Reducer.stdDev(),
#         sharedInputs=True,
#     )
#     for nmask in ["total", "rural", "urban"]:
#         if nmask == "total":
#             lst_masked = lst
#         else:
#             lst_masked = lst.updateMask(masks[nmask])

#         res = lst_masked.reduceRegion(reducer, scale=100).getInfo()

#         t_dict[nmask] = dict(
#             mean=res["ST_B10_mean"],
#             std=res["ST_B10_stdDev"],
#         )

#     urban_mean = t_dict["urban"]["mean"]
#     rural_mean = t_dict["rural"]["mean"]

#     if abs(rural_mean - urban_mean) < 0.5 or rural_mean > urban_mean:
#         lst_masked = lst.updateMask(masks["urban"])
#         res = lst_masked.reduceRegion(
#             ee.Reducer.percentile([5]), bestEffort=False, scale=100
#         ).getInfo()
#         t_dict["rural_old"] = {}
#         t_dict["rural_old"]["mean"] = rural_mean
#         t_dict["rural"]["mean"] = res["ST_B10"]

#     return t_dict
