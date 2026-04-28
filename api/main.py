from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from storage import init_buckets
from routers import upload, videos



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Streamflow API strating...")
    await init_db()
    init_buckets()
    print("Ready to handle requests")

    yield

    print("StreamFlow API shutting down...")


app = FastAPI(
    title="StreamFlow API",
    description="YOUTUBE LIKE video streaming platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://localhost:80","*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/upload",tags=["Upload"])
app.include_router(videos.router,prefix="/api/videos",tags=["Videos"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "service":"streamflow-api"}