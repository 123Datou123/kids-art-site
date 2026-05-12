/* Kids Art Gallery — Frontend script */
(function () {
    "use strict";

    // ============ DOM references ============
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");

    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const sourceSelect = document.getElementById("source-select");
    const statusEl = document.getElementById("status");
    const grid = document.getElementById("results-grid");

    const genInput = document.getElementById("gen-input");
    const genBtn = document.getElementById("gen-btn");
    const genStyle = document.getElementById("gen-style");
    const genSource = document.getElementById("gen-source");
    const genStatus = document.getElementById("gen-status");
    const genResult = document.getElementById("gen-result");

    const modal = document.getElementById("lineart-modal");
    const modalClose = document.getElementById("modal-close");
    const modalImg = document.getElementById("lineart-img");
    const modalLoading = document.getElementById("modal-loading");
    const modalStyle = document.getElementById("modal-style");
    const modalRegenerate = document.getElementById("modal-regenerate");
    const modalDownload = document.getElementById("modal-download");

    // Current source image URL in modal (used when switching style triggers regeneration)
    let currentSourceImageUrl = null;
    // Current coloring page blob URL in modal (used for download)
    let currentLineartBlobUrl = null;

    // ============ Tab switching ============
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.toggle("active", b === btn));
            tabPanels.forEach(p => {
                p.classList.toggle("active", p.id === "tab-" + target);
            });
        });
    });

    // ============ Image search ============
    async function doSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            setStatus("Please enter a search term", true);
            return;
        }

        setStatus("Searching...");
        grid.innerHTML = "";

        const params = new URLSearchParams({
            q: query,
            source: sourceSelect.value,
            count: 18,
        });

        try {
            const resp = await fetch("/api/search?" + params.toString());
            const data = await resp.json();
            if (!resp.ok) {
                setStatus(data.error || "Search failed", true);
                return;
            }
            if (data.images.length === 0) {
                setStatus(`No results for "${query}". Try a different keyword.`, true);
                return;
            }
            setStatus(`Found ${data.count} images`);
            renderResults(data.images);
        } catch (e) {
            setStatus("Network error: " + e.message, true);
        }
    }

    function setStatus(msg, isError) {
        statusEl.textContent = msg;
        statusEl.classList.toggle("error", !!isError);
    }

    function renderResults(images) {
        grid.innerHTML = "";
        const frag = document.createDocumentFragment();
        images.forEach(img => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img loading="lazy" src="${escapeAttr(img.thumb_url)}" alt="${escapeAttr(img.title)}">
                </div>
                <div class="card-body">
                    <div class="card-title">${escapeHtml(img.title || "Untitled")}</div>
                    <div class="card-actions">
                        <button class="btn-download" data-action="download">Download</button>
                        <button class="btn-lineart" data-action="lineart">To Line Art</button>
                    </div>
                </div>
            `;
            card.querySelector('[data-action="download"]').addEventListener("click", () => {
                downloadOriginal(img);
            });
            card.querySelector('[data-action="lineart"]').addEventListener("click", () => {
                openLineartModal(img);
            });
            frag.appendChild(card);
        });
        grid.appendChild(frag);
    }

    function downloadOriginal(img) {
        const url = img.full_url || img.thumb_url;
        const filename = sanitizeFilename(img.title || "image") + ".jpg";
        const dl = "/api/download?" +
            new URLSearchParams({ url: url, filename: filename }).toString();
        // Trigger download by navigation
        window.location.href = dl;
    }

    // ============ Line art modal ============
    function openLineartModal(img) {
        const url = img.full_url || img.thumb_url;
        currentSourceImageUrl = url;
        modalStyle.value = "cartoon";
        modal.classList.remove("hidden");
        requestLineart(url, modalStyle.value);
    }

    function closeModal() {
        modal.classList.add("hidden");
        modalImg.style.display = "none";
        modalLoading.style.display = "block";
        if (currentLineartBlobUrl) {
            URL.revokeObjectURL(currentLineartBlobUrl);
            currentLineartBlobUrl = null;
        }
        currentSourceImageUrl = null;
    }

    async function requestLineart(url, style) {
        modalImg.style.display = "none";
        modalLoading.style.display = "block";
        modalLoading.innerHTML = '<div class="spinner"></div><p>Generating coloring page, please wait...</p>';

        try {
            const resp = await fetch("/api/lineart", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: url, style: style }),
            });
            if (!resp.ok) {
                let err = "Generation failed";
                try { const j = await resp.json(); err = j.error || err; } catch (_) { }
                modalLoading.innerHTML = `<p style="color:#d63031">${escapeHtml(err)}</p>`;
                return;
            }
            const blob = await resp.blob();
            if (currentLineartBlobUrl) URL.revokeObjectURL(currentLineartBlobUrl);
            currentLineartBlobUrl = URL.createObjectURL(blob);
            modalImg.src = currentLineartBlobUrl;
            modalImg.style.display = "block";
            modalLoading.style.display = "none";
        } catch (e) {
            modalLoading.innerHTML = `<p style="color:#d63031">Network error: ${escapeHtml(e.message)}</p>`;
        }
    }

    modalClose.addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    modalRegenerate.addEventListener("click", () => {
        if (currentSourceImageUrl) {
            requestLineart(currentSourceImageUrl, modalStyle.value);
        }
    });
    modalStyle.addEventListener("change", () => {
        if (currentSourceImageUrl) {
            requestLineart(currentSourceImageUrl, modalStyle.value);
        }
    });

    modalDownload.addEventListener("click", () => {
        if (!currentLineartBlobUrl) return;
        const a = document.createElement("a");
        a.href = currentLineartBlobUrl;
        a.download = "coloring_page.png";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });

    // ============ Text → Coloring page ============
    async function generateFromText() {
        const query = genInput.value.trim();
        if (!query) {
            setGenStatus("Please enter what you want to draw", true);
            return;
        }

        setGenStatus("Searching and generating...");
        genResult.classList.remove("has-content");
        genResult.innerHTML = "";

        try {
            const resp = await fetch("/api/lineart/from-text", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    query: query,
                    style: genStyle.value,
                    source: genSource.value,
                }),
            });
            if (!resp.ok) {
                let err = "Generation failed";
                try { const j = await resp.json(); err = j.error || err; } catch (_) { }
                setGenStatus(err, true);
                return;
            }
            const blob = await resp.blob();
            const blobUrl = URL.createObjectURL(blob);

            const img = document.createElement("img");
            img.src = blobUrl;
            img.alt = "Generated coloring page";

            const row = document.createElement("div");
            row.className = "download-row";
            const dlBtn = document.createElement("button");
            dlBtn.textContent = "💾 Download";
            dlBtn.className = "primary";
            dlBtn.addEventListener("click", () => {
                const a = document.createElement("a");
                a.href = blobUrl;
                a.download = `coloring_${sanitizeFilename(query)}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
            const regenBtn = document.createElement("button");
            regenBtn.textContent = "🎲 Try Another";
            regenBtn.addEventListener("click", generateFromText);
            row.appendChild(regenBtn);
            row.appendChild(dlBtn);

            const note = document.createElement("p");
            note.className = "source-note";
            note.textContent = "Generated from the first matching image. Click 'Try Another' for a new result, or pick manually from the Search tab.";

            genResult.appendChild(img);
            genResult.appendChild(row);
            genResult.appendChild(note);
            genResult.classList.add("has-content");
            setGenStatus("Done ✅");
        } catch (e) {
            setGenStatus("Network error: " + e.message, true);
        }
    }

    function setGenStatus(msg, isError) {
        genStatus.textContent = msg;
        genStatus.classList.toggle("error", !!isError);
    }

    // ============ Utilities ============
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        })[c]);
    }
    function escapeAttr(str) { return escapeHtml(str); }
    function sanitizeFilename(name) {
        return String(name).replace(/[\\/:*?"<>|]/g, "_").substring(0, 60).trim() || "image";
    }

    // ============ Event bindings ============
    searchBtn.addEventListener("click", doSearch);
    searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") doSearch();
    });

    genBtn.addEventListener("click", generateFromText);
    genInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") generateFromText();
    });
})();
