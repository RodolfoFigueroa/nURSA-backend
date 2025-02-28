import ee


def get_masks(img: ee.Image) -> dict[str, ee.Image]:
    """Calculates urban, rural and unwanted masks from a WorldCover image.

    Parameters
    ----------
    img: ee.Image
        WorldCover image to use.

    Returns
    -------
    dict[str, ee.Image]:
        A dictionary with three keys:
            - urban: Urban mask. All pixels with a value of 1 are urban.
            - rural: Rural mask. All pixels with a value of 1 are rural.
            - unwanted: Unwanted mask. All pixels with a value of 0 are unwanted and shouldn't be used.
    """
    urban_mask = img.eq(50)

    rural_mask = urban_mask.focalMax(radius=500, units="meters", kernelType="circle")
    rural_mask = rural_mask.bitwiseNot()

    snow_mask = img.neq(70)
    water_mask = img.neq(80)
    unwanted_mask = snow_mask.bitwiseAnd(water_mask)
    rural_mask = rural_mask.bitwiseAnd(unwanted_mask)

    return {"urban": urban_mask, "rural": rural_mask, "unwanted": unwanted_mask}


def get_world_cover(bbox: ee.Geometry.Polygon) -> ee.Image:
    return ee.ImageCollection("ESA/WorldCover/v200").mode().clip(bbox)


def get_cover_and_masks(bbox: ee.Geometry.Polygon) -> tuple[ee.Image, dict]:
    lc_cover = get_world_cover(bbox)
    masks = get_masks(lc_cover)
    lc_cover = lc_cover.updateMask(masks["unwanted"])

    return lc_cover, masks


def get_temps(lst: ee.Image, masks: dict[str, ee.Image]) -> dict[str, dict[str, float]]:
    t_dict = {}

    reducer = ee.Reducer.mean().combine(
        ee.Reducer.stdDev(),
        sharedInputs=True,
    )
    for nmask in ["total", "rural", "urban"]:
        if nmask == "total":
            lst_masked = lst
        else:
            lst_masked = lst.updateMask(masks[nmask])

        res = lst_masked.reduceRegion(reducer, scale=100).getInfo()

        t_dict[nmask] = dict(
            mean=res["ST_B10_mean"],
            std=res["ST_B10_stdDev"],
        )

    urban_mean = t_dict["urban"]["mean"]
    rural_mean = t_dict["rural"]["mean"]

    if abs(rural_mean - urban_mean) < 0.5 or rural_mean > urban_mean:
        lst_masked = lst.updateMask(masks["urban"])
        res = lst_masked.reduceRegion(
            ee.Reducer.percentile([5]), bestEffort=False, scale=100
        ).getInfo()
        t_dict["rural_old"] = {}
        t_dict["rural_old"]["mean"] = rural_mean
        t_dict["rural"]["mean"] = res["ST_B10"]

    return t_dict
