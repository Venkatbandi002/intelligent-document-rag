// Enterprise Document Intelligence RAG Frontend Controller
document.addEventListener("DOMContentLoaded", () => {
  // State
  let activeTab = "chat-tab";
  let activeDocuments = [];
  let conversationId = "conv_" + Math.random().toString(36).substring(2, 9);

  // DOM Elements
  const tabButtons = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const systemStatusText = document.getElementById("system-status-text");

  // Ingestion DOM
  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const dropzoneTrigger = document.getElementById("dropzone-trigger");
  const uploadStatus = document.getElementById("upload-status");
  const advancedToggle = document.getElementById("advanced-toggle");
  const advancedParams = document.getElementById("advanced-params");
  const chunkSizeInput = document.getElementById("chunk-size");
  const chunkOverlapInput = document.getElementById("chunk-overlap");
  const chunkSizeVal = document.getElementById("chunk-size-val");
  const chunkOverlapVal = document.getElementById("chunk-overlap-val");

  // Retrieval Settings DOM
  const topKSlider = document.getElementById("top-k-slider");
  const topKVal = document.getElementById("top-k-val");
  const rerankToggle = document.getElementById("rerank-toggle");
  const docFilterSelect = document.getElementById("doc-filter-select");
  const activeConfigIndicator = document.getElementById("active-config-indicator");

  // Sidebar & Document Repository DOM
  const sidebarDocList = document.getElementById("sidebar-doc-list");
  const sidebarChunkCount = document.getElementById("sidebar-chunk-count");
  const tabDocCount = document.getElementById("tab-doc-count");
  const docsTableBody = document.getElementById("docs-table-body");
  const loadSampleDocsBtn = document.getElementById("load-sample-docs-btn");
  const clearChatBtn = document.getElementById("clear-chat-btn");

  // Chat DOM
  const chatStream = document.getElementById("chat-stream");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");

  // Evaluation & Benchmark DOM
  const runEvalBtn = document.getElementById("run-eval-btn");
  const kpiHitRate = document.getElementById("kpi-hit-rate");
  const kpiMrr = document.getElementById("kpi-mrr");
  const kpiPrecision = document.getElementById("kpi-precision");
  const kpiRecall = document.getElementById("kpi-recall");
  const kpiLatency = document.getElementById("kpi-latency");
  const evalQueriesTbody = document.getElementById("eval-queries-tbody");
  const runBenchmarkBtn = document.getElementById("run-benchmark-btn");
  const benchmarkResultsContainer = document.getElementById("benchmark-results");

  // Modal DOM
  const passageModal = document.getElementById("passage-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalBody = document.getElementById("modal-body");
  const modalCloseBtn = document.getElementById("modal-close-btn");

  // --- Initial Setup ---
  initSystem();

  async function initSystem() {
    setupTabSwitching();
    setupEventListeners();
    await checkHealth();
    await loadDocuments();
    await loadDashboardStats();
  }

  // --- Health Check ---
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        systemStatusText.innerText = `Provider: ${data.llm_provider.toUpperCase()} | Embeddings: MiniLM-L6`;
      }
    } catch (e) {
      systemStatusText.innerText = "Backend offline";
    }
  }

  // --- Tab Switching ---
  function setupTabSwitching() {
    tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab");
        tabButtons.forEach((b) => b.classList.remove("active"));
        tabPanes.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(target).classList.add("active");
        activeTab = target;
        if (target === "eval-tab") {
          loadDashboardStats();
        }
      });
    });
  }

  // --- Event Listeners ---
  function setupEventListeners() {
    // Advanced params toggle
    advancedToggle.addEventListener("click", () => {
      const isHidden = advancedParams.style.display === "none";
      advancedParams.style.display = isHidden ? "flex" : "none";
      advancedToggle.innerText = isHidden ? "Ingestion Config ▴" : "Ingestion Config ▾";
    });

    chunkSizeInput.addEventListener("input", (e) => {
      chunkSizeVal.innerText = e.target.value;
    });

    chunkOverlapInput.addEventListener("input", (e) => {
      chunkOverlapVal.innerText = e.target.value;
    });

    topKSlider.addEventListener("input", (e) => {
      topKVal.innerText = e.target.value;
      updateConfigIndicator();
    });

    rerankToggle.addEventListener("change", () => {
      updateConfigIndicator();
    });

    function updateConfigIndicator() {
      const k = topKSlider.value;
      const rerank = rerankToggle.checked ? "ON" : "OFF";
      activeConfigIndicator.innerText = `Top-K: ${k} | Rerank: ${rerank}`;
    }

    // Dropzone triggers
    dropzoneTrigger.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        uploadForm.requestSubmit();
      }
    });

    // Drag and drop
    dropzoneTrigger.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzoneTrigger.style.borderColor = "var(--accent-primary)";
    });
    dropzoneTrigger.addEventListener("dragleave", () => {
      dropzoneTrigger.style.borderColor = "var(--border-color)";
    });
    dropzoneTrigger.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzoneTrigger.style.borderColor = "var(--border-color)";
      if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        uploadForm.requestSubmit();
      }
    });

    // Upload Form Submit
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) return;

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("chunk_size", chunkSizeInput.value);
      formData.append("chunk_overlap", chunkOverlapInput.value);

      showStatus("Ingesting & embedding PDF chunks...", "info");

      try {
        const res = await fetch("/api/v1/documents/upload", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();
        if (res.ok) {
          showStatus(
            data.is_duplicate
              ? `Duplicate detected: ${data.document.filename} is already indexed.`
              : `Indexed ${data.document.filename} (${data.chunks_created} chunks)`,
            "success"
          );
          fileInput.value = "";
          await loadDocuments();
        } else {
          showStatus(`Upload failed: ${data.detail || "Server error"}`, "error");
        }
      } catch (err) {
        showStatus(`Upload error: ${err.message}`, "error");
      }
    });

    // Load Sample Docs Demo Button
    loadSampleDocsBtn.addEventListener("click", async () => {
      loadSampleDocsBtn.disabled = true;
      loadSampleDocsBtn.innerText = "Indexing Sample Docs...";
      showStatus("Generating & ingesting demo enterprise documents...", "info");

      try {
        // Trigger backend evaluation generation or upload demo PDFs
        const res = await fetch("/api/v1/evaluation/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "Demo Warmup Run", top_k: 4, enable_reranking: true }),
        });
        await loadDocuments();
        showStatus("Sample enterprise policies ready for questioning!", "success");
      } catch (err) {
        showStatus("Could not auto-load sample PDFs.", "error");
      } finally {
        loadSampleDocsBtn.disabled = false;
        loadSampleDocsBtn.innerText = "⚡ Load Sample Enterprise PDFs";
      }
    });

    // Chat Form Submit
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const question = chatInput.value.trim();
      if (!question) return;

      chatInput.value = "";
      appendUserMessage(question);

      // Loading placeholder
      const loadingId = appendLoadingMessage();

      try {
        const res = await fetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: question,
            conversation_id: conversationId,
            top_k: parseInt(topKSlider.value, 10),
            enable_reranking: rerankToggle.checked,
            document_filter: docFilterSelect.value || null,
          }),
        });

        const data = await res.json();
        removeMessage(loadingId);

        if (res.ok) {
          appendAssistantMessage(data);
        } else {
          appendErrorMessage(data.detail || "Failed to retrieve grounded answer.");
        }
      } catch (err) {
        removeMessage(loadingId);
        appendErrorMessage(`Network error: ${err.message}`);
      }
    });

    // Quick suggestion pills
    document.querySelectorAll(".pill-btn").forEach((pill) => {
      pill.addEventListener("click", () => {
        chatInput.value = pill.getAttribute("data-query");
        chatForm.requestSubmit();
      });
    });

    // Clear chat
    clearChatBtn.addEventListener("click", async () => {
      if (confirm("Clear current conversation history?")) {
        await fetch(`/api/v1/chat/history?conversation_id=${conversationId}`, { method: "DELETE" });
        chatStream.innerHTML = `
          <div class="hero-welcome">
            <div class="hero-badge">Conversation Cleared</div>
            <h2>Enterprise Document Intelligence</h2>
            <p>Ready for your next question.</p>
          </div>
        `;
      }
    });

    // Evaluation run button
    runEvalBtn.addEventListener("click", async () => {
      runEvalBtn.disabled = true;
      runEvalBtn.innerText = "Running Test Suite...";
      try {
        const res = await fetch("/api/v1/evaluation/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: "Manual Evaluation Run",
            top_k: parseInt(topKSlider.value, 10),
            enable_reranking: rerankToggle.checked,
          }),
        });
        const report = await res.json();
        renderEvaluationReport(report);
      } catch (e) {
        alert("Evaluation run failed: " + e.message);
      } finally {
        runEvalBtn.disabled = false;
        runEvalBtn.innerText = "▶ Run Live Evaluation";
      }
    });

    // Benchmark run button
    runBenchmarkBtn.addEventListener("click", async () => {
      runBenchmarkBtn.disabled = true;
      runBenchmarkBtn.innerText = "Running 3-Configuration Benchmark...";
      try {
        const res = await fetch("/api/v1/evaluation/benchmark", { method: "POST" });
        const matrix = await res.json();
        renderBenchmarkComparison(matrix.runs);
      } catch (e) {
        alert("Benchmark execution failed: " + e.message);
      } finally {
        runBenchmarkBtn.disabled = false;
        runBenchmarkBtn.innerText = "⚡ Execute Benchmark Matrix";
      }
    });

    // Modal close
    modalCloseBtn.addEventListener("click", () => {
      passageModal.style.display = "none";
    });
    passageModal.addEventListener("click", (e) => {
      if (e.target === passageModal) passageModal.style.display = "none";
    });
  }

  // --- Document Loading & Listing ---
  async function loadDocuments() {
    try {
      const res = await fetch("/api/v1/documents");
      if (!res.ok) return;
      const data = await res.json();
      activeDocuments = data.documents;

      // Update counters
      tabDocCount.innerText = data.total_documents;
      sidebarChunkCount.innerText = `${data.total_chunks} chunks`;

      // Update Document Filter Select
      docFilterSelect.innerHTML = '<option value="">All Uploaded Documents</option>';
      activeDocuments.forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d.filename;
        opt.innerText = d.filename;
        docFilterSelect.appendChild(opt);
      });

      // Update Sidebar List
      if (activeDocuments.length === 0) {
        sidebarDocList.innerHTML = `<div class="empty-state-small">No documents indexed yet. Upload a PDF or click 'Load Demo Policies' below.</div>`;
      } else {
        sidebarDocList.innerHTML = activeDocuments
          .map(
            (d) => `
          <div class="sidebar-doc-item">
            <span class="sidebar-doc-name" title="${d.filename}">📄 ${d.filename}</span>
            <span class="badge badge-subtle">${d.chunk_count} ch</span>
          </div>
        `
          )
          .join("");
      }

      // Update Docs Table
      if (activeDocuments.length === 0) {
        docsTableBody.innerHTML = `<tr><td colspan="7" class="text-center">No documents in database. Upload a PDF above.</td></tr>`;
      } else {
        docsTableBody.innerHTML = activeDocuments
          .map(
            (d) => `
          <tr>
            <td><strong>📄 ${d.filename}</strong></td>
            <td>${d.page_count}</td>
            <td><span class="badge badge-accent">${d.chunk_count}</span></td>
            <td>${(d.file_size_bytes / 1024).toFixed(1)} KB</td>
            <td><code style="font-size:0.75rem;">${d.file_hash.substring(0, 12)}...</code></td>
            <td>${new Date(d.uploaded_at).toLocaleTimeString()}</td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="reindexDoc('${d.id}')">Re-index</button>
              <button class="btn btn-ghost btn-sm" style="color:var(--danger);" onclick="deleteDoc('${d.id}')">Delete</button>
            </td>
          </tr>
        `
          )
          .join("");
      }
    } catch (e) {
      console.error("Error loading documents:", e);
    }
  }

  // Window helper functions for table action buttons
  window.deleteDoc = async (docId) => {
    if (confirm("Are you sure you want to delete this document and all its vector embeddings?")) {
      const res = await fetch(`/api/v1/documents/${docId}`, { method: "DELETE" });
      if (res.ok) {
        await loadDocuments();
      }
    }
  };

  window.reindexDoc = async (docId) => {
    const res = await fetch(`/api/v1/documents/${docId}/index`, { method: "POST" });
    if (res.ok) {
      alert("Document re-indexed successfully!");
      await loadDocuments();
    }
  };

  // --- Chat Stream Rendering ---
  function appendUserMessage(text) {
    const id = "msg_" + Math.random().toString(36).substring(2, 9);
    const div = document.createElement("div");
    div.className = "chat-msg user";
    div.id = id;
    div.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    chatStream.appendChild(div);
    chatStream.scrollTop = chatStream.scrollHeight;
    return id;
  }

  function appendLoadingMessage() {
    const id = "loading_" + Math.random().toString(36).substring(2, 9);
    const div = document.createElement("div");
    div.className = "chat-msg assistant";
    div.id = id;
    div.innerHTML = `
      <div class="msg-bubble">
        <div class="msg-header">
          <span>Retrieving semantic chunks & generating grounded answer...</span>
        </div>
        <div style="color:var(--text-muted); font-size:0.85rem;">Searching ChromaDB vector store...</div>
      </div>
    `;
    chatStream.appendChild(div);
    chatStream.scrollTop = chatStream.scrollHeight;
    return id;
  }

  function appendAssistantMessage(resp) {
    const id = "msg_" + Math.random().toString(36).substring(2, 9);
    const div = document.createElement("div");
    div.className = "chat-msg assistant";
    div.id = id;

    const groundedBadge = resp.is_grounded
      ? `<span class="badge badge-grounded">100% Grounded</span>`
      : `<span class="badge badge-ungrounded">Information Not Found</span>`;

    // Sources Pills
    let sourcesHtml = "";
    if (resp.sources && resp.sources.length > 0) {
      const chips = resp.sources
        .map(
          (s) => `
        <span class="source-chip" onclick='inspectPassage("${escapeHtml(s.document_name)}", ${s.page_number}, "${escapeHtml(s.snippet)}")'>
          📌 ${escapeHtml(s.document_name)} — Page ${s.page_number}
        </span>
      `
        )
        .join("");
      sourcesHtml = `
        <div class="sources-card">
          <div class="sources-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            Verified Sources Cited:
          </div>
          <div class="sources-chips">${chips}</div>
        </div>
      `;
    }

    // Retrieved Passages Accordion
    let passagesHtml = "";
    if (resp.retrieved_passages && resp.retrieved_passages.length > 0) {
      const cards = resp.retrieved_passages
        .map((p, idx) => {
          const scoreLabel = p.rerank_score != null ? `Hybrid Score: ${p.rerank_score}` : `Cosine Sim: ${p.similarity_score}`;
          return `
          <div class="passage-card">
            <div class="passage-meta">
              <span>[#${idx + 1}] ${escapeHtml(p.document_name)} (P.${p.page_number})</span>
              <span>${scoreLabel}</span>
            </div>
            <div class="passage-text">"${escapeHtml(p.content)}"</div>
          </div>
        `;
        })
        .join("");

      const accId = "acc_" + Math.random().toString(36).substring(2, 9);
      passagesHtml = `
        <div class="retrieved-accordion">
          <button class="accordion-toggle" onclick="toggleAccordion('${accId}')">
            <span>🔍 View Retrieved Context Passages (${resp.retrieved_passages.length})</span> ▾
          </button>
          <div class="accordion-body" id="${accId}" style="display:none;">
            ${cards}
          </div>
        </div>
      `;
    }

    div.innerHTML = `
      <div class="msg-bubble">
        <div class="msg-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <strong>DocRAG Engine (${resp.model_used})</strong>
            ${groundedBadge}
          </div>
          <span>Latency: ${resp.latency_ms} ms</span>
        </div>
        <div class="msg-text">${formatAnswerMarkdown(resp.answer)}</div>
        ${sourcesHtml}
        ${passagesHtml}
      </div>
    `;

    chatStream.appendChild(div);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function appendErrorMessage(errText) {
    const div = document.createElement("div");
    div.className = "chat-msg assistant";
    div.innerHTML = `
      <div class="msg-bubble" style="border-color: var(--danger);">
        <div class="msg-header" style="color: var(--danger);"><strong>System Alert</strong></div>
        <div class="msg-text">${escapeHtml(errText)}</div>
      </div>
    `;
    chatStream.appendChild(div);
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // --- Accordion & Modal Handlers ---
  window.toggleAccordion = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = el.style.display === "none" ? "flex" : "none";
    }
  };

  window.inspectPassage = (docName, pageNum, snippet) => {
    modalTitle.innerText = `${docName} — Page ${pageNum}`;
    modalBody.innerHTML = `
      <p style="margin-bottom:12px;"><strong>Exact Retrieved Passage Text:</strong></p>
      <div style="background:var(--bg-primary); padding:16px; border-radius:6px; border:1px solid var(--border-color); font-family:var(--font-sans); font-size:0.92rem; line-height:1.6; color:var(--text-primary);">
        "${snippet}"
      </div>
      <p style="margin-top:12px; font-size:0.75rem; color:var(--text-muted);">
        Verified provenance via ChromaDB chunk metadata & SHA-256 document hashing.
      </p>
    `;
    passageModal.style.display = "flex";
  };

  // --- Evaluation Dashboard ---
  async function loadDashboardStats() {
    try {
      const res = await fetch("/api/v1/evaluation/dashboard/stats");
      if (!res.ok) return;
      const stats = await res.json();
      if (stats.latest_evaluation) {
        kpiHitRate.innerText = (stats.latest_evaluation.hit_rate * 100).toFixed(1) + "%";
        kpiMrr.innerText = stats.latest_evaluation.mrr.toFixed(3);
        kpiPrecision.innerText = (stats.latest_evaluation.precision_at_k * 100).toFixed(1) + "%";
        kpiRecall.innerText = (stats.latest_evaluation.recall_at_k * 100).toFixed(1) + "%";
        kpiLatency.innerText = stats.latest_evaluation.avg_latency_ms.toFixed(1) + " ms";
      }
    } catch (e) {
      console.error(e);
    }
  }

  function renderEvaluationReport(report) {
    kpiHitRate.innerText = (report.hit_rate * 100).toFixed(1) + "%";
    kpiMrr.innerText = report.mrr.toFixed(3);
    kpiPrecision.innerText = (report.precision_at_k * 100).toFixed(1) + "%";
    kpiRecall.innerText = (report.recall_at_k * 100).toFixed(1) + "%";
    kpiLatency.innerText = report.avg_latency_ms.toFixed(1) + " ms";

    evalQueriesTbody.innerHTML = report.query_results
      .map((q) => {
        const isPass = q.hit || (q.expected_sources.length === 0 && q.retrieved_sources.length === 0);
        const statusBadge = isPass
          ? `<span class="badge badge-grounded">PASS</span>`
          : `<span class="badge badge-ungrounded">FAIL</span>`;
        return `
        <tr>
          <td>${statusBadge}</td>
          <td><strong>${escapeHtml(q.question)}</strong></td>
          <td>${q.hit ? "Yes" : "No"}</td>
          <td>${(q.precision_at_k * 100).toFixed(0)}%</td>
          <td>${q.reciprocal_rank.toFixed(2)}</td>
          <td>${q.latency_ms.toFixed(0)} ms</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='showQueryInspectModal(${JSON.stringify(escapeHtml(q.generated_answer))}, ${JSON.stringify(escapeHtml(q.expected_answer || ""))})'>Details</button>
          </td>
        </tr>
      `;
      })
      .join("");
  }

  window.showQueryInspectModal = (generated, expected) => {
    modalTitle.innerText = "Answer Comparison";
    modalBody.innerHTML = `
      <p><strong>Generated Answer:</strong></p>
      <div style="background:var(--bg-primary); padding:10px; border-radius:6px; margin:6px 0 14px;">${generated}</div>
      <p><strong>Expected Ground Truth:</strong></p>
      <div style="background:var(--bg-primary); padding:10px; border-radius:6px; margin:6px 0;">${expected || "N/A (Negative Test Case)"}</div>
    `;
    passageModal.style.display = "flex";
  };

  function renderBenchmarkComparison(runs) {
    benchmarkResultsContainer.innerHTML = `
      <div class="benchmark-card">
        <h3>Live Retrieval Optimization Experiment Results</h3>
        <p style="color:var(--text-secondary); font-size:0.85rem; margin-bottom:16px;">
          Empirically evaluated against <code>evaluation/questions.json</code> test set.
        </p>
        <table class="data-table benchmark-table">
          <thead>
            <tr>
              <th>Configuration</th>
              <th>Hit Rate</th>
              <th>Precision@K</th>
              <th>MRR</th>
              <th>Avg Latency</th>
            </tr>
          </thead>
          <tbody>
            ${runs
              .map(
                (r) => `
              <tr>
                <td><strong>${escapeHtml(r.name)}</strong></td>
                <td>
                  <div class="score-bar-bg"><div class="score-bar-fill" style="width:${r.hit_rate * 100}%;"></div></div>
                  ${(r.hit_rate * 100).toFixed(1)}%
                </td>
                <td>
                  <div class="score-bar-bg"><div class="score-bar-fill" style="width:${r.precision_at_k * 100}%;"></div></div>
                  ${(r.precision_at_k * 100).toFixed(1)}%
                </td>
                <td><strong>${r.mrr.toFixed(3)}</strong></td>
                <td>${r.avg_latency_ms.toFixed(1)} ms</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  // --- Utility Functions ---
  function showStatus(msg, type) {
    uploadStatus.innerText = msg;
    uploadStatus.className = `status-msg ${type}`;
    setTimeout(() => {
      if (type === "success") uploadStatus.className = "status-msg";
    }, 6000);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatAnswerMarkdown(text) {
    if (!text) return "";
    // Highlight citations [Doc, Page X]
    let formatted = escapeHtml(text).replace(
      /\[([a-zA-Z0-9_\-\. ]+?)(?:,\s*(?:Page|page|p\.)\s*(\d+))?\]/g,
      '<strong style="color:#0369A1; background:#E0F2FE; border:1px solid #BAE6FD; padding:1px 6px; border-radius:4px; font-family:var(--font-mono); font-size:0.85em; font-weight:600;">[$1, Page $2]</strong>'
    );
    // Replace newlines with breaks
    return formatted.replace(/\n/g, "<br>");
  }
});
