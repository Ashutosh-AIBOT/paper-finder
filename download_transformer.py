import asyncio
import os
from fetcher import download_pdf

async def download_transformer():
    # Canonical arXiv URL and Title for "Attention Is All You Need"
    url = "https://arxiv.org/abs/1706.03762"
    title = "Attention Is All You Need"
    print(f"📥 Downloading: {title} from {url}")
    
    try:
        content, filename = await download_pdf(url, title=title)
        os.makedirs("downloads", exist_ok=True)
        save_path = f"downloads/{filename}"
        with open(save_path, "wb") as f:
            f.write(content)
        print(f"🎉 Successfully downloaded: {save_path} ({len(content)} bytes)")
    except Exception as e:
        print(f"❌ Download failed: {e}")

if __name__ == "__main__":
    asyncio.run(download_transformer())
