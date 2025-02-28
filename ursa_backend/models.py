import ee

from pydantic import BaseModel
from ursa_backend.code.common import bounds_to_ee, get_hash


class GeographicRequestModel(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def bounds_to_ee(self) -> ee.Geometry:
        return bounds_to_ee(self.xmin, self.ymin, self.xmax, self.ymax)

    def get_hash(self) -> str:
        return get_hash(self.xmin, self.ymin, self.xmax, self.ymax)


class GeoTemporalRequestModel(GeographicRequestModel):
    year: int
    season: str
