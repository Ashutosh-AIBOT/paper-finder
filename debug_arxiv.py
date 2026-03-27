import httpx
import xml.etree.ElementTree as ET
import asyncio

async def debug_arxiv():
    url = "http://export.arxiv.org/api/query"
    params = {"search_query": "all:Attention Is All You Need", "max_results": 5}
    print(f"Fetching from: {url} with {params}")
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
        print(f"Status: {r.status_code}")
        # print(f"Content: {r.text[:500]}")
        
        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(r.text)
            entries = root.findall("a:entry", ns)
            print(f"Found {len(entries)} entries")
            for e in entries:
                title = e.find("a:title", ns).text
                print(f"Title: {title.strip() if title else 'N/A'}")
        except Exception as e:
            print(f"Error parsing: {e}")

if __name__ == "__main__":
    asyncio.run(debug_arxiv())
