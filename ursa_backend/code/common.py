import ee
import geemap
import os
import shapely

import matplotlib as mpl
import matplotlib.colors as mcol
import numpy as np
import rasterio as rio

from typing import Optional


def format_date(season: str, year: int) -> list[str, str]:
    """Formats a year and season string in a way that's interpretable by Earth Engine's filters.

    Parameters
    ----------
    season: str
        Season of the year to analyze. Possible values are Q1 (spring), Q2 (summer), Q3 (fall), Q4 (winter) and Qall (entire year).

    year: int
        Year to analyze.

    Returns
    -------
    str
        Date string in '{year}-{month}-{day}' format.
    """
    sdict = {
        "Q1": [f"{year}-3-1", f"{year}-5-31"],
        "Q2": [f"{year}-6-1", f"{year}-8-31"],
        "Q3": [f"{year}-9-1", f"{year}-11-30"],
        "Q4": [f"{year}-12-1", f"{year + 1}-2-29"],
        "Qall": [f"{year}-1-1", f"{year}-12-31"],
    }

    return sdict[season]


def bbox_to_ee(bbox: shapely.Polygon) -> ee.Geometry.Polygon:
    """Converts a shapely polygon to an EarthEngine geometry.

    Parameters
    ----------
    bbox: shapely.Polygon
        Polygon to convert.

    Returns
    -------
    ee.Geometry.Polygon
        Equivalent EarthEngine geometry.
    """
    return ee.Geometry.Polygon([t for t in zip(*bbox.exterior.coords.xy)])


def bounds_to_ee(xmin: float, ymin: float, xmax: float, ymax: float) -> ee.Geometry:
    """Converts a list of bounds to an EarthEngine geometry.

    Parameters
    ----------
    xmin: float
        Minimum x coordinate.

    ymin: float
        Minimum y coordinate.

    xmax: float
        Maximum x coordinate.

    ymax: float
        Maximum y coordinate.


    Returns
    -------
    ee.Geometry.Polygon
        Equivalent EarthEngine geometry.
    """
    return bbox_to_ee(shapely.box(xmin, ymin, xmax, ymax))


def get_hash(xmin: float, ymin: float, xmax: float, ymax: float) -> str:
    """Hashes a bounding box given by its extent.

    Parameters
    ----------
    xmin: float
        Minimum x coordinate.

    ymin: float
        Minimum y coordinate.

    xmax: float
        Maximum x coordinate.

    ymax: float
        Maximum y coordinate.

    Returns
    -------
    str
        Hash of the bounding box.
    """
    return str(hash((xmin, ymin, xmax, ymax)))[:7]


def load_or_download_image(
    img: ee.Image,
    raster_path: os.PathLike,
    bbox: ee.Geometry,
    nodata: Optional[float] = None,
) -> None:
    if raster_path.exists():
        return

    raster_path.parent.mkdir(exist_ok=True, parents=True)

    if nodata is None:
        temp_raster_path = raster_path
    else:
        temp_raster_path = raster_path.with_name(f"{raster_path.stem}_temp.tif")

    geemap.download_ee_image(
        img,
        temp_raster_path,
        scale=100,
        crs="EPSG:4326",
        region=bbox,
        unmask_value=nodata,
    )

    if nodata is None:
        return

    with rio.open(temp_raster_path) as ds:
        data = ds.read(1)
        profile = ds.profile

    data[data == profile["nodata"]] = nodata
    data[np.isnan(data)] = nodata
    data = data.squeeze()

    profile.update(nodata=nodata, compress="lzw")

    with rio.open(raster_path, "w", **profile) as ds:
        ds.write(data, 1)

    os.remove(temp_raster_path)


def raster_to_rgb(
    raster_path: os.PathLike, *, discrete: bool = False
) -> tuple[list, int, int, list[float]]:
    """Converts a raster in the filesystem to an RGBA array.

    Parameters
    ----------
    raster_path: os.PathLike
        Path to the raster.

    vmin: float
        Color scale minimum.

    vmax: float
        Color scale maximum.

    Returns
    -------
    colors: list[int]
        Flattened RGBA array.

    width: int
        Width of the array.

    height: int
        Height of the array.
    """

    with rio.open(raster_path) as ds:
        data = ds.read(1)
        width = ds.width
        height = ds.height
        nodata = ds.nodata

    data = data.astype(float)
    data[data == nodata] = np.nan

    data_notna = data[np.bitwise_not(np.isnan(data))]

    cmap = mpl.colormaps["RdBu"].reversed()

    if discrete:
        vmin = -3
        vmax = 3
        bounds = []
    else:
        vmin = np.quantile(data_notna, 0.05)
        vmax = np.quantile(data_notna, 0.95)
        bounds = [vmin, vmax]

    norm = mcol.Normalize(vmin=vmin, vmax=vmax)
    rgb = cmap(norm(data))
    colors = np.round(rgb * 255).astype(np.uint8).flatten().tolist()

    return colors, width, height, bounds
