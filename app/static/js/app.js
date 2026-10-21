// Add cleanups registry
window.pjaxCleanupTasks = window.pjaxCleanupTasks || [];
let pageInitializerQueue = null;
function scheduleReadyListener(target, type, listener) {
  const run = () => {
    const event = new Event(type);
    if (typeof listener === "function") listener.call(target, event);
    else listener?.handleEvent(event);
  };
  if (pageInitializerQueue) pageInitializerQueue.push(run);
  else setTimeout(run, 0);
}

// Intercept addEventListener for DOMContentLoaded & load to trigger immediately if already loaded
const originalAddEventListener = document.addEventListener;
document.addEventListener = function (type, listener, options) {
  if (type === "DOMContentLoaded" && document.readyState !== "loading") {
    scheduleReadyListener(this, type, listener);
  } else {
    originalAddEventListener.call(this, type, listener, options);
  }
};

const originalWindowAddEventListener = window.addEventListener;
window.addEventListener = function (type, listener, options) {
  if (
    (type === "DOMContentLoaded" || type === "load") &&
    document.readyState === "complete"
  ) {
    scheduleReadyListener(this, type, listener);
  } else if (
    type === "DOMContentLoaded" &&
    document.readyState === "interactive"
  ) {
    scheduleReadyListener(this, type, listener);
  } else {
    originalWindowAddEventListener.call(this, type, listener, options);
  }
};

// Clean up all page-specific tasks and watchers
function runPjaxCleanups() {
  if (quoteController) {
    quoteController.abort();
    quoteController = null;
  }

  // 1. Clear any watchlist refresh interval
  if (typeof startQuoteRefresh === "function") {
    startQuoteRefresh(0);
  }
  // 2. Run custom page cleanup tasks
  if (window.pjaxCleanupTasks && window.pjaxCleanupTasks.length) {
    window.pjaxCleanupTasks.forEach((task) => {
      try {
        task();
      } catch (e) {
        console.error("Cleanup error:", e);
      }
    });
    window.pjaxCleanupTasks = [];
  }
}

// Helper to set quick look loading state
window.setQuickLookLoading = function (loading) {
  const btn = document.getElementById("quickLookSubmitBtn");
  const progress = document.getElementById("quickLookProgress");
  const fill = progress ? progress.querySelector(".progress-bar-fill") : null;

  if (window.quickLookInterval) {
    clearInterval(window.quickLookInterval);
    window.quickLookInterval = null;
  }

  if (loading) {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "正在分析数据...";
      btn.style.background = "#9ca3af";
      btn.style.cursor = "not-allowed";
    }
    if (progress && fill) {
      progress.style.display = "block";
      fill.style.width = "0%";
      let width = 0;
      window.quickLookInterval = setInterval(() => {
        if (width < 90) {
          width += Math.random() * 15 + 5;
          if (width > 90) width = 90;
          fill.style.width = width + "%";
        } else {
          clearInterval(window.quickLookInterval);
          window.quickLookInterval = null;
        }
      }, 250);
    }
  } else {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "获取分析数据";
      btn.style.background = "";
      btn.style.cursor = "";
    }
    if (progress) {
      progress.style.display = "none";
    }
    if (fill) {
      fill.style.width = "0%";
    }
  }
};

function historyText(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}
// Analysis history list management
window.addToAnalysisHistory = function (symbol, market, name) {
  if (!symbol) return;
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem("analysis_history") || "[]");
  } catch (e) {
    history = [];
  }

  // Remove duplicate if exists
  history = history.filter(
    (item) =>
      !(
        item.symbol.toUpperCase() === symbol.toUpperCase() &&
        item.market.toUpperCase() === market.toUpperCase()
      ),
  );

  // Add to beginning of array
  history.unshift({
    symbol: symbol.toUpperCase(),
    market: market.toUpperCase(),
    name: name || symbol.toUpperCase(),
    timestamp: Date.now(),
  });

  // Limit to 10 items
  if (history.length > 10) {
    history = history.slice(0, 10);
  }

  localStorage.setItem("analysis_history", JSON.stringify(history));
  window.renderAnalysisHistory();
};

