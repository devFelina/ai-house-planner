from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import workflow_routes, assistant_routes, knowledge_routes

app = FastAPI(title="Agentic AI Service - House Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Allow React app explicitly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflow_routes.router)
app.include_router(assistant_routes.router)
app.include_router(knowledge_routes.router)

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
