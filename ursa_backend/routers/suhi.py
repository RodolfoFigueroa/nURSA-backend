import geemap
import shapely

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pathlib import Path
from ursa_backend.code.common import bbox_to_ee, format_date
from ursa_backend.code.suhi import get_lst, raster_to_rgb
from ursa_backend.models import LSTRequestModel


router = APIRouter(prefix="/suhi")

@router.post("/plot")
async def fetch_lst(request: LSTRequestModel):
    box = shapely.box(
        xmin=request.xmin,
        ymin=request.ymin,
        xmax=request.xmax,
        ymax=request.ymax
    )
    box_ee = bbox_to_ee(box)

    start_date, end_date = format_date(request.season, request.year)
    lst = get_lst(box_ee, start_date, end_date)

    h = request.get_hash()
    raster_path = Path(f"./data/{h}/{request.year}_{request.season}.tif")
    raster_path.parent.mkdir(exist_ok=True, parents=True)

    if not raster_path.exists():
        geemap.download_ee_image(lst, raster_path, scale=100, crs="EPSG:4326", region=box_ee)
    

    image_data = raster_to_rgb(raster_path, vmin=22, vmax=45)
    image_data["xmin"] = request.xmin
    image_data["xmax"] = request.xmax
    image_data["ymin"] = request.ymin
    image_data["ymax"] = request.ymax

    return JSONResponse(image_data)