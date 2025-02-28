import ee


def fmask(image: ee.Image) -> ee.Image:
    """Calculates the cloud mask for a Landsat image.

    Parameters
    ----------
    image : ee.Image
        The image to analyze. Must have valid cloud bands.

    Returns
    -------
    ee.Image
        The resultant cloud mask image with binary values. A 0 indicates that a cloud was present.
    """

    qa = image.select("QA_PIXEL")

    dilated_cloud_bit = 1
    cloud_bit = 3
    cloud_shadow_bit = 4

    mask = qa.bitwiseAnd(1 << dilated_cloud_bit).eq(0)
    mask = mask.And(qa.bitwiseAnd(1 << cloud_bit).eq(0))
    mask = mask.And(qa.bitwiseAnd(1 << cloud_shadow_bit).eq(0))

    return image.updateMask(mask)


def get_lst(bbox_ee: ee.Geometry.Polygon, start_date: str, end_date: str) -> ee.Image:
    """Calculates the average Land Surface Temperature for a given region and date range.

    Parameters
    ----------
    bbox_ee: ee.Geometry.Polygon
        Region of interest.

    start_date: str
        Start date.

    end_date: str
        End date.

    Returns
    -------
    ee.Image
        LST image.
    """

    filtered: ee.ImageCollection = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start_date, end_date)
        .filterBounds(bbox_ee)
    )

    if filtered.size().getInfo() == 0:
        raise ValueError("No measurements for given date and location found.")

    return (
        filtered.map(fmask)
        .select("ST_B10")
        .mean()
        .multiply(0.00341802)
        .add(149 - 273.15)
        .clip(bbox_ee)
    )
