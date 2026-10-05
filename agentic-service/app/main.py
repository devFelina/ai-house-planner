from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from app.api.routers import workflow_routes, assistant_routes, knowledge_routes, readiness_routes
from app.config import OUTPUT_PLANS_DIR, VISUALIZATIONS_DIR

app = FastAPI(title="Agentic AI Service - House Planner")

import os
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow_routes.router)
app.include_router(assistant_routes.router)
app.include_router(knowledge_routes.router)
app.include_router(readiness_routes.router)

app.mount("/plans", StaticFiles(directory=str(OUTPUT_PLANS_DIR)), name="plans")
app.mount("/visualizations", StaticFiles(directory=str(VISUALIZATIONS_DIR)), name="visualizations")

@app.get("/")
async def root():
    return {
        "message": "AI House Planner Agentic Service is running on Render",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "agentic-service"
    }
