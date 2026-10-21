/* Amicro btn-11 / btn-9 motion, adapted to the local HTML/PJAX shell.
 * Reference: https://github.com/Subhan-code/Amicro--Micro-transitions- (MIT).
 * Decoration keeps the original buttons and their action handlers intact.
 */
(() => {
  "use strict";
  const paths = {
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    close: '<path d="m18 6-12 12M6 6l12 12"/>',
    trash: '<path d="M3 6h18M19 6l-1 14H6L5 6M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M10 10v7M14 10v7"/>',
    edit: '<path d="m16 3 5 5M4 20l4-1L21 6a2 2 0 0 0-4-4L4 15zM4 15l5 5"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1A8 8 0 0 1 19.5 10M4.5 14A8 8 0 0 0 18 18"/>',
    manage: '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8"/><path d="M10 3h4l.6 3 2.4 1.4 2.9-.9 2 3.5-2.3 2 0 2.8 2.3 2-2 3.5-2.9-.9-2.4 1.4-.6 3h-4l-.6-3L7 19.4l-2.9.9-2-3.5 2.3-2V12l-2.3-2 2-3.5 2.9.9L9.4 6z"/>',
  };
  function icon(kind) {
    const span = document.createElement("span");
    span.className = `micro-icon micro-icon-${kind}`;
    span.setAttribute("aria-hidden", "true");
    span.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths[kind]}</svg>`;
    return span;
  }
  function morph(from = "search", to = "close") {
    const span = document.createElement("span");
    span.className = "micro-morph";
    span.setAttribute("aria-hidden", "true");
    span.append(icon(from), icon(to));
    return span;
  }
  function decorateButton(button) {
    if (button.querySelector(".micro-icon, .micro-morph")) return;
    if (button.dataset.micro === "delete") {
      // Icon-only option controls retain their accessible name, not the old emoji.
      if (button.textContent.trim() === "❌") {
        button.replaceChildren();
        if (!button.hasAttribute("aria-label")) button.setAttribute("aria-label", button.title || "删除");
      }
      const mark = icon(button.closest(".option-manager-row") ? "close" : "trash");
      mark.classList.add("micro-icon-trash");
      button.prepend(mark);
    } else if (button.dataset.micro === "edit") {
      if (button.textContent.trim() === "✏️") button.replaceChildren();
      if (!button.textContent.trim() && !button.hasAttribute("aria-label")) button.setAttribute("aria-label", button.title || "修改");
      button.prepend(morph("edit", "check"));
    } else if (button.dataset.micro === "refresh") {
      const old = button.querySelector(".refresh-icon");
      if (old) { old.replaceChildren(icon("refresh")); }
      else button.prepend(icon("refresh"));
    } else if (button.dataset.micro === "manage") {
      [...button.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).forEach(node => { node.textContent = node.textContent.replace(/⚙️?/g, "").trim(); });
      button.prepend(icon("manage"));
    } else {
      button.prepend(morph());
    }
  }
  function decorateSearch(input) {
    if (input.dataset.microReady) return;
    input.dataset.microReady = "1";
    let wrapper = input.parentElement;
    if (!wrapper.matches("[data-micro-search-field]")) {
      wrapper = document.createElement("div");
      input.before(wrapper);
      wrapper.append(input);
    }
    wrapper.classList.add("micro-search-field");
    if (wrapper.tagName === "LABEL" && input.id) wrapper.htmlFor = input.id;
    if (!input.hasAttribute("aria-label") && wrapper.tagName !== "LABEL") input.setAttribute("aria-label", "搜索");
    // Replace only the old visual icon; keep labels and input nodes intact.
    [...wrapper.children].filter(node => node.tagName === "SPAN" && node.textContent.trim() === "🔍").forEach(node => node.remove());
    const button = document.createElement("button");
    button.type = "button";
    button.className = "micro-search-control";
    button.append(morph());
    wrapper.prepend(button);
    const update = () => {
      const hasQuery = input.value.length > 0;
      wrapper.classList.toggle("micro-has-query", hasQuery);
      button.setAttribute("aria-label", hasQuery ? "清除搜索" : "搜索");
      button.title = hasQuery ? "清除搜索" : "搜索";
    };
    // Clearing emits the original input event, preserving filters and page reset.
    button.addEventListener("click", event => {
      event.preventDefault();
      if (input.value) {
        input.value = "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
      input.focus({ preventScroll: true });
      update();
    });
    input.addEventListener("input", update);
    update();
  }
  function enhance(root) {
    if (!(root instanceof Element || root instanceof Document)) return;
    const buttons = [...root.querySelectorAll("button[data-micro]")];
    if (root.matches?.("button[data-micro]")) buttons.unshift(root);
    buttons.forEach(decorateButton);
    const inputs = [...root.querySelectorAll("input[data-micro-search]")];
    if (root.matches?.("input[data-micro-search]")) inputs.unshift(root);
    inputs.forEach(decorateSearch);
  }
  function init() {
    enhance(document);
    // Only inspect added subtrees: supports option dialogs and PJAX without
    // rescanning the whole page or binding duplicate listeners on navigation.
    new MutationObserver(records => {
      records.forEach(record => {
        if (record.type === "attributes") enhance(record.target);
        else record.addedNodes.forEach(enhance);
      });
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-micro"] });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
