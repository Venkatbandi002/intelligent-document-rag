// Enterprise Document Intelligence RAG Frontend Controller
document.addEventListener("DOMContentLoaded", () => {
  // State
  let activeTab = "chat-tab";
  let activeDocuments = [];
  let conversationId = "conv_" + Math.random().toString(36).substring(2, 9);

  // Layout & Top Nav DOM
  const sidebar = document.getElementById("sidebar");
  const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
  const dockBar = document.getElementById("dock-bar");
  const dockLeftCol = document.getElementById("dock-left-col");
  const dockCenterCol = document.getElementById("dock-center-col");
  const dockCollapsedBrand = document.getElementById("dock-collapsed-brand");
  const dockSidebarExpandBtn = document.getElementById("dock-sidebar-expand-btn");
  const activeViewName = document.getElementById("active-view-name");
  const systemStatusText = document.getElementById("system-status-text");

  // Sidebar Navigation & Actions DOM
  const navItems = document.querySelectorAll(".sidebar-nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const newChatBtn = document.getElementById("new-chat-btn");
  const recentsList = document.getElementById("recents-list");
  const tabDocCount = document.getElementById("tab-doc-count");
  const sidebarChunkCount = document.getElementById("sidebar-chunk-count");
  const clearChatBtn = document.getElementById("clear-chat-btn");

  // Ingestion & Drawer DOM
  const ingestDrawerBtn = document.getElementById("ingest-drawer-btn");
  const ingestDrawerBody = document.getElementById("ingest-drawer-body");
  const drawerArrow = document.getElementById("drawer-arrow");
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
  const loadSampleDocsBtn = document.getElementById("load-sample-docs-btn");

  // Retrieval Settings DOM
  const topKSlider = document.getElementById("top-k-slider");
  const topKVal = document.getElementById("top-k-val");
  const rerankToggle = document.getElementById("rerank-toggle");
  const docFilterSelect = document.getElementById("doc-filter-select");
  const activeConfigIndicator = document.getElementById("active-config-indicator");

  // Document Repository Tab DOM
  const docsTableBody = document.getElementById("docs-table-body");

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

  // LLM Settings Modal DOM
  const openLlmSettingsBtn = document.getElementById("open-llm-settings-btn");
  const llmModal = document.getElementById("llm-modal");
  const llmModalCloseBtn = document.getElementById("llm-modal-close-btn");
  const llmModalCancelBtn = document.getElementById("llm-modal-cancel-btn");
  const llmModalSaveBtn = document.getElementById("llm-modal-save-btn");
  const modalProviderSelect = document.getElementById("modal-provider-select");
  const geminiConfigSection = document.getElementById("gemini-config-section");
  const modalGeminiKey = document.getElementById("modal-gemini-key");
  const modalGeminiModel = document.getElementById("modal-gemini-model");
  const openaiConfigSection = document.getElementById("openai-config-section");
  const modalOpenaiKey = document.getElementById("modal-openai-key");
  const modalOpenaiModel = document.getElementById("modal-openai-model");
  const ollamaConfigSection = document.getElementById("ollama-config-section");
  const modalOllamaModel = document.getElementById("modal-ollama-model");
  const modalOllamaUrl = document.getElementById("modal-ollama-url");
  const llmModalStatus = document.getElementById("llm-modal-status");

  // --- Initial Setup ---
  initSystem();

  async function initSystem() {
    setupTabSwitching();
    setupEventListeners();
    attachPillListeners();
    await checkHealth();
    await loadDocuments();
    await loadConversations();
    await loadDashboardStats();
  }

  // --- Health Check ---
  async function checkHealth() {
    try {
      const res = await fetch("/api/v1/settings/llm");
      if (res.ok) {
        const data = await res.json();
        if (data.provider === "gemini") {
          systemStatusText.innerText = `Gemini (${data.active_model}) [ONLINE]`;
        } else if (data.provider === "ollama") {
          const statusTag = data.status === "online" ? "[ONLINE]" : "[ACTIVE]";
          systemStatusText.innerText = `Ollama (${data.active_model}) ${statusTag}`;
        } else if (data.provider === "mock") {
          systemStatusText.innerText = `Offline Grounded Extractor`;
        } else {
          systemStatusText.innerText = `Provider: ${data.provider.toUpperCase()} (${data.active_model})`;
        }
      }
    } catch (e) {
      systemStatusText.innerText = "Backend offline";
    }
  }

  // --- Tab & View Switching ---
  function switchTab(target) {
    navItems.forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-tab") === target);
    });
    tabPanes.forEach((p) => {
      p.classList.toggle("active", p.id === target);
    });
    activeTab = target;

    if (activeViewName) {
      const titles = {
        "chat-tab": "Chat & Grounded Retrieval",
        "ingest-tab": "PDF Ingestion & RAG Tuning Studio",
        "docs-tab": "Document Repository & Vectors",
        "eval-tab": "RAG Evaluation Dashboard",
        "benchmark-tab": "Optimization Benchmark Matrix",
      };
      activeViewName.innerText = titles[target] || "DocRAG";
    }

    if (target === "eval-tab") {
      loadDashboardStats();
    } else if (target === "docs-tab" || target === "ingest-tab") {
      loadDocuments();
    }
  }

  function setupTabSwitching() {
    navItems.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab");
        switchTab(target);
      });
    });
  }

  function setSidebarCollapsed(collapsed) {
    if (!sidebar) return;
    sidebar.classList.toggle("collapsed", collapsed);
    if (dockBar) dockBar.classList.toggle("sidebar-collapsed", collapsed);
    if (dockCollapsedBrand) {
      dockCollapsedBrand.style.display = collapsed ? "flex" : "none";
    }
    if (activeViewName) {
      if (collapsed && dockCenterCol) {
        dockCenterCol.appendChild(activeViewName);
      } else if (!collapsed && dockLeftCol) {
        dockLeftCol.appendChild(activeViewName);
      }
    }
  }

  // --- Event Listeners ---
  function setupEventListeners() {
    // Sidebar collapse & expand toggles
    if (sidebarToggleBtn && sidebar) {
      sidebarToggleBtn.addEventListener("click", () => {
        const isCollapsed = !sidebar.classList.contains("collapsed");
        setSidebarCollapsed(isCollapsed);
      });
    }

    if (dockSidebarExpandBtn && sidebar) {
      dockSidebarExpandBtn.addEventListener("click", () => {
        setSidebarCollapsed(false);
      });
    }

    // Ingestion drawer toggle
    if (ingestDrawerBtn && ingestDrawerBody) {
      ingestDrawerBtn.addEventListener("click", () => {
        const isHidden = ingestDrawerBody.style.display === "none";
        ingestDrawerBody.style.display = isHidden ? "block" : "none";
        if (drawerArrow) {
          drawerArrow.innerText = isHidden ? "▴" : "▾";
        }
      });
    }

    // New Chat Button
    if (newChatBtn) {
      newChatBtn.addEventListener("click", () => {
        startNewChat();
      });
    }

    // Advanced params toggle
    if (advancedToggle && advancedParams) {
      advancedToggle.addEventListener("click", () => {
        const isHidden = advancedParams.style.display === "none";
        advancedParams.style.display = isHidden ? "flex" : "none";
        advancedToggle.innerText = isHidden ? "Chunking Parameters ▴" : "Chunking Parameters ▾";
      });
    }

    if (chunkSizeInput && chunkSizeVal) {
      chunkSizeInput.addEventListener("input", (e) => {
        chunkSizeVal.innerText = e.target.value;
      });
    }

    if (chunkOverlapInput && chunkOverlapVal) {
      chunkOverlapInput.addEventListener("input", (e) => {
        chunkOverlapVal.innerText = e.target.value;
      });
    }

    if (topKSlider && topKVal) {
      topKSlider.addEventListener("input", (e) => {
        topKVal.innerText = e.target.value;
        updateConfigIndicator();
      });
    }

    if (rerankToggle) {
      rerankToggle.addEventListener("change", () => {
        updateConfigIndicator();
      });
    }

    function updateConfigIndicator() {
      if (!activeConfigIndicator) return;
      const k = topKSlider ? topKSlider.value : 4;
      const rerank = rerankToggle && rerankToggle.checked ? "ON" : "OFF";
      activeConfigIndicator.innerText = `Top-K: ${k} | Rerank: ${rerank}`;
    }

    // Dropzone triggers
    if (dropzoneTrigger && fileInput) {
      dropzoneTrigger.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
          uploadForm.requestSubmit();
        }
      });

      // Drag and drop
      dropzoneTrigger.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzoneTrigger.style.borderColor = "var(--blue-primary)";
      });
      dropzoneTrigger.addEventListener("dragleave", () => {
        dropzoneTrigger.style.borderColor = "";
      });
      dropzoneTrigger.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzoneTrigger.style.borderColor = "";
        if (e.dataTransfer.files.length > 0) {
          fileInput.files = e.dataTransfer.files;
          uploadForm.requestSubmit();
        }
      });
    }

    // Upload Form Submit
    if (uploadForm) {
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
    }

    // Load Sample Docs Demo Button
    if (loadSampleDocsBtn) {
      loadSampleDocsBtn.addEventListener("click", async () => {
        loadSampleDocsBtn.disabled = true;
        loadSampleDocsBtn.innerText = "Indexing Sample Docs...";
        showStatus("Generating & ingesting demo enterprise documents...", "info");

        try {
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
    }

    // Chat Form Submit
    if (chatForm) {
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
            await loadConversations();
          } else {
            appendErrorMessage(data.detail || "Failed to retrieve grounded answer.");
          }
        } catch (err) {
          removeMessage(loadingId);
          appendErrorMessage(`Network error: ${err.message}`);
        }
      });
    }

    // Clear chat
    if (clearChatBtn) {
      clearChatBtn.addEventListener("click", async () => {
        if (confirm("Clear current conversation messages?")) {
          await fetch(`/api/v1/chat/history?conversation_id=${encodeURIComponent(conversationId)}`, { method: "DELETE" });
          renderHeroWelcome();
          await loadConversations();
        }
      });
    }

    // Evaluation run button
    if (runEvalBtn) {
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
    }

    // Benchmark run button
    if (runBenchmarkBtn) {
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
    }

    // Passage Modal close
    if (modalCloseBtn && passageModal) {
      modalCloseBtn.addEventListener("click", () => {
        passageModal.style.display = "none";
      });
      passageModal.addEventListener("click", (e) => {
        if (e.target === passageModal) passageModal.style.display = "none";
      });
    }

    // LLM Settings Modal Event Listeners
    if (openLlmSettingsBtn) {
      openLlmSettingsBtn.addEventListener("click", async () => {
        llmModalStatus.className = "status-msg";
        llmModalStatus.style.display = "none";
        try {
          const res = await fetch("/api/v1/settings/llm");
          if (res.ok) {
            const data = await res.json();
            modalProviderSelect.value = data.provider;
            if (data.provider === "gemini") {
              modalGeminiModel.value = data.active_model;
              if (data.has_gemini_key) {
                modalGeminiKey.placeholder = "Key saved (leave empty to keep current)";
              }
            } else if (data.provider === "ollama") {
              if (modalOllamaModel) modalOllamaModel.value = data.active_model;
            }
            updateProviderSections(data.provider);
          }
        } catch (err) {
          console.error(err);
        }
        llmModal.style.display = "flex";
      });
    }

    function updateProviderSections(prov) {
      if (geminiConfigSection) geminiConfigSection.style.display = prov === "gemini" ? "block" : "none";
      if (openaiConfigSection) openaiConfigSection.style.display = prov === "openai" ? "block" : "none";
      if (ollamaConfigSection) ollamaConfigSection.style.display = prov === "ollama" ? "block" : "none";
    }

    if (modalProviderSelect) {
      modalProviderSelect.addEventListener("change", (e) => {
        updateProviderSections(e.target.value);
      });
    }

    const closeLlmModal = () => {
      if (llmModal) llmModal.style.display = "none";
    };
    if (llmModalCloseBtn) llmModalCloseBtn.addEventListener("click", closeLlmModal);
    if (llmModalCancelBtn) llmModalCancelBtn.addEventListener("click", closeLlmModal);
    if (llmModal) {
      llmModal.addEventListener("click", (e) => {
        if (e.target === llmModal) closeLlmModal();
      });
    }

    // Save & Connect LLM
    if (llmModalSaveBtn) {
      llmModalSaveBtn.addEventListener("click", async () => {
        const provider = modalProviderSelect.value;
        const payload = {
          provider: provider,
          gemini_api_key: modalGeminiKey ? modalGeminiKey.value.trim() || null : null,
          gemini_model: modalGeminiModel ? modalGeminiModel.value : "gemini-1.5-flash",
          openai_api_key: modalOpenaiKey ? modalOpenaiKey.value.trim() || null : null,
          openai_model: modalOpenaiModel ? modalOpenaiModel.value : "gpt-4o-mini",
          ollama_model: modalOllamaModel ? modalOllamaModel.value.trim() || "llama3" : "llama3",
          ollama_base_url: modalOllamaUrl ? modalOllamaUrl.value.trim() || "http://localhost:11434" : "http://localhost:11434",
        };

        llmModalSaveBtn.disabled = true;
        llmModalSaveBtn.innerText = "Verifying Connection...";
        llmModalStatus.innerText = provider === "ollama" ? "Checking Ollama localhost:11434..." : "Testing connection...";
        llmModalStatus.className = "status-msg info";
        llmModalStatus.style.display = "block";

        try {
          const res = await fetch("/api/v1/settings/llm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

          const data = await res.json();
          if (res.ok) {
            llmModalStatus.innerText = `✓ ${data.message}`;
            llmModalStatus.className = "status-msg success";
            await checkHealth();
            setTimeout(() => {
              closeLlmModal();
            }, 1200);
          } else {
            llmModalStatus.innerText = `Error: ${data.detail || "Connection failed"}`;
            llmModalStatus.className = "status-msg error";
          }
        } catch (e) {
          llmModalStatus.innerText = `Network error: ${e.message}`;
          llmModalStatus.className = "status-msg error";
        } finally {
          llmModalSaveBtn.disabled = false;
          llmModalSaveBtn.innerText = "Save & Connect";
        }
      });
    }
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

      // Update Sidebar List (if present)
      if (sidebarDocList) {
        if (activeDocuments.length === 0) {
          sidebarDocList.innerHTML = `<div class="empty-state-small">No documents indexed yet. Upload a PDF or click 'Load Demo Policies' below.</div>`;
        } else {
          sidebarDocList.innerHTML = activeDocuments
            .map(
              (d) => `
            <div class="sidebar-doc-item">
              <span class="sidebar-doc-name" title="${escapeHtml(d.filename)}">📄 ${escapeHtml(d.filename)}</span>
              <span class="badge badge-subtle">${d.chunk_count} ch</span>
            </div>
          `
            )
            .join("");
        }
      }

      // Update Docs Table
      if (docsTableBody) {
        if (activeDocuments.length === 0) {
          docsTableBody.innerHTML = `<tr><td colspan="7" class="text-center">No documents in database. Upload a PDF above.</td></tr>`;
        } else {
          docsTableBody.innerHTML = activeDocuments
            .map(
              (d) => `
            <tr>
              <td><strong>📄 ${escapeHtml(d.filename)}</strong></td>
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
      }
    } catch (e) {
      console.error("Error loading documents:", e);
    }
  }

  // --- Conversation Management (ChatGPT-Style Recents) ---
  async function loadConversations() {
    if (!recentsList) return;
    try {
      const res = await fetch("/api/v1/chat/conversations");
      if (!res.ok) return;
      const data = await res.json();
      const list = data.conversations || [];

      if (list.length === 0) {
        recentsList.innerHTML = `<div class="recent-empty">No conversations yet</div>`;
        return;
      }

      recentsList.innerHTML = list
        .map(
          (c) => `
        <div class="recent-chat-item ${c.conversation_id === conversationId ? "active" : ""}" data-conv-id="${escapeHtml(c.conversation_id)}">
          <span class="recent-chat-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</span>
          <button class="delete-chat-btn" title="Delete conversation" data-conv-id="${escapeHtml(c.conversation_id)}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      `
        )
        .join("");

      // Wire item click to load history
      recentsList.querySelectorAll(".recent-chat-item").forEach((item) => {
        const convId = item.getAttribute("data-conv-id");
        item.addEventListener("click", (e) => {
          if (e.target.closest(".delete-chat-btn")) return;
          loadConversationHistory(convId);
        });
      });

      // Wire delete button
      recentsList.querySelectorAll(".delete-chat-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const convId = btn.getAttribute("data-conv-id");
          if (confirm("Delete this conversation?")) {
            await deleteConversation(convId);
          }
        });
      });
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  }

  function startNewChat() {
    conversationId = "conv_" + Math.random().toString(36).substring(2, 9);
    renderHeroWelcome();
    if (recentsList) {
      recentsList.querySelectorAll(".recent-chat-item").forEach((el) => el.classList.remove("active"));
    }
    switchTab("chat-tab");
    if (chatInput) chatInput.focus();
  }

  async function loadConversationHistory(convId) {
    conversationId = convId;
    if (recentsList) {
      recentsList.querySelectorAll(".recent-chat-item").forEach((el) => {
        el.classList.toggle("active", el.getAttribute("data-conv-id") === convId);
      });
    }
    switchTab("chat-tab");
    chatStream.innerHTML = `<div class="hero-welcome"><p style="color:var(--text-muted)">Loading conversation history...</p></div>`;

    try {
      const res = await fetch(`/api/v1/chat/history?conversation_id=${encodeURIComponent(convId)}`);
      if (!res.ok) throw new Error("Could not load chat history");
      const data = await res.json();
      chatStream.innerHTML = "";

      if (!data.messages || data.messages.length === 0) {
        renderHeroWelcome();
        return;
      }

      data.messages.forEach((m) => {
        if (m.role === "user") {
          appendUserMessage(m.content);
        } else {
          appendAssistantMessage({
            answer: m.content,
            is_grounded: (m.sources && m.sources.length > 0) || !m.content.includes("Information Not Found"),
            model_used: "DocRAG Grounded Model",
            sources: m.sources,
            retrieved_passages: m.retrieved_passages,
            latency_ms: m.latency_ms,
          });
        }
      });
    } catch (e) {
      chatStream.innerHTML = `<div class="hero-welcome"><p style="color:var(--danger)">Failed to load conversation: ${escapeHtml(e.message)}</p></div>`;
    }
  }

  async function deleteConversation(convId) {
    try {
      const res = await fetch(`/api/v1/chat/conversations/${encodeURIComponent(convId)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (conversationId === convId) {
          startNewChat();
        }
        await loadConversations();
      }
    } catch (err) {
      alert("Could not delete conversation: " + err.message);
    }
  }

  function renderHeroWelcome() {
    chatStream.innerHTML = `
      <div class="hero-welcome">
        <div class="hero-badge">Enterprise Document RAG Architecture</div>
        <h2>Grounded Semantic Search & Document Intelligence</h2>
        <p>Upload enterprise policies, manuals, or contracts and query with strict hallucination protection and exact source page attribution.</p>
        
        <div class="query-suggestions-title">Try asking an example question:</div>
        <div class="query-pills">
          <button class="pill-btn" data-query="What is the company's annual leave policy?">
            📋 "What is the annual leave policy?"
          </button>
          <button class="pill-btn" data-query="What is the daily meal allowance for business travel?">
            ✈️ "What is the travel meal allowance?"
          </button>
          <button class="pill-btn" data-query="What are the minimum hardware specifications for Titan Cloud Gateway?">
            🖥️ "Titan Gateway hardware specs?"
          </button>
          <button class="pill-btn" data-query="What is the stock option equity vesting schedule for interns?">
            🛡️ "Intern stock options?" (Hallucination Test)
          </button>
        </div>
      </div>
    `;
    attachPillListeners();
  }

  function attachPillListeners() {
    document.querySelectorAll(".pill-btn").forEach((pill) => {
      pill.addEventListener("click", () => {
        if (chatInput && chatForm) {
          chatInput.value = pill.getAttribute("data-query");
          chatForm.requestSubmit();
        }
      });
    });
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

    const answerText = resp.answer || resp.content || "";
    const isGrounded = resp.is_grounded !== undefined ? resp.is_grounded : (resp.sources && resp.sources.length > 0);
    const modelUsed = resp.model_used || "DocRAG Grounded Model";

    const groundedBadge = isGrounded
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

    const latencyText = resp.latency_breakdown
      ? `<span title="ChromaDB Retrieval: ${resp.latency_breakdown.retrieval_ms}ms | BM25 Rerank: ${resp.latency_breakdown.rerank_ms}ms | LLM Synthesis: ${resp.latency_breakdown.synthesis_ms}ms" style="cursor:help;">⚡ ${resp.latency_ms} ms (retrieval: ${resp.latency_breakdown.retrieval_ms}ms • rerank: ${resp.latency_breakdown.rerank_ms}ms)</span>`
      : `<span>⚡ ${resp.latency_ms != null ? resp.latency_ms : 0} ms</span>`;

    div.innerHTML = `
      <div class="msg-bubble">
        <div class="msg-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <strong>${escapeHtml(modelUsed)}</strong>
            ${groundedBadge}
          </div>
          ${latencyText}
        </div>
        <div class="msg-text">${formatAnswerMarkdown(answerText)}</div>
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
