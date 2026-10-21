// Global Client-side Pagination Function
window.paginateTable = function (tableId, itemsPerPage = 5) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const tbody = table.querySelector("tbody");
  if (!tbody) return;

  const rows = Array.from(tbody.querySelectorAll("tr"));

  let pagContainer = table.parentNode.nextElementSibling;
  if (pagContainer && pagContainer.classList.contains("pagination-container")) {
    pagContainer.innerHTML = "";
    if (rows.length <= itemsPerPage) {
      pagContainer.style.display = "none";
      rows.forEach((r) => (r.style.display = ""));
      return;
    }
    pagContainer.style.display = "flex";
  } else if (rows.length > itemsPerPage) {
    pagContainer = document.createElement("div");
    pagContainer.className = "pagination-container";
    table.parentNode.after(pagContainer);
  } else {
    return;
  }

  let currentPage = parseInt(sessionStorage.getItem("page_" + tableId)) || 1;
  const totalPages = Math.ceil(rows.length / itemsPerPage);

  function updatePage() {
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    sessionStorage.setItem("page_" + tableId, currentPage);

    rows.forEach((row, idx) => {
      const start = (currentPage - 1) * itemsPerPage;
      const end = start + itemsPerPage;
      if (idx >= start && idx < end) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
    renderControls();
  }

  function renderControls() {
    pagContainer.innerHTML = "";

    // Prev button
    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "page-btn";
    prevBtn.innerHTML = "&laquo; 上一页";
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        updatePage();
      }
    });
    pagContainer.appendChild(prevBtn);

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
      const pageBtn = document.createElement("button");
      pageBtn.type = "button";
      pageBtn.className = "page-btn" + (i === currentPage ? " active" : "");
      pageBtn.textContent = i;
      pageBtn.addEventListener("click", () => {
        currentPage = i;
        updatePage();
      });
      pagContainer.appendChild(pageBtn);
    }

    // Next button
    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "page-btn";
    nextBtn.innerHTML = "下一页 &raquo;";
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage++;
        updatePage();
      }
    });
    pagContainer.appendChild(nextBtn);
  }

  updatePage();
};

document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("appSidebar");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");

  function setSidebarOpen(open) {
    if (!sidebar || !sidebarToggle || !sidebarBackdrop) return;
    sidebar.classList.toggle("is-open", open);
    sidebarBackdrop.classList.toggle("is-visible", open);
    document.body.classList.toggle("sidebar-open", open);
    sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      setSidebarOpen(!sidebar.classList.contains("is-open"));
    });
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setSidebarOpen(false);
  });

  // Setup page resets on sidebar navigation links click
  document.querySelectorAll(".sidebar-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      setSidebarOpen(false);
      Object.keys(sessionStorage).forEach((key) => {
        if (key.startsWith("page_") || key === "cards_current_page") {
          sessionStorage.removeItem(key);
        }
      });
    });
  });
});

// One shared report dialog survives navigation. Closing it cancels stale loads.
(() => {
  let controller = null,
    previousFocus = null;
  window.openStockCardModal = async (date, ticker) => {
    controller?.abort();
    const request = new AbortController();
    controller = request;
    const overlay = document.getElementById("stock-card-modal-overlay"),
      body = document.getElementById("modal-card-body");
    if (!overlay || !body) return;
    previousFocus = document.activeElement;
    document.getElementById("modal-card-title").textContent =
      `${ticker} 当日深度评估报告 (${date})`;
    body.replaceChildren();
    const loading = document.createElement("p");
    loading.textContent = "正在读取完整评估报告…";
    body.append(loading);
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
    overlay.querySelector("button")?.focus();
    try {
      const response = await fetch(
        `/api/briefing/stock-card?date=${encodeURIComponent(date)}&ticker=${encodeURIComponent(ticker)}`,
        { signal: request.signal },
      );
      const data = await response.json();
      if (controller !== request) return;
      if (response.ok && data.status === "success" && data.html)
        body.innerHTML = data.html;
      else body.textContent = "没有找到这一天的完整评估报告。";
    } catch (error) {
      if (error.name !== "AbortError" && controller === request)
        body.textContent = "报告暂时无法读取，请稍后重试。";
    }
  };
  window.closeStockCardModal = (event) => {
    if (
      event &&
      event.target &&
      !event.target.classList.contains("modal-overlay") &&
      !event.target.closest(".modal-close-btn")
    )
      return;
    controller?.abort();
    controller = null;
    document
      .getElementById("stock-card-modal-overlay")
      ?.classList.remove("active");
    document.body.style.overflow = "";
    if (previousFocus?.isConnected) previousFocus.focus();
    previousFocus = null;
  };
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") window.closeStockCardModal();
  });
  document.addEventListener("saul:page-ready", () =>
    window.closeStockCardModal(),
  );
})();
