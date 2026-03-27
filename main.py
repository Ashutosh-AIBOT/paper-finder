from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
import io
from contextlib import asynccontextmanager
import asyncio, asyncpg, os
from fetcher import run_search, download_pdf
from db import init_db, get_apis_by_sector

DATABASE_URL = os.getenv("DATABASE_URL", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log information without revealing secrets
    if not DATABASE_URL:
        print("❌ DATABASE_URL is missing or empty. Please check your Hugging Face Secrets.")
    else:
        print(f"🏁 Connecting to Database (URL length: {len(DATABASE_URL)} characters)")
    
    try:
        app.state.pool = await asyncpg.create_pool(
            DATABASE_URL, 
            ssl="require", 
            min_size=1, 
            max_size=10,
            command_timeout=10
        )
        await init_db(app.state.pool)
        app.state.db_status = "Connected"
        print("✅ Database connection established.")
    except Exception as e:
        app.state.pool = None
        app.state.db_status = f"Disconncted: {str(e)}"
        print(f"⚠️ Warning: Database connection failed. Details: {e}")
    
    yield
    
    if app.state.pool:
        await app.state.pool.close()

app = FastAPI(title="Research Paper API", lifespan=lifespan)

@app.get("/")
def root():
    return {
        "status": "ok", 
        "database": getattr(app.state, 'db_status', 'Unknown'),
        "endpoints": ["/search", "/apis", "/sectors", "/docs"]
    }

@app.get("/search")
async def search(topic: str, sector: str = "all", limit: int = Query(default=10, le=50)):
    apis = await get_apis_by_sector(app.state.pool, sector)
    results = await run_search(topic, apis, limit)
    return {"topic": topic, "sector": sector, "total": len(results), "results": results}

@app.get("/apis")
async def list_apis(sector: str = "all"):
    apis = await get_apis_by_sector(app.state.pool, sector)
    return {"total": len(apis), "apis": [{"id": a["id"], "name": a["name"], "sector": a["sector"], "status": a["status"], "priority": a["priority"]} for a in apis]}

@app.get("/sectors")
async def list_sectors():
    return {"sectors": ["all", "ai", "biology", "physics", "cs", "multidisciplinary", "social", "chemistry"]}

@app.get("/download")
async def download_paper(url: str, title: str = None):
    """
    Downloads a research paper from a given URL and streams it to the user.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    
    try:
        content, filename = await download_pdf(url, title=title)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
