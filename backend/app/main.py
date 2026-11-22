from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.routers import trips, navigation

app = FastAPI(
    title="FE Express Dispatcher, Trip & Navigation API",
    description="Realtime fleet monitoring, truck navigation guidance, and live GPS tracking",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount trips and navigation routers
app.include_router(trips.router)
app.include_router(navigation.router)

# Mount dispatch frontend if present
dispatch_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dispatch"))
if os.path.exists(dispatch_dir):
    app.mount("/dispatch", StaticFiles(directory=dispatch_dir, html=True), name="dispatch")


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "service": "FE Express Trip & Navigation Dispatch"}
