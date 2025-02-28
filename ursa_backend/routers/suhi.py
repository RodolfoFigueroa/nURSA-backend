from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Annotated
from ursa_backend.dependencies import lst_dependency
from ursa_backend.code.common import raster_to_rgb


router = APIRouter(prefix="/suhi")


@router.post("/maps/continuous")
async def lst_endpoint(raster_path: Annotated[Path, Depends(lst_dependency)]):
    data, width, height, bounds = raster_to_rgb(raster_path)
    return JSONResponse(dict(data=data, width=width, height=height, bounds=bounds))


@router.post("/maps/categorical")
async def lst_cat_endpoint(raster_path: Annotated[Path, Depends(lst_dependency)]):
    data, width, height, bounds = raster_to_rgb(raster_path, discrete=True)
    return JSONResponse(dict(data=data, width=width, height=height, bounds=bounds))


# @router.post("/charts/temp_cat")
# async def temp_cat_chart_endpoint(raster_path: Annotated[Path, Depends(lst_dependency)]):
