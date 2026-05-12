"""
图片源模块
设计为插件式 —— 新增图片源时实现 ImageSource 接口并注册到 SOURCES 即可
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests

from config import Config


class ImageSource(ABC):
    """图片源抽象基类"""
    name: str = ""

    @abstractmethod
    def search(self, query: str, count: int = 12) -> List[Dict]:
        """
        根据关键词搜索图片
        返回结构示例:
        [
            {
                "id": "唯一标识",
                "title": "图片标题",
                "thumb_url": "缩略图 URL",
                "full_url": "原图 URL",
                "source": "数据源名称",
                "page_url": "原始页面 URL（用于标注来源）",
            },
            ...
        ]
        """
        raise NotImplementedError


class WikimediaSource(ImageSource):
    """
    Wikimedia Commons —— 维基共享资源
    特点：无需 API 密钥；内容为公共领域或自由许可；以教育、自然类内容居多
    """
    name = "wikimedia"
    API_URL = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str, count: int = 12) -> List[Dict]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            # 限定为位图（jpg/png 等），过滤掉 SVG / 音视频
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,           # File 命名空间
            "gsrlimit": count,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 400,           # 缩略图宽度
        }
        headers = {"User-Agent": "KidsArtSite/1.0 (Educational; contact@example.com)"}
        resp = requests.get(self.API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results: List[Dict] = []
        pages = data.get("query", {}).get("pages", {})
        # 按 index 排序保持搜索相关性顺序
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
            # 过滤非图片或 SVG
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
    Pixabay —— 免费高质量图片库
    特点：需要免费 API 密钥（https://pixabay.com/api/docs/）；支持 safesearch，更适合儿童
    """
    name = "pixabay"
    API_URL = "https://pixabay.com/api/"

    def search(self, query: str, count: int = 12) -> List[Dict]:
        api_key = Config.PIXABAY_API_KEY
        if not api_key:
            raise RuntimeError(
                "未配置 Pixabay API 密钥。请在 https://pixabay.com/api/docs/ "
                "免费注册后设置 PIXABAY_API_KEY 环境变量。"
            )

        params = {
            "key": api_key,
            "q": query,
            "image_type": "photo",
            "safesearch": "true",     # 关键：开启安全搜索，过滤成人内容
            "per_page": max(3, min(count, 200)),
            "lang": "zh",
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


# ============ 数据源注册表 ============
# 想新增图片源 → 在此处注册即可
SOURCES: Dict[str, ImageSource] = {
    WikimediaSource.name: WikimediaSource(),
    PixabaySource.name: PixabaySource(),
}


def get_source(name: str) -> Optional[ImageSource]:
    """根据名称获取数据源实例"""
    return SOURCES.get(name)


def list_sources() -> List[str]:
    """列出所有可用数据源"""
    return list(SOURCES.keys())
