import ee

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ursa_backend.routers import suhi

ee.Initialize()

app = FastAPI()
app.include_router(suhi.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "test"}
