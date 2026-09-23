// PDF-Engine Enterprise Frontend Application
document.addEventListener("DOMContentLoaded", () => {
  // State
  let currentDoc = null;
  let activePageNum = 1;
  let activeHighlightQuery = "";
  let targetFields = [
    "Número de Factura",
    "Proveedor Autorizado",
    "NIT",
    "Fecha de Emisión",
    "Valor Total a Pagar",
    "Responsable"
  ];
  let lastAIResult = null;
  let matchedPages = new Set();

  // DOM Elements
  const btnUploadTrigger = document.getElementById("btn-upload-trigger");
  const fileInput = document.getElementById("file-input");
  const btnLoadSample = document.getElementById("btn-load-sample");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingTitle = document.getElementById("loading-title");
  const loadingDesc = document.getElementById("loading-desc");

  // Theme elements
  const btnThemeToggle = document.getElementById("btn-theme-toggle");
  const themeIcon = document.getElementById("theme-icon");
  const themeText = document.getElementById("theme-text");

  // KPI elements
  const kpiTotalTime = document.getElementById("kpi-total-time");
  const kpiPagesSec = document.getElementById("kpi-pages-sec");
  const kpiTotalPages = document.getElementById("kpi-total-pages");
  const kpiDocName = document.getElementById("kpi-doc-name");
  const kpiOcrTime = document.getElementById("kpi-ocr-time");
  const kpiOcrCount = document.getElementById("kpi-ocr-count");
  const kpiAiTime = document.getElementById("kpi-ai-time");
  const kpiAiModel = document.getElementById("kpi-ai-model");

  // Search elements
  const searchInput = document.getElementById("search-input");
  const btnSearch = document.getElementById("btn-search");
  const searchStatusText = document.getElementById("search-status-text");
  const searchLatencyBadge = document.getElementById("search-latency-badge");
  const tabSearchCount = document.getElementById("tab-search-count");
  const searchResultsList = document.getElementById("search-results-list");

  // Page List & Viewer
  const pageList = document.getElementById("page-list");
  const pageCountBadge = document.getElementById("page-count-badge");
  const viewerImg = document.getElementById("viewer-img");
  const viewerPageLabel = document.getElementById("viewer-page-label");
  const viewerHighlightBadge = document.getElementById("viewer-highlight-badge");
  const btnClearHighlights = document.getElementById("btn-clear-highlights");
  const btnPrevPage = document.getElementById("btn-prev-page");
  const btnNextPage = document.getElementById("btn-next-page");

  // AI Extractor Elements
  const fieldTagsContainer = document.getElementById("field-tags-container");
  const newFieldInput = document.getElementById("new-field-input");
  const btnAddField = document.getElementById("btn-add-field");
  const selectAiModel = document.getElementById("select-ai-model");
  const btnRunAi = document.getElementById("btn-run-ai");
  const btnCopyJson = document.getElementById("btn-copy-json");
  const aiResultsTbody = document.getElementById("ai-results-tbody");
  const aiTelemetryBadge = document.getElementById("ai-telemetry-badge");

  // Gallery
  const galleryContainer = document.getElementById("gallery-container");

  // Tabs
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  // 1. Theme Management (Dark Mode / Light Mode)
  function initTheme() {
    const savedTheme = localStorage.getItem("pdf_engine_theme") || "light";
    applyTheme(savedTheme);
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
      if (themeIcon) themeIcon.textContent = "☀️";
      if (themeText) themeText.textContent = "Modo Claro";
    } else {
      document.documentElement.removeAttribute("data-theme");
      if (themeIcon) themeIcon.textContent = "🌙";
      if (themeText) themeText.textContent = "Modo Oscuro";
    }
    localStorage.setItem("pdf_engine_theme", theme);
  }

  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(currentTheme === "dark" ? "light" : "dark");
    });
  }

  initTheme();
  renderFieldTags();
  checkSystemStatus();

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.style.display = "none");

      btn.classList.add("active");
      const activeContent = document.getElementById(tabId);
      if (activeContent) activeContent.style.display = "block";
    });
  });

  function switchTab(tabId) {
    tabBtns.forEach(b => {
      if (b.getAttribute("data-tab") === tabId) b.classList.add("active");
      else b.classList.remove("active");
    });
    tabContents.forEach(c => {
      c.style.display = (c.id === tabId) ? "block" : "none";
    });
  }

  // Check system status
  async function checkSystemStatus() {
    try {
      const res = await fetch("/api/system-status");
      if (res.ok) {
        const data = await res.json();
        const label = document.getElementById("system-status-label");
        label.textContent = `AMD Ryzen (12 Hilos) • Tesseract 5.x • ${data.default_model || 'Ollama Listo'}`;
      }
    } catch (err) {
      console.warn("Status check error", err);
    }
  }

  // Loaders
  function showLoader(title, desc) {
    loadingTitle.textContent = title;
    loadingDesc.textContent = desc;
    loadingOverlay.style.display = "flex";
  }

  function hideLoader() {
    loadingOverlay.style.display = "none";
  }

  // Upload handler
  btnUploadTrigger.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    showLoader("Procesando PDF a Alta Velocidad...", "Ejecutando lectura híbrida y OCR paralelo multihilo en 12 hilos...");

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.success) {
        handleDocumentLoaded(data);
      } else {
        alert("Error al procesar PDF: " + (data.detail || "Error desconocido"));
      }
    } catch (err) {
      alert("Error de red al subir el documento: " + err.message);
    } finally {
      hideLoader();
      fileInput.value = "";
    }
  });

  // Load sample benchmark handler
  btnLoadSample.addEventListener("click", async () => {
    showLoader("Cargando Benchmark Oficial (20 Páginas)...", "Procesando 20 páginas con texto, fotos y escaneos de prueba...");
    try {
      const res = await fetch("/api/load-sample", { method: "POST" });
      const data = await res.json();
      if (res.ok && data.success) {
        handleDocumentLoaded(data);
      } else {
        alert("Error cargando benchmark: " + (data.detail || "Error"));
      }
    } catch (err) {
      alert("Error al cargar benchmark: " + err.message);
    } finally {
      hideLoader();
    }
  });

  // AugLy Generator Modal Elements
  const btnOpenGenerator = document.getElementById("btn-open-generator");
  const generatorModal = document.getElementById("generator-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnCancelGen = document.getElementById("btn-cancel-gen");
  const btnSubmitGen = document.getElementById("btn-submit-gen");
  const generatorResultBox = document.getElementById("generator-result-box");
  const genResultMeta = document.getElementById("gen-result-meta");
  const btnScanNow = document.getElementById("btn-scan-now");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");

  const genPages = document.getElementById("gen-pages");
  const genImages = document.getElementById("gen-images");
  const genDensity = document.getElementById("gen-density");
  const genDegradation = document.getElementById("gen-degradation");
  const genKeywords = document.getElementById("gen-keywords");

  let lastGeneratedDoc = null;

  if (btnOpenGenerator) {
    btnOpenGenerator.addEventListener("click", () => {
      if (generatorResultBox) generatorResultBox.style.display = "none";
      if (generatorModal) generatorModal.style.display = "flex";
    });
  }

  function closeGeneratorModal() {
    if (generatorModal) generatorModal.style.display = "none";
  }

  if (btnCloseModal) btnCloseModal.addEventListener("click", closeGeneratorModal);
  if (btnCancelGen) btnCancelGen.addEventListener("click", closeGeneratorModal);

  // Submit Generation
  if (btnSubmitGen) {
    btnSubmitGen.addEventListener("click", async () => {
      const pages = parseInt(genPages.value) || 20;
      const images = parseInt(genImages.value) || 4;
      const density = genDensity.value;
      const degradation = genDegradation.value;
      const keywords = genKeywords.value.trim();

      btnSubmitGen.disabled = true;
      btnSubmitGen.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></span> Generando...`;

      try {
        const res = await fetch("/api/generate-random-pdf", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pages: pages,
            images_count: images,
            text_density: density,
            degradation: degradation,
            keywords: keywords
          })
        });

        const data = await res.json();
        if (res.ok && data.success) {
          lastGeneratedDoc = data;

          let kwSummary = (data.injected_keywords || []).map(k => `<b>${k.term}</b> (pág. ${k.page} en ${k.location})`).join("<br>• ");

          genResultMeta.innerHTML = `
            <div><b>Archivo:</b> ${data.filename} (${data.file_size_kb} KB)</div>
            <div><b>Estructura:</b> ${data.total_pages} páginas, ${data.images_count} imágenes con aumento AugLy (${data.degradation})</div>
            <div style="margin-top: 6px;"><b>Palabras Clave Inyectadas para Búsqueda:</b><br>• ${kwSummary || 'Ninguna'}</div>
          `;

          if (btnDownloadPdf) {
            btnDownloadPdf.href = `/api/download-generated/${data.filename}`;
          }

          generatorResultBox.style.display = "block";
        } else {
          alert("Error generando PDF: " + (data.detail || "Error desconocido"));
        }
      } catch (err) {
        alert("Error de red al generar: " + err.message);
      } finally {
        btnSubmitGen.disabled = false;
        btnSubmitGen.innerHTML = `<svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Generar PDF con AugLy`;
      }
    });
  }

  // Scan Generated PDF Immediately
  if (btnScanNow) {
    btnScanNow.addEventListener("click", async () => {
      if (!lastGeneratedDoc || !lastGeneratedDoc.file_path) {
        alert("No hay documento generado disponible.");
        return;
      }

      closeGeneratorModal();
      showLoader("Escaneando Documento Generado (AugLy)...", "Ejecutando lectura híbrida y OCR paralelo multihilo...");

      try {
        const res = await fetch("/api/scan-generated-pdf", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ file_path: lastGeneratedDoc.file_path })
        });

        const data = await res.json();
        if (res.ok && data.success) {
          handleDocumentLoaded(data);

          // If keywords were injected, automatically trigger search with the first token
          if (lastGeneratedDoc.injected_keywords && lastGeneratedDoc.injected_keywords.length > 0) {
            const firstKw = lastGeneratedDoc.injected_keywords[0].term;
            searchInput.value = firstKw;
            performSearch();
          }
        } else {
          alert("Error al escanear documento: " + (data.detail || "Error"));
        }
      } catch (err) {
        alert("Error al escanear: " + err.message);
      } finally {
        hideLoader();
      }
    });
  }

  // Handle Document Loaded
  function handleDocumentLoaded(data) {
    currentDoc = data;
    activePageNum = 1;
    activeHighlightQuery = "";
    matchedPages.clear();

    // KPIs
    const metrics = data.metrics || {};
    kpiTotalTime.textContent = `${metrics.total_seconds || '--'} s`;
    kpiPagesSec.textContent = `${metrics.pages_per_second || '0'} páginas / seg`;
    kpiTotalPages.textContent = data.total_pages;
    kpiDocName.textContent = data.filename;

    const breakdown = metrics.breakdown || {};
    const ocrTime = breakdown.parallel_ocr || 0;
    kpiOcrTime.textContent = `${ocrTime} s`;
    kpiOcrCount.textContent = `${data.ocr_items_processed || 0} elementos procesados`;

    pageCountBadge.textContent = `${data.total_pages} Págs`;

    renderPageList();
    loadPagePreview(1);
    renderGallery();

    // Reset search
    searchInput.value = "";
    searchStatusText.textContent = `Documento cargado (${data.total_pages} páginas). Listo para buscar.`;
    searchLatencyBadge.textContent = "";
    tabSearchCount.textContent = "0";
    searchResultsList.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">Ingresa una o más palabras para buscar.</div>';
  }

  // Render Page List in left sidebar
  function renderPageList() {
    if (!currentDoc) return;
    pageList.innerHTML = "";

    currentDoc.pages.forEach(p => {
      const item = document.createElement("div");
      item.className = `page-item ${p.page === activePageNum ? 'active' : ''}`;
      item.id = `page-item-${p.page}`;

      let tagHtml = "";
      if (p.is_scanned) {
        tagHtml = '<span class="page-tag tag-scanned">Escaneo OCR</span>';
      } else {
        tagHtml = '<span class="page-tag tag-digital">Digital</span>';
      }

      if (matchedPages.has(p.page)) {
        tagHtml += ' <span class="page-tag tag-match">Coincidencia</span>';
      }

      const imgCount = p.images ? p.images.length : 0;
      const imgMeta = imgCount > 0 ? ` • ${imgCount} img` : '';

      item.innerHTML = `
        <div class="page-item-info">
          <span class="page-item-title">Página ${p.page}</span>
          <span class="page-item-meta">${p.is_scanned ? 'Sin texto nativo' : 'Texto digital'}${imgMeta}</span>
        </div>
        <div>${tagHtml}</div>
      `;

      item.addEventListener("click", () => {
        loadPagePreview(p.page, activeHighlightQuery);
        switchTab("tab-viewer");
      });

      pageList.appendChild(item);
    });
  }

  // Load Page Preview in viewer tab with optional visual highlighting
  function loadPagePreview(pageNum, highlightQuery = null) {
    if (!currentDoc) return;
    activePageNum = pageNum;
    viewerPageLabel.textContent = `Página ${pageNum} de ${currentDoc.total_pages}`;

    let url = `/api/page-preview/${pageNum}?t=${Date.now()}`;
    if (highlightQuery && highlightQuery.trim()) {
      url += `&highlight=${encodeURIComponent(highlightQuery.trim())}`;
      viewerHighlightBadge.style.display = "inline-flex";
      btnClearHighlights.style.display = "inline-flex";
    } else {
      viewerHighlightBadge.style.display = "none";
      btnClearHighlights.style.display = "none";
    }

    viewerImg.src = url;

    // Update active highlight in page list
    document.querySelectorAll(".page-item").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`page-item-${pageNum}`);
    if (activeEl) {
      activeEl.classList.add("active");
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  btnClearHighlights.addEventListener("click", () => {
    activeHighlightQuery = "";
    loadPagePreview(activePageNum, "");
  });

  btnPrevPage.addEventListener("click", () => {
    if (currentDoc && activePageNum > 1) {
      loadPagePreview(activePageNum - 1, activeHighlightQuery);
    }
  });

  btnNextPage.addEventListener("click", () => {
    if (currentDoc && activePageNum < currentDoc.total_pages) {
      loadPagePreview(activePageNum + 1, activeHighlightQuery);
    }
  });

  // Render Image Gallery
  function renderGallery() {
    if (!currentDoc) return;
    galleryContainer.innerHTML = "";

    let totalImages = 0;
    currentDoc.pages.forEach(p => {
      (p.images || []).forEach(img => {
        totalImages++;
        const card = document.createElement("div");
        card.className = "gallery-card";
        
        card.innerHTML = `
          <img src="/api/extracted-image/${img.id}" alt="${img.id}" loading="lazy">
          <div class="gallery-card-body">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 600; font-size: 13px;">${img.id}</span>
              <span style="font-size: 11px; color: var(--text-muted);">Pág. ${img.page} • ${img.width}x${img.height}</span>
            </div>
            <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Texto OCR Recuperado:</div>
            <div class="gallery-ocr-box">${img.ocr_text || '<em style="color: #94a3b8;">Sin texto detectable en imagen</em>'}</div>
          </div>
        `;
        galleryContainer.appendChild(card);
      });
    });

    if (totalImages === 0) {
      galleryContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No se detectaron imágenes embebidas en este documento.</div>';
    }
  }

  // Search Logic with Disjoint Multi-Token Support
  async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
      matchedPages.clear();
      activeHighlightQuery = "";
      renderPageList();
      if (activePageNum) loadPagePreview(activePageNum, "");
      searchStatusText.textContent = "Ingresa uno o varios términos para buscar.";
      searchLatencyBadge.textContent = "";
      tabSearchCount.textContent = "0";
      searchResultsList.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No hay búsquedas activas.</div>';
      return;
    }

    if (!currentDoc) {
      alert("Por favor carga un documento PDF primero.");
      return;
    }

    searchStatusText.textContent = `Buscando términos de "${query}"...`;

    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      });
      const data = await res.json();

      matchedPages = new Set(data.matched_pages || []);
      activeHighlightQuery = query;
      renderPageList();

      tabSearchCount.textContent = data.total_matches;
      const tokensSearched = (data.tokens || []).join(", ");
      searchStatusText.textContent = `${data.total_matches} coincidencia(s) en ${data.matched_pages.length} página(s) [Términos: ${tokensSearched || query}].`;
      searchLatencyBadge.textContent = `⚡ ${data.search_latency_ms} ms`;

      // Render search tab results
      if (data.results.length === 0) {
        searchResultsList.innerHTML = `<div style="color: var(--text-muted); padding: 16px;">No se encontraron coincidencias para los términos ingresados.</div>`;
      } else {
        searchResultsList.innerHTML = "";
        data.results.forEach(item => {
          const card = document.createElement("div");
          card.className = "snippet-card";

          // Highlight matching term in snippet
          const termToHighlight = item.token_searched || item.matched_term || query;
          const regex = new RegExp(`(${termToHighlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
          const highlightedSnippet = item.snippet.replace(regex, '<span class="highlight-match">$1</span>');

          card.innerHTML = `
            <div class="snippet-header">
              <div>
                <span class="snippet-title">Página ${item.page} — <span style="color: var(--primary);">${item.source_label}</span></span>
                <span class="brand-badge" style="margin-left: 8px;">Término: "${item.token_searched || item.matched_term}" (${item.match_type})</span>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="jumpToPage(${item.page}, '${encodeURIComponent(item.token_searched || query)}')">Ver en Visor ➔</button>
            </div>
            <div class="snippet-body">${highlightedSnippet}</div>
          `;
          searchResultsList.appendChild(card);
        });

        // Automatically load preview of first matching page with visual highlights
        if (data.matched_pages.length > 0) {
          loadPagePreview(data.matched_pages[0], activeHighlightQuery);
        }
      }

      switchTab("tab-search");

    } catch (err) {
      searchStatusText.textContent = "Error ejecutando búsqueda: " + err.message;
    }
  }

  window.jumpToPage = function(p, term) {
    const q = term ? decodeURIComponent(term) : activeHighlightQuery;
    loadPagePreview(p, q);
    switchTab("tab-viewer");
  };

  btnSearch.addEventListener("click", performSearch);
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") performSearch();
  });

  // AI Field Tag Management
  function renderFieldTags() {
    fieldTagsContainer.innerHTML = "";
    targetFields.forEach((field, index) => {
      const tag = document.createElement("div");
      tag.className = "field-tag";
      tag.innerHTML = `
        <span>${field}</span>
        <span class="remove-btn" title="Eliminar campo" onclick="removeField(${index})">&times;</span>
      `;
      fieldTagsContainer.appendChild(tag);
    });
  }

  window.removeField = function(idx) {
    targetFields.splice(idx, 1);
    renderFieldTags();
  };

  btnAddField.addEventListener("click", () => {
    const val = newFieldInput.value.trim();
    if (val && !targetFields.includes(val)) {
      targetFields.push(val);
      renderFieldTags();
      newFieldInput.value = "";
    }
  });

  newFieldInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      btnAddField.click();
    }
  });

  // Execute AI Extraction
  btnRunAi.addEventListener("click", async () => {
    if (!currentDoc) {
      alert("Por favor carga un documento PDF primero.");
      return;
    }
    if (targetFields.length === 0) {
      alert("Agrega al menos un campo para extraer.");
      return;
    }

    const selectedModel = selectAiModel.value;
    showLoader(`Consultando Inteligencia Artificial (${selectedModel})...`, "Podando contexto de páginas y generando JSON estructurado...");

    try {
      const res = await fetch("/api/extract-ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fields: targetFields,
          model: selectedModel
        })
      });

      const data = await res.json();
      lastAIResult = data;

      // Update KPI
      kpiAiTime.textContent = `${data.latency_seconds || '--'} s`;
      kpiAiModel.textContent = `${data.model_used} (${data.pages_consulted.length} págs podadas)`;

      aiTelemetryBadge.textContent = `⚡ Latencia: ${data.latency_seconds} s • Páginas analizadas: [${data.pages_consulted.join(", ")}]`;

      // Render table
      aiResultsTbody.innerHTML = "";
      const values = data.values || {};

      Object.keys(values).forEach(field => {
        const val = values[field];
        const tr = document.createElement("tr");
        const isFound = val && val !== "No encontrado" && !val.includes("Error");

        tr.innerHTML = `
          <td style="font-weight: 600;">${field}</td>
          <td>
            <span style="color: ${isFound ? 'var(--text-primary)' : 'var(--text-muted)'}; font-weight: ${isFound ? '600' : '400'};">
              ${val}
            </span>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="navigator.clipboard.writeText('${val.replace(/'/g, "\\'")}'); alert('Valor copiado al portapapeles');">Copiar</button>
          </td>
        `;
        aiResultsTbody.appendChild(tr);
      });

      btnCopyJson.disabled = false;
      switchTab("tab-ai");

    } catch (err) {
      alert("Error al extraer con IA: " + err.message);
    } finally {
      hideLoader();
    }
  });

  // Copy JSON handler
  btnCopyJson.addEventListener("click", () => {
    if (lastAIResult && lastAIResult.values) {
      navigator.clipboard.writeText(JSON.stringify(lastAIResult.values, null, 2));
      alert("JSON copiado exitosamente al portapapeles.");
    }
  });

});