window.renderAnalysisHistory = function () {
  const card = document.getElementById("analysisHistoryCard");
  const list = document.getElementById("sidebarHistoryList");
  if (!card || !list) return;

  let history = [];
  try {
    history = JSON.parse(localStorage.getItem("analysis_history") || "[]");
  } catch (e) {
    history = [];
  }

  if (history.length === 0) {
    card.style.display = "none";
    return;
  }

  card.style.display = "block";
  list.innerHTML = history
    .map((item) => {
      const marketLabel =
        item.market === "US" ? "美股" : item.market === "HK" ? "港股" : "A股";
      return `
            <div class="history-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: var(--bg); border: 1px solid var(--line); border-radius: 12px; font-size: 13px; transition: all 0.2s;">
                <div style="display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; margin-right: 8px;">
                    <span class="history-name" style="font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${historyText(item.name)}">${historyText(item.name)}</span>
                    <span class="history-symbol" style="font-size: 11px; color: var(--muted);">${historyText(item.symbol)} (${marketLabel})</span>
                </div>
                <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
                    <a href="/stock?symbol=${encodeURIComponent(item.symbol)}&market=${encodeURIComponent(item.market)}" class="history-btn-view" style="color: #ff4a3d; font-weight: 600; font-size: 12px; text-decoration: none; padding: 4px 8px; border-radius: 8px; background: rgba(255, 74, 61, 0.08); transition: all 0.2s;">查看</a>
                    <button class="history-btn-refresh" data-symbol="${historyText(item.symbol)}" data-market="${historyText(item.market)}" style="border: none; background: none; color: #10b981; font-weight: 600; font-size: 12px; cursor: pointer; padding: 4px 8px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); transition: all 0.2s;">重新分析</button>
                </div>
            </div>
        `;
    })
    .join("");

  // Bind refresh button click
  list.querySelectorAll(".history-btn-refresh").forEach((btn) => {
    btn.onclick = (e) => {
      e.preventDefault();
      const symbol = btn.dataset.symbol;
      const market = btn.dataset.market;

      // Set the sidebar form values
      const mSelect = document.querySelector(
        "#quickLookForm select[name='market']",
      );
      const sInput = document.querySelector(
        "#quickLookForm input[name='symbol']",
      );
      if (mSelect && sInput) {
        mSelect.value = market;
        sInput.value = symbol;
      }

      // Navigate with refresh=true
      window.setQuickLookLoading(true);
      navigateTo(
        `/stock?symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(market)}&refresh=true`,
      );
    };
  });
};

// Keep only the latest PJAX navigation active so slower, older responses
// cannot replace the page selected by the user most recently.
let activeNavigationController = null;
let activeNavigationId = 0;

// Prepare assets while the current page remains intact; only page data is fetched afresh.
const pageScriptSources = new Map();
const pageStyles = new Map();
const persistentScripts = new Set(
  Array.from(document.querySelectorAll('script[src*="/vendor/"]'), script => script.src),
);
const isGlobalStyle = (href) => /\/(style|glass|layout_stability)\.css(?:\?|$)/.test(href);
for (const link of document.querySelectorAll('link[rel="stylesheet"]')) {
  if (!isGlobalStyle(link.href)) {
    link.dataset.pjaxPageStyle = "1";
    pageStyles.set(link.href, { link, ready: Promise.resolve() });
  }
}
async function preparePageAssets(doc) {
  const styles = Array.from(doc.querySelectorAll('link[rel="stylesheet"]')).filter(link => !isGlobalStyle(link.href));
  const scripts = Array.from(doc.querySelectorAll('.content-area script, #dynamic-sidebar-content script'));
  await Promise.all([
    ...styles.map(link => {
      if (!pageStyles.has(link.href)) {
        const resource = document.createElement("link");
        resource.rel = "stylesheet";
        resource.href = link.href;
        resource.media = "not all";
        resource.dataset.pjaxPageStyle = "1";
        const ready = new Promise((resolve, reject) => {
          resource.onload = resolve;
          resource.onerror = () => {
            pageStyles.delete(link.href);
            resource.remove();
            reject(new Error("页面样式加载失败"));
          };
        });
        pageStyles.set(link.href, { link: resource, ready });
        document.head.append(resource);
      }
      return pageStyles.get(link.href).ready;
    }),
    ...scripts.filter(script => script.src && !persistentScripts.has(script.src)).map(script => {
      if (!pageScriptSources.has(script.src)) {
        const source = fetch(script.src).then(response => {
          if (!response.ok) throw new Error("页面脚本加载失败");
          return response.text();
        }).catch(error => { pageScriptSources.delete(script.src); throw error; });
        pageScriptSources.set(script.src, source);
      }
      return pageScriptSources.get(script.src);
    }),
  ]);
  for (const script of scripts) {
    if (script.src && !persistentScripts.has(script.src))
      script.textContent = await pageScriptSources.get(script.src);
  }
  return { styles, scripts };
}

