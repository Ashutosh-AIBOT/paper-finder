import httpx, asyncio, xml.etree.ElementTree as ET
from datetime import datetime

CURRENT_YEAR = datetime.now().year
TIMEOUT = 8


# ── Protocol Parsers ──────────────────────────────────────────────────────────

def parse_atom(text: str) -> list:
    try:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(text)
        out = []
        for e in root.findall("a:entry", ns):
            yr = (e.find("a:published", ns).text or "")[:4]
            out.append({
                "title":    (e.find("a:title", ns).text or "").strip(),
                "abstract": (e.find("a:summary", ns).text or "").strip()[:300],
                "url":      (e.find("a:id", ns).text or "").strip(),
                "year":     int(yr) if yr.isdigit() else CURRENT_YEAR,
                "authors":  [a.find("a:name", ns).text for a in e.findall("a:author", ns)][:3],
                "citations": 0,
            })
        return out
    except Exception:
        return []


def parse_oaipmh(text: str) -> list:
    try:
        root = ET.fromstring(text)
        ns = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "dc":  "http://purl.org/dc/elements/1.1/",
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
        }
        out = []
        for record in root.findall(".//oai:record", ns):
            meta = record.find(".//oai_dc:dc", ns)
            if meta is None:
                continue
            title    = (meta.findtext("dc:title", default="", namespaces=ns) or "").strip()
            abstract = (meta.findtext("dc:description", default="", namespaces=ns) or "")[:300]
            url      = (meta.findtext("dc:identifier", default="", namespaces=ns) or "").strip()
            date_raw = (meta.findtext("dc:date", default="", namespaces=ns) or "")[:4]
            authors  = [a.text for a in meta.findall("dc:creator", ns) if a.text][:3]
            if title:
                out.append({
                    "title": title, "abstract": abstract, "url": url,
                    "year": int(date_raw) if date_raw.isdigit() else CURRENT_YEAR,
                    "authors": authors, "citations": 0,
                })
        return out
    except Exception:
        return []


def parse_rest(data: dict, api_id: str) -> list:
    items = (
        data.get("data") or
        data.get("results") or
        data.get("items") or
        data.get("response", {}).get("docs") or
        data.get("hits", {}).get("hits") or
        data.get("records") or
        data.get("papers") or
        data.get("esearchresult", {}).get("idlist") or
        []
    )
    out = []
    for p in items[:20]:
        if isinstance(p, str):
            out.append({"title": f"ID:{p}", "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}",
                        "year": CURRENT_YEAR, "authors": [], "citations": 0, "abstract": ""})
            continue
        title = (p.get("title") or p.get("display_title") or
                 (p.get("titles") or [{}])[0].get("title") or
                 p.get("_source", {}).get("title") or "")
        abstract = (p.get("abstract") or p.get("description") or
                    p.get("_source", {}).get("abstract") or "")
        url = (p.get("url") or p.get("doi") or p.get("id") or
               p.get("link") or p.get("arxiv_eprints", [{}])[0].get("value") or "")
        year = (p.get("year") or p.get("publication_year") or
                str(p.get("publishedDate", "") or "")[:4] or
                str((p.get("imprints") or [{}])[0].get("date", "") or "")[:4] or CURRENT_YEAR)
        try:
            year = int(str(year)[:4])
        except Exception:
            year = CURRENT_YEAR
        citations = (p.get("citationCount") or p.get("cited_by_count") or
                     p.get("times_cited") or p.get("citation_count") or 0)
        authors_raw = p.get("authors") or p.get("authorships") or p.get("author") or []
        authors = []
        for a in authors_raw[:3]:
            if isinstance(a, str):
                authors.append(a)
            elif isinstance(a, dict):
                authors.append(a.get("name") or a.get("display_name") or
                               (a.get("author") or {}).get("display_name") or
                               a.get("full_name") or "")
        if title:
            out.append({
                "title": str(title).strip(),
                "abstract": str(abstract)[:300],
                "url": str(url),
                "year": year,
                "authors": [x for x in authors if x],
                "citations": int(citations) if citations else 0,
            })
    return out


# ── Request Builder ───────────────────────────────────────────────────────────

