import ee
import shapely


def format_date(season: str, year: int) -> list[str, str]:
    sdict = {
        "Q1": [f"{year}-3-1", f"{year}-5-31"],
        "Q2": [f"{year}-6-1", f"{year}-8-31"],
        "Q3": [f"{year}-9-1", f"{year}-11-30"],
        "Q4": [f"{year}-12-1", f"{year + 1}-2-29"],
        "Qall": [f"{year}-1-1", f"{year}-12-31"],
    }

    return sdict[season]


def bbox_to_ee(bbox: shapely.Polygon) -> ee.Geometry.Polygon:
    return ee.Geometry.Polygon([t for t in zip(*bbox.exterior.coords.xy)])


def get_hash(xmin: float, ymin: float, xmax: float, ymax: float) -> str:
    return str(hash((xmin, ymin, xmax, ymax)))[:7]