import ee
import os
import rasterio.features  # pylint: disable=unused-import
import shapely

import geopandas as gpd
import numpy as np
import rasterio as rio

from affine import Affine
from rasterio.crs import CRS  # pylint: disable=no-name-in-module
from rasterio.windows import Window
from typing import Generator, TypedDict


class MaskMap(TypedDict):
    urban: np.ndarray
    rural: np.ndarray
    valid: np.ndarray
    cover: np.ndarray | None = None


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
    ).astype(bool)
    return burnt


# pylint: disable=possibly-used-before-assignment,undefined-variable
def get_masks(
    wc_arr: np.ndarray,
    *,
    transform: Affine,
    crs: CRS,
    urban: bool = True,
    rural: bool = True,
    valid: bool = True,
) -> MaskMap:
    """Calculates urban, rural and valid masks from a WorldCover image.

    Parameters
    ----------
    wc_arr: np.ndarray
        Data extracted from WorldCover raster.

    urban: bool
        Whether to return the urban mask.

    rural: bool
        Whether to return the urban mask. If `rural=True`, this mask is calculated regardless.

    valid: bool
        Whether to return the valid mask. If `rural=True`, this mask is calculated regardless.

    Returns
    -------
    dict[str, np.ndarray]:
        A dictionary with values corresponding to the resultant masks. The keys are as follow:
            - urban: Urban mask. All pixels with a value of 1 are urban.
            - rural: Rural mask. All pixels with a value of 1 are rural.
            - valid: Valid mask. All pixels with a value of 0 are not valid for temperature calculations and shouldn't be used.
    """
    if urban or rural:
        urban_mask = wc_arr == 50

    if rural or valid:
        snow_mask = wc_arr != 70
        water_mask = wc_arr != 80
        valid_mask = np.bitwise_and(snow_mask, water_mask)

    if rural:
        rural_mask = np.bitwise_not(
            dilate_binary_array(
                urban_mask, transform=transform, crs=crs, buffer_size=500
            )
        )

        if not urban:
            del urban_mask

        rural_mask = np.bitwise_and(rural_mask, valid_mask)

        if not valid:
            del valid_mask

    return MaskMap(
        urban=urban_mask if urban else None,
        rural=rural_mask if rural else None,
        valid=valid_mask if valid else None,
    )


def get_world_cover(bbox: ee.Geometry) -> ee.Image:
    lc_cover = ee.ImageCollection("ESA/WorldCover/v200").mode().clip(bbox)
    return lc_cover


def load_cover_and_masks(
    wc_path: os.PathLike,
    *,
    urban: bool = False,
    rural: bool = False,
    valid: bool = False,
) -> MaskMap:
    with rio.open(wc_path) as ds:
        data = ds.read(1)
        crs = ds.crs
        transform = ds.transform

    masks = get_masks(
        data, transform=transform, crs=crs, urban=urban, rural=rural, valid=valid
    )
    masks["cover"] = data
    return masks


def load_cover_and_masks_generator(
    wc_path: os.PathLike,
    *,
    urban: bool = False,
    rural: bool = False,
    valid: bool = False,
) -> Generator[tuple[Window, MaskMap], None, None]:
    with rio.open(wc_path) as ds:
        for _, window in ds.block_windows(1):
            data = ds.read(1, window=window)
            crs = ds.crs
            transform = ds.transform

            masks = get_masks(
                data,
                transform=transform,
                crs=crs,
                urban=urban,
                rural=rural,
                valid=valid,
            )
            masks["cover"] = data
            yield (window, masks)
