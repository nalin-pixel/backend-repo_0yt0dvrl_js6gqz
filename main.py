import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

app = FastAPI(title="SeedCodes API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
from schemas import Project

# Database helpers
from database import db, create_document, get_documents


@app.get("/")
def read_root():
    return {"message": "SeedCodes API running"}


@app.get("/schema")
def get_schema():
    """Expose Pydantic schemas for the workspace database viewer"""
    return {
        "project": Project.model_json_schema(),
    }


class CreateProjectRequest(Project):
    pass


@app.post("/api/projects", response_model=dict)
def create_project(payload: CreateProjectRequest):
    try:
        inserted_id = create_document("project", payload)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects", response_model=List[dict])
def list_projects(tag: Optional[str] = None, limit: int = 24):
    try:
        filter_query = {"tags": {"$in": [tag]}} if tag else {}
        docs = get_documents("project", filter_query, limit)
        # Convert ObjectId to string for JSON
        for d in docs:
            if isinstance(d.get("_id"), ObjectId):
                d["id"] = str(d.pop("_id"))
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# --- Seeding utilities ---
SAMPLE_PROJECTS: List[Project] = [
    Project(
        title="Neon Path Tracer",
        description="Real-time WebGL path tracer with denoising and emissive materials.",
        tags=["webgl", "graphics", "shader"],
        github_url="https://github.com/example/neon-tracer",
        live_url="https://seedcodes.dev/demos/neon-tracer",
        thumbnail="https://images.unsplash.com/photo-1551817958-20204d6ab8f8?q=80&w=1200&auto=format&fit=crop"
    ),
    Project(
        title="Synthwave ChatGPT UI",
        description="A stylized AI chat interface with streaming tokens and prompt presets.",
        tags=["ai", "ui", "react"],
        github_url="https://github.com/example/synthwave-chat",
        live_url="https://seedcodes.dev/demos/synthwave-chat",
        thumbnail="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1200&auto=format&fit=crop"
    ),
    Project(
        title="Robotic Arm Planner",
        description="Inverse kinematics visualizer and motion planner with constraints.",
        tags=["robotics", "ik", "python"],
        github_url="https://github.com/example/arm-planner",
        live_url="https://seedcodes.dev/demos/arm-planner",
        thumbnail="https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?q=80&w=1200&auto=format&fit=crop"
    ),
    Project(
        title="Audio-Driven Particles",
        description="FFT-reactive particle system with GPU instancing and post-processing.",
        tags=["audio", "threejs", "gpu"],
        github_url="https://github.com/example/audio-particles",
        live_url="https://seedcodes.dev/demos/audio-particles",
        thumbnail="https://images.unsplash.com/photo-1518655048521-f130df041f66?q=80&w=1200&auto=format&fit=crop"
    ),
]


def _seed_if_empty() -> dict:
    if db is None:
        return {"seeded": False, "reason": "Database not configured"}
    count = db["project"].count_documents({})
    if count > 0:
        return {"seeded": False, "reason": "Collection already has data", "count": count}
    inserted = 0
    for p in SAMPLE_PROJECTS:
        try:
            create_document("project", p)
            inserted += 1
        except Exception:
            pass
    return {"seeded": True, "inserted": inserted}


@app.post("/api/seed")
def manual_seed():
    try:
        return _seed_if_empty()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def startup_seed():
    try:
        _seed_if_empty()
    except Exception:
        # Ignore seeding errors during startup to not block the app
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
