import asyncio
import os
import httpx
from fetcher import run_search, download_pdf

# Load environment variables from deploy/.env if exists
env_path = "deploy/.env"
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

async def test_search_and_download():
    # 1. Search for "Attention Is All You Need"
    print("🔍 Searching for 'Attention Is All You Need'...")
    
    # We'll use a mock API list for direct testing if DB is not initialized
    # But since we have the DB URL, we'll try to initialize and get real APIs
    from db import init_db, get_apis_by_sector
    import asyncpg
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ DATABASE_URL not found, using manual API list for testing.")
        apis = [{"id": "arxiv", "name": "arXiv", "url": "http://export.arxiv.org/api/query", "protocol": "atom"}]
    else:
        try:
            pool = await asyncpg.create_pool(db_url, ssl="require")
            await init_db(pool)
            apis = await get_apis_by_sector(pool, "ai")
            await pool.close()
        except Exception as e:
            print(f"⚠️ Database connection failed: {e}. Using manual API list.")
            apis = [{"id": "arxiv", "name": "arXiv", "url": "http://export.arxiv.org/api/query", "protocol": "atom"}]

    results = await run_search("Attention Is All You Need", apis, limit=1)
    
    if not results:
        print("❌ No results found.")
        return

    paper = results[0]
    print(f"✅ Found paper: {paper['title']}")
    print(f"🔗 URL: {paper['url']}")

    # 2. Test Download
    print(f"📥 Attempting to download: {paper['url']}...")
    try:
        content, filename = await download_pdf(paper['url'])
        save_path = f"downloads/{filename}"
        os.makedirs("downloads", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(content)
        print(f"🎉 Successfully downloaded to: {save_path} ({len(content)} bytes)")
    except Exception as e:
        print(f"❌ Download failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_and_download())
