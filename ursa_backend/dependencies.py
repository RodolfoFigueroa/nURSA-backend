from pathlib import Path
from ursa_backend.code.common import format_date, load_or_download_image
from ursa_backend.code.constants import LST_NODATA
from ursa_backend.code.suhi import get_lst
from ursa_backend.code.world_cover import get_world_cover
from ursa_backend.models import GeographicRequestModel, GeoTemporalRequestModel


async def lst_dependency(request: GeoTemporalRequestModel) -> Path:
    box_ee = request.bounds_to_ee()
    start_date, end_date = format_date(request.season, request.year)
    lst = get_lst(box_ee, start_date, end_date)

    raster_path = Path(
        f"./data/{request.get_hash()}/suhi/{request.year}_{request.season}.tif"
    )
    load_or_download_image(lst, raster_path, box_ee, nodata=LST_NODATA)
    return raster_path


async def world_cover_dependency(request: GeographicRequestModel) -> Path:
    box_ee = request.bounds_to_ee()
    cover = get_world_cover(box_ee)

    raster_path = Path(f"./data/{request.get_hash()}/cover.tif")
    load_or_download_image(cover, raster_path, box_ee, nodata=0)
    return raster_path