// Perform client-side PJAX navigation
async function navigateTo(url, pushState = true) {
  const contentArea = document.querySelector(".content-area");
  if (!contentArea) {
    window.location.href = url;
    return;
  }

  const navigationId = ++activeNavigationId;
  if (activeNavigationController) {
    activeNavigationController.abort();
  }
  const navigationController = new AbortController();
  activeNavigationController = navigationController;

  // Visual feedback (delay to prevent flicker on fast loads)
  let loadingTimeout = setTimeout(() => {
    contentArea.classList.add("pjax-loading");
  }, 100);

  try {
    const response = await fetch(url, { signal: navigationController.signal });
    if (!response.ok) {
      throw new Error(`Failed to fetch page: ${response.status}`);
    }
    const html = await response.text();
    if (navigationId !== activeNavigationId) return;
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const newContent = doc.querySelector(".content-area");
    if (!newContent) throw new Error("页面内容缺失");
    const assets = await preparePageAssets(doc);
    if (navigationId !== activeNavigationId) return;
    runPjaxCleanups();
    document.body.dataset.page = doc.body.dataset.page || "";
    // Apply styles and initialize the new DOM in the same task, before the next paint.
    const activeStyles = new Set(assets.styles.map(link => link.href));
    for (const [href, entry] of pageStyles) {
      if (entry.link.parentElement !== document.head) document.head.append(entry.link);
      entry.link.media = activeStyles.has(href) ? "all" : "not all";
    }
    doc.querySelectorAll('.content-area link[rel="stylesheet"], #dynamic-sidebar-content link[rel="stylesheet"]').forEach(link => link.remove());
    assets.scripts.forEach(script => script.remove());
    pageInitializerQueue = [];

    // Swap main content area
    if (newContent) {
      contentArea.innerHTML = newContent.innerHTML;
    }
    document.querySelector(".main-shell")?.scrollTo({ top: 0, behavior: "instant" });

    // Swap page title
    const newTitle = doc.querySelector(".page-title");
    const titleEl = document.querySelector(".page-title");
    if (newTitle && titleEl) {
      titleEl.innerHTML = newTitle.innerHTML;
    }

    // Sync title actions before initializing the new page's scripts.
    const topbar = document.querySelector(".page-topbar");
    if (topbar) {
      topbar.querySelector(".page-topbar-actions")?.remove();
      const newActions = doc.querySelector(".page-topbar-actions");
      if (newActions) topbar.appendChild(newActions.cloneNode(true));
    }

    // Swap document title
    if (doc.title) {
      document.title = doc.title;
    }

    // Swap page-specific sidebar content if exists
    const newSidebar = doc.querySelector("#dynamic-sidebar-content");
    const sidebarEl = document.querySelector("#dynamic-sidebar-content");
    if (sidebarEl) {
      if (newSidebar) {
        sidebarEl.innerHTML = newSidebar.innerHTML;
      } else {
        sidebarEl.innerHTML = "";
      }
    }

    // Update active page class in sidebar-nav
    const newActiveLink = doc.querySelector(".sidebar-nav a.active");
    document.querySelectorAll(".sidebar-nav a").forEach((link) => {
      link.classList.remove("active");
      if (
        newActiveLink &&
        link.getAttribute("href") === newActiveLink.getAttribute("href")
      ) {
        link.classList.add("active");
      }
    });

    // Push history state if requested
    if (pushState) {
      window.history.pushState({}, "", url);
    }

    for (const oldScript of assets.scripts) {
      if (oldScript.src && persistentScripts.has(oldScript.src)) continue;
      const script = document.createElement("script");
      script.textContent = oldScript.textContent;
      contentArea.append(script);
      script.remove();
      if (oldScript.src.includes("/vendor/")) persistentScripts.add(oldScript.src);
    }
    while (pageInitializerQueue.length) pageInitializerQueue.shift()();
    pageInitializerQueue = null;
    if (navigationId !== activeNavigationId) return;
    document
      .querySelector(".main-shell")
      ?.scrollTo({ top: 0, behavior: "instant" });
    document.dispatchEvent(new CustomEvent("saul:page-ready"));

    // Trigger watchlist/global refresh if we land on dashboard or detail or general page
    const hasQuoteNodes =
      document.querySelectorAll("[data-quote-symbol]").length > 0;
    if (hasQuoteNodes) {
      if (typeof refreshAllQuotes === "function") {
        refreshAllQuotes();
      }

      // Re-initialize app.js UI event hooks for elements that might be re-created in content/sidebar
      const intervalInput = document.getElementById("refreshIntervalInput");
      if (intervalInput) {
        const seconds = parseInt(intervalInput.value, 10);
        if (!isNaN(seconds)) {
          startQuoteRefresh(seconds * 1000);
        }
      }
    } else {
      // Stop watchlist refresh on pages that don't display watchlist items
      startQuoteRefresh(0);
    }
  } catch (error) {
    if (error.name === "AbortError" || navigationId !== activeNavigationId)
      return;
    console.error("PJAX navigation failed:", error);
    // Fallback to standard reload
    window.location.href = url;
  } finally {
    pageInitializerQueue = null;
    clearTimeout(loadingTimeout);
    if (navigationId === activeNavigationId) {
      if (activeNavigationController === navigationController) {
        activeNavigationController = null;
      }
      contentArea.classList.remove("pjax-loading");

      // Reset the sidebar "quick look" form state if it was loading and we are NOT on a stock page
      if (!window.location.pathname.startsWith("/stock")) {
        window.setQuickLookLoading(false);
      }
    }
  }
}

