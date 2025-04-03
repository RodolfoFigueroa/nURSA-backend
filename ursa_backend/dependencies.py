from fastapi import Query
from pathlib import Path
from typing import Annotated
from ursa_backend.code.common import load_or_download_image
from ursa_backend.code.dates import get_date_range, season_to_months
from ursa_backend.code.constants import LST_NODATA
from ursa_backend.code.suhi import get_lst
from ursa_backend.code.world_cover import get_world_cover
from ursa_backend.models import GeographicRequestModel, GeoTemporalRequestModel


def lst_dependency(
    request: Annotated[GeoTemporalRequestModel, Query()]
) -> dict[str, Path]:
    box_ee = request.bounds_to_ee()

    out = []
    for month in season_to_months(request.season):
        cont_raster_path = Path(
            f"./data/{request.get_hash()}/suhi/{request.year}_{str(month).rjust(2, '0')}.tif"
        )

        if not cont_raster_path.exists():
            start_date, end_date = get_date_range(month, request.year)
            lst = get_lst(box_ee, start_date, end_date)
            load_or_download_image(lst, cont_raster_path, box_ee, nodata=LST_NODATA)

        out.append(cont_raster_path)

    return out


def world_cover_dependency(request: Annotated[GeographicRequestModel, Query()]) -> Path:
    box_ee = request.bounds_to_ee()
    img = get_world_cover(box_ee)
    path = Path(f"./data/{request.get_hash()}/cover.tif")
    load_or_download_image(img, path, box_ee, nodata=0)

    return path
