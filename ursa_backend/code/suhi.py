import ee

import matplotlib as mpl
import matplotlib.colors as mcol
import numpy as np
import rasterio as rio

from pathlib import Path


def fmask(image):
    qa = image.select("QA_PIXEL")

    dilated_cloud_bit = 1
    cloud_bit = 3
    cloud_shadow_bit = 4

    mask = qa.bitwiseAnd(1 << dilated_cloud_bit).eq(0)
    mask = mask.And(qa.bitwiseAnd(1 << cloud_bit).eq(0))
    mask = mask.And(qa.bitwiseAnd(1 << cloud_shadow_bit).eq(0))

    return image.updateMask(mask)


def prep_img(img):
    orig = img
    img = fmask(img)
    img = img.select(["ST_B10"])
    img = ee.Image(img.copyProperties(orig, orig.propertyNames()))
    img = img.set({"epsg": orig.projection().crs()})
    return img  # .resample("bicubic")


def get_lst(bbox_ee: ee.Geometry.Polygon, start_date: str, end_date: str) -> ee.Image:
    filtered: ee.ImageCollection = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start_date, end_date)
        .filterBounds(bbox_ee)
    )

    if filtered.size().getInfo() == 0:
        raise ValueError("No measurements for given date and location found.")

    return (
        filtered
        .map(fmask)
        .select("ST_B10")
        .mean()
        .multiply(0.00341802)
        .add(149 - 273.15)
        .clip(bbox_ee)
    )


def raster_to_rgb(raster_path: Path, *, vmin: float, vmax: float):
    with rio.open(raster_path) as ds:
        data = ds.read(1)
        width = ds.width
        height = ds.height

    data[data == -np.inf] = np.nan
    data[data == np.inf] = np.nan

    norm = mcol.Normalize(vmin=vmin, vmax=vmax)
    cmap = mpl.colormaps["RdBu"].reversed()

    rgb = cmap(norm(data))
    colors = np.round(rgb * 255).astype(np.uint8).flatten().tolist()

    return dict(
        data=colors,
        width=width, 
        height=height
    )