// Hook internal link clicks
document.addEventListener("click", (e) => {
  const link = e.target.closest("a");
  if (!link) return;

  // Skip non-standard clicks
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
    return;

  const href = link.getAttribute("href");
  if (!href || href.startsWith("#") || href.startsWith("javascript:")) return;

  try {
    const url = new URL(link.href);
    // Check same origin
    if (url.origin !== window.location.origin) return;

    // Skip static file directories
    if (url.pathname.startsWith("/static")) return;

    e.preventDefault();
    navigateTo(url.pathname + url.search);
  } catch (err) {
    // Ignore invalid URL
  }
});

// Hook GET form submissions
document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.method.toLowerCase() === "get") {
    try {
      const actionUrl = new URL(form.action || window.location.href);
      if (actionUrl.origin !== window.location.origin) return;

      // Build query params
      const formData = new FormData(form);
      const params = new URLSearchParams();
      for (const [key, val] of formData.entries()) {
        params.append(key, val);
      }

      const targetUrl = actionUrl.pathname + "?" + params.toString();
      e.preventDefault();
      navigateTo(targetUrl);
    } catch (err) {
      // Ignore
    }
  }
});

// Handle browser back/forward buttons
window.addEventListener("popstate", () => {
  navigateTo(window.location.pathname + window.location.search, false);
});

let priceChartInstance = null;
let refreshIntervalId = null;
let quoteRefreshInFlight = false;
let quoteController = null;
const DEFAULT_REFRESH_SECONDS = 30;

async function refreshQuoteNode(node) {
  const symbol = node.dataset.quoteSymbol;
  const market = node.dataset.quoteMarket;
  if (!symbol || !market) {
    return;
  }

  try {
    const pair = `${symbol.trim().toUpperCase()}:${market.trim().toUpperCase()}`;
    const response = await fetch(
      `/api/quotes/batch?pairs=${encodeURIComponent(pair)}&_t=${Date.now()}`,
    );
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    const payload = (data.quotes || {})[pair];
    if (!payload) {
      return;
    }
    const fields = [
      "price",
      "previous_close",
      "change",
      "change_percent",
      "source",
      "updated_at",
    ];
    fields.forEach((field) => {
      node.querySelectorAll(`[data-value="${field}"]`).forEach((element) => {
        const key = field === "source" ? "source" : `${field}_text`;
        element.textContent = payload[key] ?? "--";
        if (field === "change" || field === "change_percent") {
          element.classList.remove("quote-up", "quote-down", "quote-flat");
          element.classList.add(`quote-${payload.css_class}`);
        }
      });
    });

    node.classList.remove("quote-up", "quote-down", "quote-flat");
    node.classList.add(`quote-${payload.css_class}`);
  } catch (error) {
    console.error("quote refresh failed", error);
  }
}

