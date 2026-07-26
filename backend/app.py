"""FastAPI application main entry point."""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.config import API_HOST, API_PORT, FRONTEND_URL, LOG_LEVEL
from backend.db import init_db
from backend.routes import health, predict, recommend, correlations, feedback

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PaperMill Grade-Change Assistant",
    description="AI-powered advisory system for paper machine grade changes",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        raise

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(predict.router, prefix="/api", tags=["Predictions"])
app.include_router(recommend.router, prefix="/api", tags=["Recommendations"])
app.include_router(correlations.router, prefix="/api", tags=["Correlations"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PaperMill Grade-Change Assistant API",
        "docs": "/docs",
        "version": "0.1.0",
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "backend.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
