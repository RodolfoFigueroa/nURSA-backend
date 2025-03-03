from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path
from typing import Annotated
from ursa_backend.dependencies import lst_dependency, world_cover_dependency
from ursa_backend.code.common import raster_to_rgb
from ursa_backend.code.suhi import calculate_rural_temperature


router = APIRouter(prefix="/suhi")


@router.post("/maps/continuous")
def lst_endpoint(temp_path_map: Annotated[dict[str, Path], Depends(lst_dependency)]):
    data, width, height, bounds = raster_to_rgb(temp_path_map["cont"])
    return JSONResponse(dict(data=data, width=width, height=height, bounds=bounds))


@router.post("/maps/categorical")
def lst_cat_endpoint(
    temp_path_map: Annotated[dict[str, Path], Depends(lst_dependency)]
):
    data, width, height, bounds = raster_to_rgb(temp_path_map["cat"], discrete=True)
    return JSONResponse(dict(data=data, width=width, height=height, bounds=bounds))


@router.post("/data/rural")
def rural_temp_endpoint(
    temp_path_map: Annotated[dict[str, Path], Depends(lst_dependency)],
    world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
):
    return JSONResponse(
        dict(value=calculate_rural_temperature(temp_path_map["cont"], world_cover_path))
    )


# @router.post("/charts/temp_cat")
# async def temp_cat_chart_endpoint(raster_path: Annotated[Path, Depends(lst_dependency)]):
