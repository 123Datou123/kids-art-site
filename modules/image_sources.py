"""
Image source module
Plugin-style design — to add a new image source, implement the ImageSource interface
and register it in SOURCES.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests

from config import Config


class ImageSource(ABC):
    """Abstract base class for image sources."""
    name: str = ""

    @abstractmethod
    def search(self, query: str, count: int = 12) -> List[Dict]:
        """
        Search for images by keyword.
        Returns a list of dicts:
        [
            {
                "id": "unique id",
                "title": "image title",
                "thumb_url": "thumbnail URL",
                "full_url": "full-size URL",
                "source": "source name",
                "page_url": "original page URL (for attribution)",
            },
            ...
        ]
        """
        raise NotImplementedError


class WikimediaSource(ImageSource):
    """
    Wikimedia Commons — free, no API key required.
    Content is public domain or freely licensed; mostly educational and nature topics.
    """
    name = "wikimedia"
    API_URL = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str, count: int = 12) -> List[Dict]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            # Restrict to bitmap images (jpg/png), exclude SVG/audio/video
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,           # File namespace
            "gsrlimit": count,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 400,           # Thumbnail width
        }
        headers = {"User-Agent": "KidsArtSite/1.0 (Educational; contact@example.com)"}
        resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict] = []
        pages = data.get("query", {}).get("pages", {})
        # Sort by search relevance index
        sorted_pages = sorted(
            pages.values(),
            key=lambda p: p.get("index", 9999)
        )
        for page in sorted_pages:
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            mime = info.get("mime", "")
            # Skip non-images and SVG
            if not mime.startswith("image/") or "svg" in mime:
                continue
            title = page.get("title", "").replace("File:", "")
            results.append({
                "id": str(page.get("pageid", "")),
                "title": title,
                "thumb_url": info.get("thumburl") or info.get("url"),
                "full_url": info.get("url"),
                "source": self.name,
                "page_url": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
            })
        return results


class PixabaySource(ImageSource):
    """
    Pixabay — free high-quality image library.
    Requires a free API key (https://pixabay.com/api/docs/).
    Has safesearch, making it suitable for kids.
    """
    name = "pixabay"
    API_URL = "https://pixabay.com/api/"

    def search(self, query: str, count: int = 12) -> List[Dict]:
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
            "safesearch": "true",     # Enable safe search to filter adult content
            "per_page": max(3, min(count, 200)),
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


# ============ Source registry ============
# To add a new image source — register it here.
SOURCES: Dict[str, ImageSource] = {
    WikimediaSource.name: WikimediaSource(),
    PixabaySource.name: PixabaySource(),
}


def get_source(name: str) -> Optional[ImageSource]:
    """Get a source instance by name."""
    return SOURCES.get(name)


def list_sources() -> List[str]:
    """List all registered source names."""
    return list(SOURCES.keys())