async function refreshAllQuotes() {
  if (document.hidden) return;
  if (quoteRefreshInFlight) {
    return;
  }

  const nodes = document.querySelectorAll("[data-quote-symbol]");
  if (nodes.length === 0) {
    return;
  }

  const pairs = [];
  nodes.forEach((node) => {
    const symbol = node.dataset.quoteSymbol;
    const market = node.dataset.quoteMarket;
    if (symbol && market) {
      pairs.push(
        `${symbol.trim().toUpperCase()}:${market.trim().toUpperCase()}`,
      );
    }
  });

  if (pairs.length === 0) {
    return;
  }

  const uniquePairs = Array.from(new Set(pairs));

  try {
    quoteRefreshInFlight = true;
    quoteController = new AbortController();
    const response = await fetch(
      `/api/quotes/batch?pairs=${encodeURIComponent(uniquePairs.join(","))}&_t=${Date.now()}`,
      { signal: quoteController.signal },
    );
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    const quotes = data.quotes || {};

    nodes.forEach((node) => {
      if (!node.isConnected) return;
      const symbol = (node.dataset.quoteSymbol || "").trim().toUpperCase();
      const market = (node.dataset.quoteMarket || "").trim().toUpperCase();
      const key = `${symbol}:${market}`;
      const payload = quotes[key];
      if (!payload) {
        return;
      }

      const fields = [
        "price",
        "previous_close",
        "change",
        "change_percent",
        "source",
        "updated_at",
      ];
      fields.forEach((field) => {
        node.querySelectorAll(`[data-value="${field}"]`).forEach((element) => {
          const keyName = field === "source" ? "source" : `${field}_text`;
          element.textContent = payload[keyName] ?? "--";
          if (field === "change" || field === "change_percent") {
            element.classList.remove("quote-up", "quote-down", "quote-flat");
            element.classList.add(`quote-${payload.css_class}`);
          }
        });
      });

      node.classList.remove("quote-up", "quote-down", "quote-flat");
      node.classList.add(`quote-${payload.css_class}`);
    });
  } catch (error) {
    if (error.name !== "AbortError")
      console.error("batch quote refresh failed", error);
  } finally {
    quoteRefreshInFlight = false;
  }
}

function renderPriceChart() {
  const canvas = document.getElementById("priceChart");
  const points = window.stockChartData;
  if (
    !canvas ||
    !Array.isArray(points) ||
    !points.length ||
    typeof Chart === "undefined"
  ) {
    return;
  }

  const labels = points.map((item) => item.date);
  const values = points
    .map((item) => Number(item.close))
    .filter((value) => Number.isFinite(value));
  if (!values.length) {
    return;
  }

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const padding = Math.max((maxValue - minValue) * 0.18, maxValue * 0.01, 1);

  if (priceChartInstance) {
    priceChartInstance.destroy();
  }

  priceChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "#111827",
          backgroundColor: "rgba(17, 24, 39, 0.06)",
          borderWidth: 2.5,
          fill: true,
          pointRadius: 2,
          pointHoverRadius: 4,
          pointBackgroundColor: "#111827",
          tension: 0.32,
          spanGaps: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#6b7280", maxTicksLimit: 6 },
        },
        y: {
          min: minValue - padding,
          max: maxValue + padding,
          grid: { color: "#eef2f7" },
          ticks: {
            color: "#6b7280",
            callback(value) {
              return Number(value).toFixed(2);
            },
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#111827",
          titleColor: "#ffffff",
          bodyColor: "#ffffff",
        },
      },
    },
  });
}

function queueChartRender(retryCount = 12) {
  if (typeof Chart !== "undefined") {
    renderPriceChart();
    return;
  }
  if (retryCount <= 0) {
    return;
  }
  window.setTimeout(() => queueChartRender(retryCount - 1), 250);
}

