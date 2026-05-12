"""
Image source module
Plugin-style design — to add a new image source, implement the ImageSource interface
and register it in SOURCES.

NEW in v2: pagination support via `page` parameter.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests

from config import Config


class ImageSource(ABC):
    """Abstract base class for image sources."""
    name: str = ""

    @abstractmethod
    def search(self, query: str, count: int = 12, page: int = 1) -> List[Dict]:
        """
        Search for images.
        page is 1-indexed. count is per-page.
        """
        raise NotImplementedError


class WikimediaSource(ImageSource):
    """Wikimedia Commons — free, no API key required."""
    name = "wikimedia"
    API_URL = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str, count: int = 12, page: int = 1) -> List[Dict]:
        # Wikimedia uses an offset-based pagination
        offset = max(0, (page - 1) * count)

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": count,
            "gsroffset": offset,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 400,
        }
        headers = {"User-Agent": "KidsArtSite/1.0 (Educational; contact@example.com)"}
        resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict] = []
        pages = data.get("query", {}).get("pages", {})
        sorted_pages = sorted(
            pages.values(),
            key=lambda p: p.get("index", 9999)
        )
        for page_item in sorted_pages:
            info_list = page_item.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            mime = info.get("mime", "")
            if not mime.startswith("image/") or "svg" in mime:
                continue
            title = page_item.get("title", "").replace("File:", "")
            results.append({
                "id": str(page_item.get("pageid", "")),
                "title": title,
                "thumb_url": info.get("thumburl") or info.get("url"),
                "full_url": info.get("url"),
                "source": self.name,
                "page_url": f"https://commons.wikimedia.org/wiki/{page_item.get('title', '').replace(' ', '_')}",
            })
        return results


class PixabaySource(ImageSource):
    """Pixabay — free with API key, supports safesearch (kid-friendly)."""
    name = "pixabay"
    API_URL = "https://pixabay.com/api/"

    def search(self, query: str, count: int = 12, page: int = 1) -> List[Dict]:
        api_key = Config.PIXABAY_API_KEY
        if not api_key:
            raise RuntimeError(
                "Pixabay API key not configured. "
                "Register for free at https://pixabay.com/api/docs/ "
                "and set the PIXABAY_API_KEY environment variable."
            )

        params = {
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "safesearch": "true",
            "per_page": max(3, min(count, 200)),
            "page": max(1, page),
            "lang": "en",
        }
        resp = requests.get(self.API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict] = []
        for hit in data.get("hits", []):
            results.append({
                "id": str(hit.get("id", "")),
                "title": hit.get("tags", "")[:80],
                "thumb_url": hit.get("webformatURL") or hit.get("previewURL"),
                "full_url": hit.get("largeImageURL") or hit.get("webformatURL"),
                "source": self.name,
                "page_url": hit.get("pageURL", ""),
            })
        return results


SOURCES: Dict[str, ImageSource] = {
    WikimediaSource.name: WikimediaSource(),
    PixabaySource.name: PixabaySource(),
}


def get_source(name: str) -> Optional[ImageSource]:
    return SOURCES.get(name)


def list_sources() -> List[str]:
    return list(SOURCES.keys())
