from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator
from app.api.v1.routes import users, auth
from app.db.database import get_db
from app.db.cache import get_redis

app = FastAPI(
    title="User Service",
    version="0.1.0",
    description="User authentication and management service for the distributed notification system"
)

Instrumentator().instrument(app).expose(app)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/")
def read_root():
    return {"message": "User Service API", "version": "0.1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/health/deep")
def deep_health_check():
    health_status = {"status": "healthy", "db": "unknown", "cache": "unknown"}
    
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health_status["db"] = "healthy"
    except Exception as e:
        health_status["db"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    try:
        cache = get_redis()
        cache.ping()
        health_status["cache"] = "healthy"
    except Exception as e:
        health_status["cache"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status