function startQuoteRefresh(intervalMs) {
  if (refreshIntervalId) {
    window.clearInterval(refreshIntervalId);
    refreshIntervalId = null;
  }
  if (intervalMs > 0) {
    refreshIntervalId = window.setInterval(refreshAllQuotes, intervalMs);
  }
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

document.addEventListener("DOMContentLoaded", () => {
  refreshAllQuotes();
  queueChartRender();

  const intervalInput = document.getElementById("refreshIntervalInput");
  const applyBtn = document.getElementById("applyIntervalBtn");
  const hasQuoteNodes =
    document.querySelectorAll("[data-quote-symbol]").length > 0;

  if (intervalInput && applyBtn) {
    const savedInterval = localStorage.getItem(
      "quote_refresh_interval_seconds",
    );
    if (savedInterval !== null) {
      intervalInput.value = savedInterval;
    }

    const initialSeconds = parseFloat(intervalInput.value);
    if (hasQuoteNodes && !isNaN(initialSeconds)) {
      const seconds = Math.max(initialSeconds, 0);
      intervalInput.value = seconds;
      startQuoteRefresh(seconds * 1000);
    } else if (hasQuoteNodes) {
      intervalInput.value = DEFAULT_REFRESH_SECONDS;
      startQuoteRefresh(DEFAULT_REFRESH_SECONDS * 1000);
    } else {
      startQuoteRefresh(0);
    }

    applyBtn.addEventListener("click", () => {
      let seconds = parseFloat(intervalInput.value);
      if (isNaN(seconds) || seconds < 0) {
        seconds = 0;
        intervalInput.value = 0;
      }
      localStorage.setItem("quote_refresh_interval_seconds", seconds);

      const activeQuoteNodes =
        document.querySelectorAll("[data-quote-symbol]").length > 0;
      startQuoteRefresh(activeQuoteNodes ? seconds * 1000 : 0);

      const oldText = applyBtn.textContent;
      applyBtn.textContent = "已应用";
      applyBtn.style.background = "#059669";
      setTimeout(() => {
        applyBtn.textContent = oldText;
        applyBtn.style.background = "";
      }, 1000);
    });
  } else {
    startQuoteRefresh(hasQuoteNodes ? DEFAULT_REFRESH_SECONDS * 1000 : 0);
  }

  const elUS = document.getElementById("dataSourceSelectUS");
  const elCN = document.getElementById("dataSourceSelectCN");
  const elHK = document.getElementById("dataSourceSelectHK");
  const applyDSBtn = document.getElementById("applyDataSourceBtn");

  if (applyDSBtn && elUS && elCN && elHK) {
    applyDSBtn.addEventListener("click", () => {
      const valUS = elUS.value;
      const valCN = elCN.value;
      const valHK = elHK.value;

      document.cookie = `glass_preferred_provider_us=${valUS};path=/;max-age=31536000`;
      document.cookie = `glass_preferred_provider_cn=${valCN};path=/;max-age=31536000`;
      document.cookie = `glass_preferred_provider_hk=${valHK};path=/;max-age=31536000`;
      document.cookie = `glass_preferred_provider=auto;path=/;max-age=31536000`;

      refreshAllQuotes();
      window.dispatchEvent(new CustomEvent("dataSourceChanged"));

      const oldText = applyDSBtn.textContent;
      applyDSBtn.textContent = "已应用";
      applyDSBtn.style.background = "#059669";
      setTimeout(() => {
        applyDSBtn.textContent = oldText;
        applyDSBtn.style.background = "";
      }, 1000);
    });
  }

  const quickLookForm = document.getElementById("quickLookForm");
  if (quickLookForm) {
    quickLookForm.addEventListener("submit", () => {
      window.setQuickLookLoading(true);
    });
  }

  // Hook Clear History Button
  const clearBtn = document.getElementById("clearHistoryBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      localStorage.removeItem("analysis_history");
      window.renderAnalysisHistory();
    });
  }

  // Render analysis history on load
  window.renderAnalysisHistory();
});

// Background tabs do not continuously poll quotes. Resume with one current refresh.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshAllQuotes();
});
