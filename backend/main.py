import os
import sys

# Make root importable so routers can reach db/ and utils/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import patients, clinician, coordinator, admin
from utils.helpers import ensure_seeded

app = FastAPI(title="FulcrumCare API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router,    prefix="/api")
app.include_router(clinician.router,   prefix="/api/clinician")
app.include_router(coordinator.router, prefix="/api/coordinator")
app.include_router(admin.router,       prefix="/api/admin")


@app.on_event("startup")
def on_startup():
    ensure_seeded()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/seed")
def reseed():
    from db.seed import seed_database
    seed_database()
    return {"ok": True}
