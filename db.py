import asyncpg

SEED_APIS = [
    # AI / ML
    {"id": "arxiv",          "name": "arXiv",              "sector": "ai",                "url": "https://export.arxiv.org/api/query",                                "protocol": "atom", "auth": "none",    "priority": 10, "status": "active"},
    {"id": "semantic",       "name": "Semantic Scholar",   "sector": "ai",                "url": "https://api.semanticscholar.org/graph/v1/paper/search",              "protocol": "rest", "auth": "none",    "priority": 10, "status": "active"},
    {"id": "openalex",       "name": "OpenAlex",           "sector": "multidisciplinary", "url": "https://api.openalex.org/works",                                     "protocol": "rest", "auth": "none",    "priority": 9,  "status": "active"},
    {"id": "paperswithcode", "name": "Papers With Code",   "sector": "ai",                "url": "https://paperswithcode.com/api/v1/papers/",                          "protocol": "rest", "auth": "none",    "priority": 9,  "status": "active"},
    {"id": "core",           "name": "CORE",               "sector": "multidisciplinary", "url": "https://api.core.ac.uk/v3/search/works",                             "protocol": "rest", "auth": "api_key", "priority": 8,  "status": "active"},
    # Biology / Medicine
    {"id": "pubmed",         "name": "PubMed",             "sector": "biology",           "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",         "protocol": "rest", "auth": "none",    "priority": 9,  "status": "active"},
    {"id": "europepmc",      "name": "Europe PMC",         "sector": "biology",           "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",             "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    {"id": "biorxiv",        "name": "bioRxiv",            "sector": "biology",           "url": "https://api.biorxiv.org/details/biorxiv",                            "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    # Physics
    {"id": "inspire",        "name": "INSPIRE-HEP",        "sector": "physics",           "url": "https://inspirehep.net/api/literature",                              "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    {"id": "nasaads",        "name": "NASA ADS",           "sector": "physics",           "url": "https://api.adsabs.harvard.edu/v1/search/query",                     "protocol": "rest", "auth": "api_key", "priority": 7,  "status": "active"},
    # Multidisciplinary
    {"id": "crossref",       "name": "CrossRef",           "sector": "multidisciplinary", "url": "https://api.crossref.org/works",                                     "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    {"id": "doaj",           "name": "DOAJ",               "sector": "multidisciplinary", "url": "https://doaj.org/api/search/articles",                               "protocol": "rest", "auth": "none",    "priority": 7,  "status": "active"},
    {"id": "zenodo",         "name": "Zenodo",             "sector": "multidisciplinary", "url": "https://zenodo.org/api/records",                                     "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    {"id": "lens",           "name": "Lens.org",           "sector": "multidisciplinary", "url": "https://api.lens.org/scholarly/search",                              "protocol": "rest", "auth": "api_key", "priority": 7,  "status": "active"},
    # Social / Economics
    {"id": "ssrn",           "name": "SSRN",               "sector": "social",            "url": "https://api.ssrn.com/content/search/",                               "protocol": "rest", "auth": "none",    "priority": 6,  "status": "active"},
    {"id": "eric",           "name": "ERIC",               "sector": "social",            "url": "https://api.ies.ed.gov/eric/",                                       "protocol": "rest", "auth": "none",    "priority": 6,  "status": "active"},
    # Chemistry
    {"id": "chemrxiv",       "name": "ChemRxiv",           "sector": "chemistry",         "url": "https://chemrxiv.org/engage/chemrxiv/public-api/v1/items",           "protocol": "rest", "auth": "none",    "priority": 7,  "status": "active"},
    # Climate / Earth
    {"id": "eartharxiv",     "name": "EarthArXiv",         "sector": "physics",           "url": "https://eartharxiv.org/api/v2/preprints/",                           "protocol": "rest", "auth": "none",    "priority": 6,  "status": "active"},
    # CS
    {"id": "dblp",           "name": "DBLP",               "sector": "cs",                "url": "https://dblp.org/search/publ/api",                                   "protocol": "rest", "auth": "none",    "priority": 8,  "status": "active"},
    {"id": "unpaywall",      "name": "Unpaywall",          "sector": "multidisciplinary", "url": "https://api.unpaywall.org/v2/search",                                "protocol": "rest", "auth": "none",    "priority": 7,  "status": "active"},
]


async def init_db(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS apis (
                id          TEXT PRIMARY KEY,
                name        TEXT,
                sector      TEXT,
                url         TEXT,
                protocol    TEXT,
                auth        TEXT,
                priority    INT  DEFAULT 5,
                status      TEXT DEFAULT 'active',
                fail_count  INT  DEFAULT 0,
                last_checked TIMESTAMPTZ
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS results_cache (
                id         SERIAL PRIMARY KEY,
                topic      TEXT,
                api_id     TEXT,
                data       JSONB,
                fetched_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        count = await conn.fetchval("SELECT COUNT(*) FROM apis")
        if count == 0:
            await conn.executemany(
                "INSERT INTO apis (id,name,sector,url,protocol,auth,priority,status) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT DO NOTHING",
                [(a["id"],a["name"],a["sector"],a["url"],a["protocol"],a["auth"],a["priority"],a["status"]) for a in SEED_APIS]
            )
        else:
            # Migration: Ensure arXiv uses HTTPS
            await conn.execute("UPDATE apis SET url='https://export.arxiv.org/api/query' WHERE id='arxiv' AND url LIKE 'http://%'")


async def get_apis_by_sector(pool: asyncpg.Pool, sector: str) -> list:
    async with pool.acquire() as conn:
        if sector == "all":
            rows = await conn.fetch("SELECT * FROM apis WHERE status='active' ORDER BY priority DESC")
        else:
            rows = await conn.fetch("SELECT * FROM apis WHERE sector=$1 AND status='active' ORDER BY priority DESC", sector)
    return [dict(r) for r in rows]


async def mark_api_failed(pool: asyncpg.Pool, api_id: str):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE apis
            SET fail_count   = fail_count + 1,
                status       = CASE WHEN fail_count >= 4 THEN 'down' ELSE status END,
                last_checked = NOW()
            WHERE id = $1
        """, api_id)


async def mark_api_ok(pool: asyncpg.Pool, api_id: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE apis SET fail_count=0, status='active', last_checked=NOW() WHERE id=$1",
            api_id
        )
