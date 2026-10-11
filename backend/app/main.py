from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, skus, datasets, anomalies, scenarios, ai_routes

app = FastAPI(
    title="StockSense API",
    version="1.0.0",
    description="Adaptive Inventory Replenishment Engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(skus.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(ai_routes.router, prefix="/api")
