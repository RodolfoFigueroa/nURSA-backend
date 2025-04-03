import ee
import geemap
import os
import shapely

import matplotlib as mpl
import matplotlib.colors as mcol
import numpy as np
import rasterio as rio

from shapely import Geometry
from typing import Callable, Literal, Sequence, assert_never


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
    nodata: float | None = None,
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
        scale=50,
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
    data: np.ndarray,
    *,
    nodata: float | None = None,
    kind: Literal["continuous", "discrete", "continuous_centered"],
) -> tuple[list, list[float]]:
    data = data.astype(float).copy()

    if nodata is not None:
        data[data == nodata] = np.nan

    data_notna = data[np.bitwise_not(np.isnan(data))]

    cmap = mpl.colormaps["RdBu"].reversed()

    if kind == "discrete":
        bounds = []
        norm = mcol.Normalize(vmin=-3, vmax=3)
    else:
        vmin = np.quantile(data_notna, 0.03)
        vmax = np.quantile(data_notna, 0.97)
        bounds = [vmin, vmax]

        if kind == "continuous":
            norm = mcol.Normalize(vmin=-vmin, vmax=vmax)
        elif kind == "continuous_centered":
            norm = mcol.TwoSlopeNorm(vcenter=0, vmin=vmin, vmax=vmax)
        else:
            assert_never(kind)

    rgb = cmap(norm(data))
    colors = np.round(rgb * 255).astype(np.uint8).flatten().tolist()

    return colors, bounds
