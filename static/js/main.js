/* Kids Art Gallery — Home page script (v2) */
(function () {
    "use strict";

    // ============ DOM ============
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");

    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const sourceSelect = document.getElementById("source-select");
    const statusEl = document.getElementById("status");
    const grid = document.getElementById("results-grid");
    const loadMoreWrap = document.getElementById("load-more-wrap");
    const loadMoreBtn = document.getElementById("load-more-btn");

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
    const modalColor = document.getElementById("modal-color-online");

    // ============ State (for pagination) ============
    let currentQuery = "";
    let currentSource = "";
    let currentPage = 1;
    let currentSourceImageUrl = null;
    let currentSourceImageTitle = "";
    let currentLineartBlobUrl = null;

    // ============ Tab switching ============
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.toggle("active", b === btn));
            tabPanels.forEach(p => p.classList.toggle("active", p.id === "tab-" + target));
        });
    });

    // ============ Image search ============
    async function doSearch(append = false) {
        if (!append) {
            // New search
            currentQuery = searchInput.value.trim();
            currentSource = sourceSelect.value;
            currentPage = 1;
            grid.innerHTML = "";
            hideLoadMore();
            if (!currentQuery) {
                setStatus("Please enter a search term", true);
                return;
            }
            setStatus("Searching...");
        } else {
            currentPage++;
            loadMoreBtn.disabled = true;
            loadMoreBtn.textContent = "Loading...";
        }

        const params = new URLSearchParams({
            q: currentQuery,
            source: currentSource,
            count: 18,
            page: currentPage,
        });

        try {
            const resp = await fetch("/api/search?" + params.toString());
            const data = await resp.json();
            if (!resp.ok) {
                setStatus(data.error || "Search failed", true);
                return;
            }
            if (data.images.length === 0) {
                if (!append) {
                    setStatus(`No results for "${currentQuery}". Try a different keyword.`, true);
                }
                hideLoadMore();
                return;
            }
            if (!append) {
                setStatus(`Showing ${data.count} images`);
            } else {
                setStatus(`Showing ${grid.children.length + data.images.length} images`);
            }
            appendResults(data.images);

            if (data.has_more) {
                showLoadMore();
            } else {
                hideLoadMore();
            }
        } catch (e) {
            setStatus("Network error: " + e.message, true);
        } finally {
            loadMoreBtn.disabled = false;
            loadMoreBtn.textContent = "Load More";
        }
    }

    function setStatus(msg, isError) {
        statusEl.textContent = msg;
        statusEl.classList.toggle("error", !!isError);
    }
    function showLoadMore() {
        loadMoreWrap.style.display = "flex";
    }
    function hideLoadMore() {
        loadMoreWrap.style.display = "none";
    }

    function appendResults(images) {
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
                        <button class="btn-download" data-action="download">💾 Download</button>
                        <button class="btn-color" data-action="color">🎨 Color it!</button>
                    </div>
                    <button class="btn-text-link" data-action="lineart">Preview line art →</button>
                </div>
            `;
            card.querySelector('[data-action="download"]').addEventListener("click", () => {
                downloadOriginal(img);
            });
            card.querySelector('[data-action="color"]').addEventListener("click", () => {
                openColorPage(img);
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
        window.location.href = dl;
    }

    function openColorPage(img, style) {
        const url = img.full_url || img.thumb_url;
        const title = img.title || "picture";
        const params = { url: url, title: title };
        if (style) params.style = style;
        const dest = "/color?" + new URLSearchParams(params).toString();
        window.location.href = dest;
    }

    // ============ Line art preview modal ============
    function openLineartModal(img) {
        const url = img.full_url || img.thumb_url;
        currentSourceImageUrl = url;
        currentSourceImageTitle = img.title || "picture";
        modalStyle.value = "cartoon";
        modal.classList.remove("hidden");
        requestLineart(url, modalStyle.value);
    }
    function closeModal() {
        modal.classList.add("hidden");
        modalImg.style.display = "none";
        modalLoading.style.display = "block";
        modalLoading.innerHTML = '<div class="spinner"></div><p>Generating coloring page...</p>';
        if (currentLineartBlobUrl) {
            URL.revokeObjectURL(currentLineartBlobUrl);
            currentLineartBlobUrl = null;
        }
        currentSourceImageUrl = null;
    }
    async function requestLineart(url, style) {
        modalImg.style.display = "none";
        modalLoading.style.display = "block";
        modalLoading.innerHTML = '<div class="spinner"></div><p>Generating coloring page...</p>';

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
    modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
    modalRegenerate.addEventListener("click", () => {
        if (currentSourceImageUrl) requestLineart(currentSourceImageUrl, modalStyle.value);
    });
    modalStyle.addEventListener("change", () => {
        if (currentSourceImageUrl) requestLineart(currentSourceImageUrl, modalStyle.value);
    });
    modalDownload.addEventListener("click", () => {
        if (!currentLineartBlobUrl) return;
        const a = document.createElement("a");
        a.href = currentLineartBlobUrl;
        a.download = "coloring_page.png";
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
    });
    modalColor.addEventListener("click", () => {
        if (!currentSourceImageUrl) return;
        const dest = "/color?" + new URLSearchParams({
            url: currentSourceImageUrl,
            title: currentSourceImageTitle,
            style: modalStyle.value,    // ← 把弹窗里选的 style 带过去
        }).toString();
        window.location.href = dest;
    });

    // ============ Text → coloring page ============
    async function generateFromText() {
        const query = genInput.value.trim();
        if (!query) {
            setGenStatus("Please enter what you want to draw", true);
            return;
        }

        setGenStatus("Finding a matching image...");
        genResult.classList.remove("has-content");
        genResult.innerHTML = "";

        try {
            // Step 1: find the source image
            const findResp = await fetch("/api/lineart/find", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query, source: genSource.value }),
            });
            const findData = await findResp.json();
            if (!findResp.ok) {
                setGenStatus(findData.error || "Search failed", true);
                return;
            }

            // Step 2: generate preview line art
            setGenStatus("Generating line art preview...");
            const resp = await fetch("/api/lineart", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: findData.url, style: genStyle.value,
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
            img.alt = "Generated line art";

            const row = document.createElement("div");
            row.className = "download-row";

            const colorBtn = document.createElement("button");
            colorBtn.textContent = "🎨 Color it Online!";
            colorBtn.className = "primary";
            colorBtn.addEventListener("click", () => {
                window.location.href = "/color?" + new URLSearchParams({
                    url: findData.url,
                    title: findData.title || query,
                    style: genStyle.value,    // ← 带上 Text 生成 Tab 里选的 style
                }).toString();
            });

            const dlBtn = document.createElement("button");
            dlBtn.textContent = "💾 Download Line Art";
            dlBtn.addEventListener("click", () => {
                const a = document.createElement("a");
                a.href = blobUrl;
                a.download = `lineart_${sanitizeFilename(query)}.png`;
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
            });

            const regenBtn = document.createElement("button");
            regenBtn.textContent = "🎲 Try Another";
            regenBtn.addEventListener("click", generateFromText);

            row.appendChild(regenBtn);
            row.appendChild(dlBtn);
            row.appendChild(colorBtn);

            const note = document.createElement("p");
            note.className = "source-note";
            note.textContent = "Generated from the first matching image. Try a different keyword for variety.";

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

    // ============ Utils ============
    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        })[c]);
    }
    function escapeAttr(s) { return escapeHtml(s); }
    function sanitizeFilename(name) {
        return String(name).replace(/[\\/:*?"<>|]/g, "_").substring(0, 60).trim() || "image";
    }

    // ============ Bind ============
    searchBtn.addEventListener("click", () => doSearch(false));
    searchInput.addEventListener("keydown", e => { if (e.key === "Enter") doSearch(false); });
    loadMoreBtn.addEventListener("click", () => doSearch(true));

    genBtn.addEventListener("click", generateFromText);
    genInput.addEventListener("keydown", e => { if (e.key === "Enter") generateFromText(); });
})();
