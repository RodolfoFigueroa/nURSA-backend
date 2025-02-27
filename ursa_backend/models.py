from pydantic import BaseModel


class GeographicModel(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def get_hash(self):
        return str(hash((self.xmin, self.ymin, self.xmax, self.ymax)))[:7]
    

class LSTRequestModel(GeographicModel):
    year: int
    season: str