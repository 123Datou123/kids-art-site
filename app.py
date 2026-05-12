"""
Kids image gallery + online coloring tool
Flask entry point and routes.
"""
from dotenv import load_dotenv
load_dotenv()

import io
import os
import requests
from flask import Flask, render_template, request, jsonify, send_file, abort

from config import Config
from modules.image_sources import get_source
from modules.line_art import generate_lineart

app = Flask(__name__)
app.config.from_object(Config)


# ============== Pages ==============

@app.route("/")
def index():
    return render_template("index.html",
                           default_source=app.config["DEFAULT_SOURCE"])


@app.route("/color")
def color_page():
    image_url = request.args.get("url", "").strip()
    title = request.args.get("title", "").strip() or "your picture"
    style = request.args.get("style", "cartoon").strip()
    if style not in ("cartoon", "sketch"):
        style = "cartoon"
    return render_template("color.html",
                           image_url=image_url,
                           title=title,
                           style=style)


# ============== APIs ==============

@app.route("/api/search", methods=["GET"])
def api_search():
    """
    Search images.
    Params: q (keyword), source (optional), count (default 18), page (default 1, 1-indexed).
    """
    query = request.args.get("q", "").strip()
    source_name = request.args.get("source", app.config["DEFAULT_SOURCE"])
    try:
        count = min(int(request.args.get("count", 18)), 30)
    except ValueError:
        count = 18
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    if not query:
        return jsonify({"error": "Please provide a search keyword"}), 400

    source = get_source(source_name)
    if source is None:
        return jsonify({"error": f"Unknown source: {source_name}"}), 400

    try:
        results = source.search(query, count=count, page=page)
        return jsonify({
            "query": query,
            "source": source_name,
            "page": page,
            "count": len(results),
            "images": results,
            "has_more": len(results) >= count,
        })
    except Exception as e:
        app.logger.exception("Search failed")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/api/download")
def api_download():
    """Proxy-download an image to bypass CORS and standardize the filename."""
    url = request.args.get("url", "").strip()
    filename = request.args.get("filename", "image.jpg")

    if not url or not url.startswith(("http://", "https://")):
        abort(400, description="Invalid image URL")

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
        app.logger.exception("Download failed")
        abort(502, description=f"Image download failed: {str(e)}")


@app.route("/api/lineart", methods=["POST"])
def api_lineart():
    """
    Generate line art from an image URL.
    JSON params: url, style (cartoon|sketch), transparent (true|false)
    Returns: PNG bytes
    """
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    style = data.get("style", "cartoon")
    transparent = bool(data.get("transparent", False))

    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid image URL"}), 400

    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": "KidsArtSite/1.0 (Educational)"
        })
        resp.raise_for_status()
        lineart_bytes = generate_lineart(resp.content, style=style,
                                         transparent=transparent)
        return send_file(
            io.BytesIO(lineart_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="lineart.png",
        )
    except Exception as e:
        app.logger.exception("Line art generation failed")
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


@app.route("/api/lineart/from-text", methods=["POST"])
def api_lineart_from_text():
    """
    Generate line art from a text prompt (search → first result → line art).
    JSON params: query, source, style, transparent
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    source_name = data.get("source", app.config["DEFAULT_SOURCE"])
    style = data.get("style", "cartoon")
    transparent = bool(data.get("transparent", False))

    if not query:
        return jsonify({"error": "Please provide a description"}), 400

    source = get_source(source_name)
    if source is None:
        return jsonify({"error": f"Unknown source: {source_name}"}), 400

    try:
        results = source.search(query, count=5)
        if not results:
            return jsonify({"error": "No matching images found. Try different keywords."}), 404

        chosen = results[0]
        image_url = chosen.get("full_url") or chosen.get("thumb_url")

        resp = requests.get(image_url, timeout=20, headers={
            "User-Agent": "KidsArtSite/1.0 (Educational)"
        })
        resp.raise_for_status()
        lineart_bytes = generate_lineart(resp.content, style=style,
                                         transparent=transparent)

        return send_file(
            io.BytesIO(lineart_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name=f"lineart_{query}.png",
            # Pass the source image URL back via a custom header
            # so the frontend can offer "Color this online" directly
        )
    except Exception as e:
        app.logger.exception("Text-to-lineart failed")
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


@app.route("/api/lineart/find", methods=["POST"])
def api_lineart_find():
    """
    Like /api/lineart/from-text but returns JSON with the matched image URL,
    so the frontend can navigate to the /color page.
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    source_name = data.get("source", app.config["DEFAULT_SOURCE"])

    if not query:
        return jsonify({"error": "Please provide a description"}), 400

    source = get_source(source_name)
    if source is None:
        return jsonify({"error": f"Unknown source: {source_name}"}), 400

    try:
        results = source.search(query, count=5)
        if not results:
            return jsonify({"error": "No matching images found. Try different keywords."}), 404
        chosen = results[0]
        return jsonify({
            "url": chosen.get("full_url") or chosen.get("thumb_url"),
            "title": chosen.get("title") or query,
        })
    except Exception as e:
        app.logger.exception("Find failed")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
