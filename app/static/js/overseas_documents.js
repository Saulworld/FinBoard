(() => {
  const page = document.getElementById("overseasDocumentsPage");
  if (!page) return;
  const addForm = page.querySelector("#documentAddForm");
  const toggle = page.querySelector("#toggleDocumentForm");
  const tiles = [...page.querySelectorAll("#documentsGrid .document-tile")];
  const pager = page.querySelector("#documentsPagination");
  const empty = page.querySelector("#documentsNoResults");
  const modal = page.querySelector("#documentDetailModal");
  const view = page.querySelector("#documentDetailView");
  const editForm = page.querySelector("#documentEditForm");
  const confirm = page.querySelector("#documentDeleteConfirm");
  const modalError = page.querySelector("#documentModalError");
  const typeModal = page.querySelector("#documentTypeModal");
  const typeInput = page.querySelector("#documentNewType");
  const typeError = page.querySelector("#documentTypeError");
  const pageSize = 9;
  let currentPage = 1, current = null, previousFocus = null;
  let detailRequest = null;
  let typeDraft = [], typeTrigger = null, typeRequestId = 0, typeKey = "document_types";
  const addressOptions = new Map([...page.querySelectorAll("#documentAddressOptions option")]
    .map(option => [option.dataset.country, option.value]));
  function defaultAddress(country) {
    const name = (country || "").trim().toLowerCase();
    const aliases = { philippines: "菲律宾", ph: "菲律宾", malaysia: "马来西亚", my: "马来西亚" };
    return addressOptions.get(aliases[name] || name) || "";
  }
  function bindAddressForm(form) {
    const country = form.elements.namedItem("country");
    const address = form.elements.namedItem("address");
    let previousDefault = "";
    const update = () => {
      if (address.value.trim() && address.value !== previousDefault) return;
      address.value = defaultAddress(country.value);
      previousDefault = address.value;
    };
    country.addEventListener("input", update);
    country.addEventListener("change", update);
    address.addEventListener("input", () => {
      if (address.value !== previousDefault) previousDefault = "";
    });
    return () => { previousDefault = address.value === defaultAddress(country.value) ? address.value : ""; };
  }
  bindAddressForm(addForm);
  const resetEditAddress = bindAddressForm(editForm);

  function showTypeError(message) {
    typeError.textContent = message;
    typeError.hidden = !message;
  }
  function renderTypes() {
    window.saulRenderOptionList(page.querySelector("#documentTypeList"), typeDraft, values => { typeDraft = values; renderTypes(); }, showTypeError);
  }
  function refreshTypeSelects(types) {
    page.querySelectorAll('select[name="document_type"]').forEach(select => {
      const selected = select.value;
      const placeholder = new Option("请选择证件类型", "");
      placeholder.disabled = true;
      const options = [placeholder, ...types.map(name => new Option(name, name))];
      if (select === editForm.elements.namedItem("document_type") && selected && !types.includes(selected))
        options.push(new Option(`${selected}（已移除）`, selected));
      select.replaceChildren(...options);
      select.value = options.some(option => option.value === selected) ? selected : "";
    });
  }
  function closeTypeModal() {
    typeRequestId++;
    typeModal.hidden = true;
    typeDraft = [];
    typeInput.value = "";
    showTypeError("");
    if (modal.hidden) document.body.style.overflow = "";
    typeTrigger?.focus({ preventScroll: true });
    typeTrigger = null;
  }
  page.querySelectorAll(".documents-manage-types, .documents-manage-countries").forEach(button => button.addEventListener("click", async () => {
    typeTrigger = button;
    typeKey = button.classList.contains("documents-manage-countries") ? "countries" : "document_types";
    page.querySelector("#documentTypeTitle").textContent = typeKey === "countries" ? "管理国家/地区" : "管理证件类型";
    typeInput.placeholder = typeKey === "countries" ? "输入新国家/地区名称" : "输入证件类型名称";
    typeInput.setAttribute("aria-label", typeKey === "countries" ? "新国家/地区" : "新证件类型");
    typeModal.hidden = false;
    document.body.style.overflow = "hidden";
    typeInput.value = "";
    showTypeError("");
    const requestId = ++typeRequestId;
    page.querySelector("#documentTypeList").replaceChildren();
    typeInput.focus();
    try {
      const response = await fetch("/api/overseas-document-options", { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "加载失败，请重试。");
      if (requestId !== typeRequestId) return;
      typeDraft = data[typeKey];
      renderTypes();
    } catch (error) { if (requestId === typeRequestId) showTypeError(error.message || "加载失败，请重试。"); }
  }));
  page.querySelectorAll("[data-close-types]").forEach(button => button.addEventListener("click", closeTypeModal));
  typeModal.addEventListener("click", event => { if (event.target === typeModal) closeTypeModal(); });
  function addType() {
    const name = typeInput.value.trim();
    if (!name) return showTypeError("请输入选项名称。");
    if (typeDraft.includes(name)) return showTypeError("该选项已存在。");
    typeDraft.push(name);
    typeInput.value = "";
    showTypeError("");
    renderTypes();
    typeInput.focus();
  }
  page.querySelector("#documentAddType").addEventListener("click", addType);
  typeInput.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); addType(); } });
  page.querySelector("#documentSaveTypes").addEventListener("click", async event => {
    if (page.querySelector("#documentTypeList").commitOptionEdit?.() === false) return;
    if (!typeDraft.length) return showTypeError("请保留至少一个选项。");
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const response = await fetch("/api/overseas-document-options", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [typeKey]: typeDraft }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "保存失败，请重试。");
      refreshTypeSelects(data.document_types);
      page.querySelector("#documentCountryOptions").replaceChildren(...data.countries.map(name => new Option(name, name)));
      closeTypeModal();
    } catch (error) { showTypeError(error.message || "保存失败，请重试。"); }
    finally { button.disabled = false; }
  });

  toggle?.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") !== "true";
    window.saulSetFormExpanded(addForm, expanded);
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.textContent = expanded ? "收起" : "添加证件";
  });

  function renderRows() {
    const pageCount = Math.ceil(tiles.length / pageSize);
    currentPage = Math.max(1, Math.min(currentPage, pageCount || 1));
    tiles.forEach(tile => { tile.hidden = true; });
    tiles.slice((currentPage - 1) * pageSize, currentPage * pageSize).forEach(tile => { tile.hidden = false; });
    empty.hidden = tiles.length > 0;
    pager.replaceChildren();
    pager.hidden = pageCount <= 1;
    if (pageCount <= 1) return;
    const button = (label, target, disabled, active = false) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "page-btn" + (active ? " active" : "");
      item.textContent = label;
      item.disabled = disabled;
      if (active) item.setAttribute("aria-current", "page");
      item.addEventListener("click", () => { currentPage = target; renderRows(); });
      pager.append(item);
    };
    button("« 上一页", currentPage - 1, currentPage === 1);
    for (let n = 1; n <= pageCount; n++) button(String(n), n, false, n === currentPage);
    button("下一页 »", currentPage + 1, currentPage === pageCount);
  }
  renderRows();

  function showError(message) {
    modalError.textContent = message;
    modalError.hidden = !message;
  }
  function showSection(section) {
    view.hidden = section !== "view";
    editForm.hidden = section !== "edit";
    confirm.hidden = section !== "delete";
    showError("");
  }
  function closeModal(event) {
    detailRequest?.abort();
    detailRequest = null;
    modal.hidden = true;
    current = null;
    page.querySelectorAll("[data-detail]").forEach(node => { node.textContent = ""; });
    editForm.reset();
    if (typeModal.hidden) document.body.style.overflow = "";
    if (previousFocus?.isConnected) {
      const target = previousFocus;
      target.focus({ preventScroll: true });
      if (event?.type === "click" && event.detail > 0) {
        target.classList.add("document-tile-pointer-return");
        target.addEventListener("blur", () => target.classList.remove("document-tile-pointer-return"), { once: true });
      }
    }
    previousFocus = null;
  }
  async function openDetail(id, trigger) {
    detailRequest?.abort();
    const request = new AbortController();
    detailRequest = request;
    previousFocus = trigger;
    showSection("view");
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    page.querySelector("#documentModalTitle").textContent = "正在读取证件详情…";
    page.querySelector("[data-close-modal]").focus();
    try {
      const response = await fetch(`/api/overseas-documents/${id}`, { signal: request.signal, cache: "no-store" });
      const data = await response.json();
      if (detailRequest !== request || !page.isConnected) return;
      if (!response.ok) throw new Error(data.message || "读取失败，请稍后重试。");
      current = data.document;
      page.querySelector("#documentModalTitle").textContent = `${current.country} · ${current.document_type}`;
      page.querySelectorAll("[data-detail]").forEach(node => {
        node.textContent = current[node.dataset.detail] || "—";
      });
    } catch (error) {
      if (error.name !== "AbortError") showError(error.message || "读取失败，请稍后重试。");
    }
  }
  page.querySelectorAll(".document-tile").forEach(button =>
    button.addEventListener("click", () => openDetail(button.dataset.id, button))
  );
  page.querySelectorAll("[data-close-modal]").forEach(button => button.addEventListener("click", closeModal));
  modal.addEventListener("click", event => { if (event.target === modal) closeModal(event); });
  const onKeydown = event => {
    if (event.key !== "Escape") return;
    if (!typeModal.hidden) closeTypeModal();
    else if (!modal.hidden) closeModal(event);
  };
  document.addEventListener("keydown", onKeydown);
  window.pjaxCleanupTasks = window.pjaxCleanupTasks || [];
  window.pjaxCleanupTasks.push(() => {
    detailRequest?.abort();
    document.removeEventListener("keydown", onKeydown);
    document.body.style.overflow = "";
  });

  page.querySelector("#documentCopyNumber").addEventListener("click", async event => {
    if (!current?.number) return;
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(current.number);
      button.textContent = "已复制";
      setTimeout(() => { if (button.isConnected) button.textContent = "复制"; }, 1600);
    } catch { showError("复制失败，请手动选择号码。"); }
  });
  page.querySelector("#documentEdit").addEventListener("click", () => {
    if (!current) return;
    const typeSelect = editForm.elements.namedItem("document_type");
    if (![...typeSelect.options].some(option => option.value === current.document_type))
      typeSelect.add(new Option(`${current.document_type}（已移除）`, current.document_type));
    for (const key of ["country", "document_type", "number", "holder", "issued_on", "expires_on", "issuer", "address", "note"])
      editForm.elements.namedItem(key).value = current[key] || "";
    resetEditAddress();
    showSection("edit");
    editForm.elements.namedItem("country").focus();
  });
  page.querySelector("#documentEditCancel").addEventListener("click", () => showSection("view"));
  page.querySelector("#documentDelete").addEventListener("click", () => { if (current) showSection("delete"); });
  page.querySelector("#documentDeleteCancel").addEventListener("click", () => showSection("view"));
  editForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!current) return;
    try {
      const response = await fetch(`/overseas-documents/${current.id}/update`, { method: "POST", body: new FormData(editForm) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "保存失败。");
      location.assign("/overseas-documents?notice=" + encodeURIComponent("境外证件已更新。"));
    } catch (error) { showError(error.message || "保存失败。"); }
  });
  page.querySelector("#documentDeleteSubmit").addEventListener("click", async () => {
    if (!current) return;
    try {
      const response = await fetch(`/overseas-documents/${current.id}/delete`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "删除失败。");
      location.assign("/overseas-documents?notice=" + encodeURIComponent("境外证件已删除。"));
    } catch (error) { showError(error.message || "删除失败。"); }
  });
})();
