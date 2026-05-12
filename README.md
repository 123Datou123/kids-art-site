# Kids Art Gallery · Coloring Page Generator

A simple website that lets elementary school students search for kid-friendly images and turn them into printable coloring pages.

## Features

1. **Search kid-friendly images** by keyword
   - Default source: **Wikimedia Commons** (free, no registration)
   - Optional: **Pixabay** (free API key required; better Chinese search & stricter safe-search)
2. **Download original images**
3. **One-click coloring page** — convert any image into a coloring book style line drawing
   - Two styles: "Coloring Book" (clean closed lines) and "Pencil Sketch" (soft and artistic)
4. **Text → Coloring page** — type a word like "dog" or "dinosaur" and get a coloring page automatically

## Project Structure

```
kids_art_site/
├── app.py                 # Flask entry point and routes
├── config.py              # Centralized config (API keys, defaults, line art params)
├── requirements.txt       # Python dependencies
├── modules/
│   ├── image_sources.py   # Image source plugins (Wikimedia / Pixabay)
│   └── line_art.py        # Line art generation (OpenCV)
├── templates/
│   └── index.html         # Main page (with two tabs)
└── static/
    ├── css/style.css
    └── js/main.js
```

## Run Locally

Requires Python 3.9+.

```bash
cd kids_art_site
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

## Optional: Configure Pixabay

1. Sign up at https://pixabay.com/api/docs/
2. Set the API key as an environment variable and start:

```bash
export PIXABAY_API_KEY="your_key_here"
export DEFAULT_SOURCE="pixabay"
python app.py
```

## How to Extend

The project is intentionally modular. Adding features only touches a few files:

| Goal | Where to change |
| --- | --- |
| Add a new image source (e.g. Unsplash, Bing Images) | `modules/image_sources.py` — add a class inheriting `ImageSource`, register in the `SOURCES` dict |
| Add a new line art style (e.g. watercolor edges, anime lines) | `modules/line_art.py` — add a new function, branch in `generate_lineart`, register in `AVAILABLE_STYLES` |
| Integrate AI image generation (DALL·E / Stable Diffusion) | Create `modules/ai_image.py`, add a `/api/ai/generate` route, add a new tab in the frontend |
| Add user login, favorites, image uploads | Add Flask-Login + SQLite/SQLAlchemy; create `models.py` and `auth.py` |
| Add print templates (A4 borders, title bars) | Add a post-processing function in `modules/line_art.py` to composite the line art onto a template |

## Deployment Notes

- **Easy hosting**: [Render](https://render.com) / [Railway](https://railway.app) / [Fly.io] — connect a GitHub repo and deploy
- **Production server**: use `gunicorn -w 2 -b 0.0.0.0:8000 app:app` instead of `flask run`
- **Static assets**: currently served by Flask; for larger scale, put Nginx or a CDN in front
- **Image caching**: every request fetches from upstream; consider Redis or local caching later

## Notes

- **Image licensing**: Wikimedia images are mostly public domain or CC-licensed, but licenses vary per image. Pixabay uses a unified Pixabay License. Personal printing is fine, but verify per-image licenses for large-scale distribution.
- **Line art quality**: simple cartoon images, animals, and single objects work best. Complex backgrounds or portraits may produce messy results — this is a limitation of edge detection. For better quality, consider integrating an AI model like Anime2Sketch.
- **Keyword tips**: English keywords work well on Wikimedia. Pixabay supports better non-English search.
