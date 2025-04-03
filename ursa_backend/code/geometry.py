import shapely

import geopandas as gpd
import numpy as np
import rasterio as rio

from shapely import Geometry
from typing import Callable, Sequence


def generate_circles(
    center: tuple[float, float], circle_radius: float, max_radius: float
) -> tuple[np.ndarray, list[shapely.geometry.Polygon]]:
    """Generates a list of circles with increasing radius.

    Parameters
    ----------
    center: tuple[float, float]
        Center of the circles.

    circle_radius: float
        Radius of the circles.

    max_radius: float
        Maximum radius of the circles.

    Returns
    -------
    list[shapely.geometry.Polygon]
        List of circles.
    """
    radii = np.arange(circle_radius, max_radius + circle_radius, circle_radius)
    circles = [
        shapely.geometry.Point(center).buffer(radius, resolution=32) for radius in radii
    ]
    return radii, circles


def generate_rings(
    circles: list[shapely.geometry.Polygon],
) -> list[shapely.geometry.Polygon]:
    """Generates a list of rings from a list of circles.

    Parameters
    ----------
    circles: list[shapely.geometry.Polygon]
        List of circles.

    Returns
    -------
    list[shapely.geometry.Polygon]
        List of rings.
    """
    return [circles[i].difference(circles[i - 1]) for i in range(1, len(circles))]


def overlay_geometries(
    ds: rio.DatasetBase, geometries: Sequence[Geometry], func: Callable
) -> list[float]:
    temps = []
    for geom in geometries:
        masked, _ = rio.mask.mask(ds, [geom], crop=True, nodata=-99999)
        masked[masked == -99999] = np.nan
        temps.append(func(masked))
    return temps
