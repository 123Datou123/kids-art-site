/*
  Kids Art Gallery — online coloring tool
  Features:
    • Brush (with size + color)
    • Fill bucket (flood fill, respects black lines)
    • Eraser (paints white)
    • Undo (up to 20 steps)
    • Clear all (preserves line art)
    • Save line art (transparent PNG)
    • Save finished art (PNG with white background)
*/
(function () {
    "use strict";

    // ============ State ============
    const imageUrl = window.COLORING_IMAGE_URL || "";
    const title = window.COLORING_TITLE || "picture";
    const style = window.COLORING_STYLE || "cartoon";

    let canvas, ctx;
    let lineartImage = null;    // The line art with transparent background (as Image)
    let lineartImgData = null;  // Cached ImageData of just the line art (for re-stamping)

    let currentTool = "brush";
    let currentColor = "#ff4d6d";
    let currentSize = 14;
    let drawing = false;
    let lastX = 0, lastY = 0;

    const undoStack = [];
    const MAX_UNDO = 20;

    // ============ Color palette (16 kid-friendly colors) ============
    const COLORS = [
        "#000000", "#7f8c8d", "#c0392b", "#e74c3c",
        "#e67e22", "#f39c12", "#f1c40f", "#fdcb6e",
        "#27ae60", "#2ecc71", "#16a085", "#3498db",
        "#2980b9", "#8e44ad", "#fd79a8", "#ffffff",
    ];

    // ============ Init ============
    function init() {
        canvas = document.getElementById("color-canvas");
        ctx = canvas.getContext("2d", { willReadFrequently: true });

        buildPalette();
        wireUpControls();

        if (!imageUrl) {
            showError("No image was provided. Please go back and pick one.");
            return;
        }

        loadLineart();
    }

    function showError(msg) {
        const loading = document.getElementById("canvas-loading");
        loading.innerHTML = `<p style="color:#d63031">${msg}</p>
            <p><a href="/" style="color:#ff6b9d">← Back to Gallery</a></p>`;
    }

    // ============ Load line art from server ============
    async function loadLineart() {
        try {
            const resp = await fetch("/api/lineart", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: imageUrl,
                    style: style,
                    transparent: true,
                }),
            });
            if (!resp.ok) {
                let err = "Could not load the picture";
                try { const j = await resp.json(); err = j.error || err; } catch (_) { }
                showError(err);
                return;
            }
            const blob = await resp.blob();
            const objectUrl = URL.createObjectURL(blob);

            const img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = () => {
                setupCanvas(img);
                URL.revokeObjectURL(objectUrl);
            };
            img.onerror = () => showError("Failed to render the picture.");
            img.src = objectUrl;

            lineartImage = img;
        } catch (e) {
            showError("Network error: " + e.message);
        }
    }

    function setupCanvas(img) {
        // Resize canvas to fit image, but cap at viewport for performance
        const maxW = Math.min(window.innerWidth - 280, 1400);
        const maxH = Math.min(window.innerHeight - 100, 1400);
        let w = img.naturalWidth, h = img.naturalHeight;
        const scale = Math.min(maxW / w, maxH / h, 1);
        w = Math.round(w * scale);
        h = Math.round(h * scale);

        canvas.width = w;
        canvas.height = h;

        // Fill with white initially so saved art has white bg, not transparent
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        // Draw line art on top
        ctx.drawImage(img, 0, 0, w, h);

        // Cache line art pixels for later use (re-stamp lines after paint behind)
        lineartImgData = ctx.getImageData(0, 0, w, h);

        // Show canvas, hide loader
        document.getElementById("canvas-loading").style.display = "none";
        canvas.style.display = "block";

        // Save initial state for undo
        pushUndo();

        bindCanvasEvents();
    }

    // ============ UI: palette + buttons ============
    function buildPalette() {
        const pal = document.getElementById("color-palette");
        pal.innerHTML = "";
        COLORS.forEach((c, i) => {
            const sw = document.createElement("button");
            sw.className = "swatch";
            sw.style.background = c;
            sw.title = c;
            sw.dataset.color = c;
            if (c === currentColor) sw.classList.add("active");
            sw.addEventListener("click", () => {
                currentColor = c;
                document.querySelectorAll(".swatch").forEach(s => s.classList.remove("active"));
                sw.classList.add("active");
                // Switching color implies brush tool
                if (currentTool === "eraser") setTool("brush");
            });
            pal.appendChild(sw);
        });
    }

    function wireUpControls() {
        // Tool buttons
        document.querySelectorAll(".tool-btn").forEach(btn => {
            btn.addEventListener("click", () => setTool(btn.dataset.tool));
        });
        // Size buttons
        document.querySelectorAll(".size-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                currentSize = parseInt(btn.dataset.size, 10);
                document.querySelectorAll(".size-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });
        // Undo
        document.getElementById("undo-btn").addEventListener("click", undo);
        // Clear (keeps line art, removes colors)
        document.getElementById("clear-btn").addEventListener("click", () => {
            if (!confirm("Clear all your coloring? (Line art will stay)")) return;
            pushUndo();
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(lineartImage, 0, 0, canvas.width, canvas.height);
        });
        // Download line art (just the lines, transparent)
        document.getElementById("download-lineart").addEventListener("click", downloadLineart);
        // Download finished art
        document.getElementById("download-art").addEventListener("click", downloadArt);
    }

    function setTool(tool) {
        currentTool = tool;
        document.querySelectorAll(".tool-btn").forEach(b => {
            b.classList.toggle("active", b.dataset.tool === tool);
        });
        canvas.style.cursor = (tool === "fill") ? "crosshair" : "default";
    }

    // ============ Canvas events ============
    function bindCanvasEvents() {
        canvas.addEventListener("mousedown", onDown);
        canvas.addEventListener("mousemove", onMove);
        canvas.addEventListener("mouseup", onUp);
        canvas.addEventListener("mouseleave", onUp);

        // Touch support for tablets
        canvas.addEventListener("touchstart", onTouch, { passive: false });
        canvas.addEventListener("touchmove", onTouch, { passive: false });
        canvas.addEventListener("touchend", onUp);
    }

    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        const sx = canvas.width / rect.width;
        const sy = canvas.height / rect.height;
        return {
            x: (e.clientX - rect.left) * sx,
            y: (e.clientY - rect.top) * sy,
        };
    }

    function onDown(e) {
        const { x, y } = getPos(e);
        if (currentTool === "fill") {
            pushUndo();
            floodFill(Math.floor(x), Math.floor(y), currentColor);
            return;
        }
        drawing = true;
        pushUndo();
        lastX = x; lastY = y;
        // Single tap = single dot
        stamp(x, y);
    }
    function onMove(e) {
        if (!drawing) return;
        const { x, y } = getPos(e);
        drawLine(lastX, lastY, x, y);
        lastX = x; lastY = y;
    }
    function onUp() {
        if (drawing) {
            drawing = false;
            // After painting, re-stamp the line art on top so we don't paint over the lines
            restampLineart();
        }
    }
    function onTouch(e) {
        e.preventDefault();
        const t = e.touches[0];
        if (!t) { onUp(); return; }
        const fake = { clientX: t.clientX, clientY: t.clientY };
        if (e.type === "touchstart") onDown(fake);
        else if (e.type === "touchmove") onMove(fake);
    }

    function stamp(x, y) {
        ctx.fillStyle = (currentTool === "eraser") ? "#ffffff" : currentColor;
        ctx.beginPath();
        ctx.arc(x, y, currentSize / 2, 0, Math.PI * 2);
        ctx.fill();
    }
    function drawLine(x1, y1, x2, y2) {
        ctx.strokeStyle = (currentTool === "eraser") ? "#ffffff" : currentColor;
        ctx.lineWidth = currentSize;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
    }

    /**
     * After freehand painting, the user may have painted over the black lines.
     * Re-draw the line art on top so the lines always stay visible.
     */
    function restampLineart() {
        if (!lineartImage) return;
        ctx.drawImage(lineartImage, 0, 0, canvas.width, canvas.height);
    }

    // ============ Flood fill (paint bucket) ============
    function floodFill(startX, startY, hexColor) {
        const w = canvas.width, h = canvas.height;
        if (startX < 0 || startX >= w || startY < 0 || startY >= h) return;

        const target = hexToRgb(hexColor);
        const imgData = ctx.getImageData(0, 0, w, h);
        const data = imgData.data;
        const startIdx = (startY * w + startX) * 4;

        // Read starting pixel
        const sr = data[startIdx], sg = data[startIdx + 1], sb = data[startIdx + 2];

        // Don't fill black lines
        if (isLinePixel(sr, sg, sb)) return;
        // Don't fill if already the same color
        if (sr === target.r && sg === target.g && sb === target.b) return;

        // Stack-based 4-connected flood fill
        const stack = [[startX, startY]];
        const visited = new Uint8Array(w * h);
        const tol = 32;  // color match tolerance

        while (stack.length) {
            const [cx, cy] = stack.pop();
            if (cx < 0 || cx >= w || cy < 0 || cy >= h) continue;
            const flatIdx = cy * w + cx;
            if (visited[flatIdx]) continue;
            visited[flatIdx] = 1;
            const i = flatIdx * 4;
            const r = data[i], g = data[i + 1], b = data[i + 2];
            if (isLinePixel(r, g, b)) continue;
            if (!colorMatch(r, g, b, sr, sg, sb, tol)) continue;
            // Fill this pixel
            data[i] = target.r;
            data[i + 1] = target.g;
            data[i + 2] = target.b;
            data[i + 3] = 255;
            stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
        }
        ctx.putImageData(imgData, 0, 0);
        // Lines are part of the pixel data, so they're preserved automatically
    }

    function isLinePixel(r, g, b) {
        // Treat very dark pixels as line art
        return (r + g + b) / 3 < 80;
    }
    function colorMatch(r, g, b, tr, tg, tb, tol) {
        return Math.abs(r - tr) <= tol &&
            Math.abs(g - tg) <= tol &&
            Math.abs(b - tb) <= tol;
    }
    function hexToRgb(hex) {
        const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return m ? {
            r: parseInt(m[1], 16),
            g: parseInt(m[2], 16),
            b: parseInt(m[3], 16),
        } : { r: 0, g: 0, b: 0 };
    }

    // ============ Undo ============
    function pushUndo() {
        try {
            const snap = ctx.getImageData(0, 0, canvas.width, canvas.height);
            undoStack.push(snap);
            if (undoStack.length > MAX_UNDO) undoStack.shift();
        } catch (e) {
            console.error("Snapshot failed", e);
        }
    }
    function undo() {
        if (undoStack.length <= 1) return;
        undoStack.pop();  // discard current state
        const prev = undoStack[undoStack.length - 1];
        ctx.putImageData(prev, 0, 0);
    }

    // ============ Download ============
    function downloadArt() {
        // Canvas already has white bg + colors + lines on top — perfect for printing
        canvas.toBlob(blob => {
            triggerDownload(blob, `my_art_${sanitize(title)}.png`);
        }, "image/png");
    }
    function downloadLineart() {
        // Render line art on white background and save (for printing blank)
        const off = document.createElement("canvas");
        off.width = canvas.width;
        off.height = canvas.height;
        const octx = off.getContext("2d");
        octx.fillStyle = "#ffffff";
        octx.fillRect(0, 0, off.width, off.height);
        if (lineartImage) octx.drawImage(lineartImage, 0, 0, off.width, off.height);
        off.toBlob(blob => {
            triggerDownload(blob, `lineart_${sanitize(title)}.png`);
        }, "image/png");
    }
    function triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    }
    function sanitize(name) {
        return String(name).replace(/[\\/:*?"<>|\s]/g, "_").substring(0, 40) || "picture";
    }

    // ============ Boot ============
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
