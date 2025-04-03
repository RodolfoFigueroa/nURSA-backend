import os

import numpy as np
import rasterio as rio

from ursa_backend.models import RasterResponseModel
from typing import Generator


def raster_generator(
    raster_paths: list[os.PathLike], nan_thresh: float | None = None
) -> Generator[RasterResponseModel | None, None, None]:
    for path in raster_paths:
        with rio.open(path) as ds:
            temp = ds.read(1)
            crs = ds.crs
            transform = ds.transform
        temp[temp == ds.nodata] = np.nan

        nan_frac = np.isnan(temp).sum() / temp.size
        if nan_thresh is not None and nan_frac > nan_thresh:
            yield None
        else:
            yield RasterResponseModel(
                data=temp, crs=str(crs), transform=list(transform)
            )
