"""
儿童图片浏览与线稿生成网站
入口文件 —— Flask 应用主程序
"""
import io
import os
import requests
from flask import Flask, render_template, request, jsonify, send_file, abort

from config import Config
from modules.image_sources import get_source
from modules.line_art import generate_lineart

app = Flask(__name__)
app.config.from_object(Config)


# ============== 页面路由 ==============

@app.route("/")
def index():
    """主页"""
    return render_template("index.html",
                           default_source=app.config["DEFAULT_SOURCE"])


# ============== API 路由 ==============

@app.route("/api/search", methods=["GET"])
def api_search():
    """
    搜索图片
    参数: q（关键词）、source（数据源，可选）、count（返回数量，默认 12）
    """
    query = request.args.get("q", "").strip()
    source_name = request.args.get("source", app.config["DEFAULT_SOURCE"])
    try:
        count = min(int(request.args.get("count", 12)), 30)
    except ValueError:
        count = 12

    if not query:
        return jsonify({"error": "请提供搜索关键词"}), 400

    source = get_source(source_name)
    if source is None:
        return jsonify({"error": f"未知数据源：{source_name}"}), 400

    try:
        results = source.search(query, count=count)
        return jsonify({
            "query": query,
            "source": source_name,
            "count": len(results),
            "images": results,
        })
    except Exception as e:
        app.logger.exception("搜索失败")
        return jsonify({"error": f"搜索失败：{str(e)}"}), 500


@app.route("/api/download")
def api_download():
    """
    代理下载图片（避免跨域问题，同时统一文件名）
    参数: url（图片地址）、filename（可选，下载文件名）
    """
    url = request.args.get("url", "").strip()
    filename = request.args.get("filename", "image.jpg")

    if not url or not url.startswith(("http://", "https://")):
        abort(400, description="无效的图片地址")

    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "KidsArtSite/1.0 (Educational)"
        })
        resp.raise_for_status()
        return send_file(
            io.BytesIO(resp.content),
            mimetype=resp.headers.get("Content-Type", "image/jpeg"),
            as_attachment=True,
            download_name=filename,
        )
    except requests.RequestException as e:
        app.logger.exception("下载失败")
        abort(502, description=f"图片下载失败：{str(e)}")


@app.route("/api/lineart", methods=["POST"])
def api_lineart():
    """
    根据图片 URL 生成线稿图
    JSON 参数: url（图片地址）、style（cartoon / sketch，默认 cartoon）
    返回: PNG 图片
    """
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    style = data.get("style", "cartoon")

    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "无效的图片地址"}), 400

    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "KidsArtSite/1.0 (Educational)"
        })
        resp.raise_for_status()
        lineart_bytes = generate_lineart(resp.content, style=style)
        return send_file(
            io.BytesIO(lineart_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="lineart.png",
        )
    except Exception as e:
        app.logger.exception("线稿生成失败")
        return jsonify({"error": f"线稿生成失败：{str(e)}"}), 500


@app.route("/api/lineart/from-text", methods=["POST"])
def api_lineart_from_text():
    """
    根据文字指令生成线稿图：
    1. 用关键词在图片源里搜一张匹配图
    2. 自动转成线稿
    JSON 参数: query（描述词）、source（可选）、style（cartoon / sketch）
    返回: PNG 图片
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    source_name = data.get("source", app.config["DEFAULT_SOURCE"])
    style = data.get("style", "cartoon")

    if not query:
        return jsonify({"error": "请提供描述词"}), 400

    source = get_source(source_name)
    if source is None:
        return jsonify({"error": f"未知数据源：{source_name}"}), 400

    try:
        results = source.search(query, count=5)
        if not results:
            return jsonify({"error": "未找到相关图片，请尝试其他关键词"}), 404

        # 取第一张作为线稿原图
        chosen = results[0]
        image_url = chosen.get("full_url") or chosen.get("thumb_url")

        resp = requests.get(image_url, timeout=20, headers={
            "User-Agent": "KidsArtSite/1.0 (Educational)"
        })
        resp.raise_for_status()
        lineart_bytes = generate_lineart(resp.content, style=style)

        return send_file(
            io.BytesIO(lineart_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name=f"lineart_{query}.png",
        )
    except Exception as e:
        app.logger.exception("文本生成线稿失败")
        return jsonify({"error": f"生成失败：{str(e)}"}), 500


if __name__ == "__main__":
    # 本地开发模式，端口可在环境变量里改
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
