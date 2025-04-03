import numpy as np

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, ORJSONResponse
from pathlib import Path
from typing import Annotated
from ursa_backend.code.common import raster_to_rgb
from ursa_backend.code.suhi import (
    generate_mean_suhi_raster,
    get_rural_temps,
    get_radial_cdf,
    get_radial_pdf,
)
from ursa_backend.dependencies import lst_dependency, world_cover_dependency
from ursa_backend.models import CenterRequestModel


router = APIRouter(prefix="/suhi")


@router.get("/maps/continuous")
def lst_endpoint(
    monthly_temp_paths: Annotated[list[Path], Depends(lst_dependency)],
    world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
):
    mean_suhi_raster = generate_mean_suhi_raster(monthly_temp_paths, world_cover_path)
    arr = np.array(mean_suhi_raster.data)
    data, bounds = raster_to_rgb(arr, kind="continuous_centered")

    return JSONResponse(
        dict(data=data, width=arr.shape[1], height=arr.shape[0], bounds=bounds)
    )


@router.get("/raster/suhi")
def raster_suhi_endpoint(
    monthly_temp_paths: Annotated[list[Path], Depends(lst_dependency)],
    world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
):
    raster_response = generate_mean_suhi_raster(monthly_temp_paths, world_cover_path)
    arr = np.array(raster_response.data)
    return JSONResponse(
        dict(
            data=arr.flatten().tolist(),
            width=arr.shape[1],
            height=arr.shape[0],
            crs=raster_response.crs,
            transform=raster_response.transform,
        )
    )


@router.get("/data/rural")
def rural_temp_endpoint(
    monthly_temp_paths: Annotated[list[Path], Depends(lst_dependency)],
    world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
):
    rural_temps = get_rural_temps(monthly_temp_paths, world_cover_path)
    return ORJSONResponse(dict(value=rural_temps))


@router.get("/data/radial")
def radial_temp_endpoint(
    monthly_temp_paths: Annotated[list[Path], Depends(lst_dependency)],
    world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
    center: Annotated[CenterRequestModel, Query()],
):
    raster_response = generate_mean_suhi_raster(monthly_temp_paths, world_cover_path)
    radii, cdf = get_radial_cdf(raster_response, (center.x, center.y))
    # _, pdf = get_radial_pdf(radii, cdf)
    return ORJSONResponse(dict(radii=radii, cdf=cdf, pdf=[]))


# @router.post("/maps/categorical")
# def lst_cat_endpoint(
#     month_temp_paths: Annotated[list[Path], Depends(lst_dependency)]
# ):
#     for path in temp_path_list:


#     data, width, height, bounds = raster_to_rgb(temp_path_map["cat"], discrete=True)
#     return JSONResponse(dict(data=data, width=width, height=height, bounds=bounds))


# @router.post("/data/category")
# def category_temp_endpoint(
#     temp_path_map: Annotated[dict[str, Path], Depends(lst_dependency)],
#     world_cover_path: Annotated[Path, Depends(world_cover_dependency)],
# ):
#     return ORJSONResponse(calculate_cover_temperature(temp_path_map["cont"], world_cover_path))

# # @router.post("/charts/temp_cat")
# # async def temp_cat_chart_endpoint(raster_path: Annotated[Path, Depends(lst_dependency)]):
