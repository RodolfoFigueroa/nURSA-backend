from pathlib import Path
from ursa_backend.code.common import format_date, load_or_download_image
from ursa_backend.code.constants import LST_NODATA
from ursa_backend.code.suhi import get_lst, generate_categorical_raster
from ursa_backend.code.world_cover import get_world_cover
from ursa_backend.models import GeographicRequestModel, GeoTemporalRequestModel


async def lst_dependency(request: GeoTemporalRequestModel) -> dict[str, Path]:
    box_ee = request.bounds_to_ee()
    start_date, end_date = format_date(request.season, request.year)
    lst = get_lst(box_ee, start_date, end_date)

    cont_raster_path = Path(
        f"./data/{request.get_hash()}/suhi/{request.year}_{request.season}.tif"
    )
    load_or_download_image(lst, cont_raster_path, box_ee, nodata=LST_NODATA)

    cat_raster_path = cont_raster_path.with_name(f"{cont_raster_path.stem}_cat.tif")
    if not cat_raster_path.exists():
        generate_categorical_raster(cont_raster_path, cat_raster_path)

    return dict(cont=cont_raster_path, cat=cat_raster_path)


async def world_cover_dependency(request: GeographicRequestModel) -> Path:
    box_ee = request.bounds_to_ee()
    img = get_world_cover(box_ee)
    path = Path(f"./data/{request.get_hash()}/cover.tif")
    load_or_download_image(img, path, box_ee, nodata=0)

    return path