def build_request(api: dict, topic: str) -> tuple:
    aid, url = api["id"], api["url"]
    params, headers = {}, {}

    if aid == "arxiv":
        params = {"search_query": f"all:{topic}", "max_results": 15, "sortBy": "relevance"}
    elif aid == "semantic":
        params = {"query": topic, "limit": 15, "fields": "title,authors,year,abstract,url,citationCount"}
    elif aid == "openalex":
        params = {"search": topic, "per-page": 15, "sort": "cited_by_count:desc"}
        headers = {"User-Agent": "ResearchPaperAPI/1.0"}
    elif aid == "paperswithcode":
        params = {"q": topic, "items_per_page": 15}
    elif aid == "pubmed":
        params = {"db": "pubmed", "term": topic, "retmax": 15, "retmode": "json"}
    elif aid == "europepmc":
        params = {"query": topic, "resultType": "core", "pageSize": 15, "format": "json"}
    elif aid == "biorxiv":
        url = f"{url}/{topic}/0/15/json"
    elif aid == "inspire":
        params = {"q": topic, "size": 15, "fields": "titles,authors,arxiv_eprints,citation_count,imprints"}
    elif aid == "crossref":
        params = {"query": topic, "rows": 15, "select": "title,author,published,DOI,is-referenced-by-count"}
    elif aid == "doaj":
        url = f"{url}/{topic}"
        params = {"pageSize": 15}
    elif aid == "zenodo":
        params = {"q": topic, "size": 15, "type": "publication"}
    elif aid == "chemrxiv":
        params = {"term": topic, "limit": 15}
    elif aid == "eartharxiv":
        params = {"filter[title]": topic, "page[size]": 15}
    elif aid == "eric":
        params = {"search": topic, "format": "json", "rows": 15}
    elif aid == "dblp":
        params = {"q": topic, "format": "json", "h": 15}
    elif aid == "unpaywall":
        params = {"query": topic, "email": "research@api.com"}
    else:
        params = {"query": topic, "q": topic, "search": topic, "limit": 15}

    return url, params, headers


# ── Single Fetcher ────────────────────────────────────────────────────────────

async def fetch_one(client: httpx.AsyncClient, api: dict, topic: str) -> tuple:
    try:
        url, params, headers = build_request(api, topic)
        r = await client.get(url, params=params, headers=headers, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code in (429, 401, 403):
            return api["id"], []
        if r.status_code != 200:
            return api["id"], []

        proto = api.get("protocol", "rest")
        if proto == "atom":
            papers = parse_atom(r.text)
        elif proto == "oaipmh":
            papers = parse_oaipmh(r.text)
        else:
            try:
                papers = parse_rest(r.json(), api["id"])
            except Exception:
                papers = []

        for p in papers:
            p["source"] = api["name"]
            age = max(CURRENT_YEAR - p.get("year", CURRENT_YEAR), 1)
            p["boom_score"] = round(p.get("citations", 0) / age, 1)

        return api["id"], papers

    except Exception:
        return api["id"], []


# ── Master Search ─────────────────────────────────────────────────────────────

async def run_search(topic: str, apis: list, limit: int) -> list:
    all_papers, seen = [], set()
    apis = sorted(apis, key=lambda x: x.get("priority", 5), reverse=True)
    batches = [apis[i:i+5] for i in range(0, len(apis), 5)]

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for batch in batches:
            tasks = [fetch_one(client, api, topic) for api in batch]
            for api_id, papers in await asyncio.gather(*tasks):
                for p in papers:
                    key = (p.get("title") or "").lower()[:50]
                    if key and key not in seen:
                        seen.add(key)
                        all_papers.append(p)
            if len(all_papers) >= limit * 2:
                break

    all_papers.sort(key=lambda x: x.get("boom_score", 0), reverse=True)
    return all_papers[:limit]


# ── Paper Downloader ──────────────────────────────────────────────────────────

import re

def sanitize_filename(name: str) -> str:
    """Removes invalid characters and trims the name."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()[:100]


async def download_pdf(url: str, title: str = None) -> tuple[bytes, str]:
    """
    Downloads a PDF from a given URL, optionally using a title for the filename.
    Returns (content, filename).
    """
    # 1. Clean and convert common abstract URLs to PDF URLs
    pdf_url = url
    
    # Default filename logic
    if title:
        filename = sanitize_filename(title) + ".pdf"
    else:
        filename = "paper.pdf"

    if "arxiv.org/abs/" in url:
        pdf_url = url.replace("arxiv.org/abs/", "arxiv.org/pdf/") + ".pdf"
        if not title:
            filename = pdf_url.split("/")[-1]
    elif "arxiv.org/pdf/" in url and not url.endswith(".pdf"):
        pdf_url = url + ".pdf"
        if not title:
            filename = pdf_url.split("/")[-1]
    elif "semanticscholar.org" in url:
        # Semantic Scholar abstract URLs aren't directly convertible to PDF without API/extra logic
        # For now, we hope the URL provided in search results is a direct/accessible PDF if it ends in .pdf
        pass
    
    # 2. Perform the download
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(pdf_url, timeout=15)
            r.raise_for_status()
            
            # 3. Verify content-type
            content_type = r.headers.get("Content-Type", "").lower()
            if "application/pdf" not in content_type and len(r.content) < 1000:
                # If not a PDF and very small, might be an error page
                raise ValueError(f"URL did not return a valid PDF. Content-Type: {content_type}")
            
            return r.content, filename
            
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to download paper: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")
