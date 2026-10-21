/* User backgrounds stay in this browser's local IndexedDB, never in business data. */
(() => {
  const dialog = document.getElementById("backgroundDialog");
  const picker = document.getElementById("backgroundFiles");
  const status = document.getElementById("backgroundStatus");
  const preview = document.getElementById("backgroundPreview");
  let current = [];

  async function storage(value) {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open("finboard-backgrounds", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("settings");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    try {
      return await new Promise((resolve, reject) => {
        const transaction = db.transaction("settings", value === undefined ? "readonly" : "readwrite");
        const store = transaction.objectStore("settings");
        const request = value === undefined ? store.get("images") : store.put(value, "images");
        transaction.oncomplete = () => resolve(value === undefined ? request.result || [] : value);
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error || new Error("保存已中止"));
      });
    } finally { db.close(); }
  }

  function useImages(images) {
    const old = current;
    current = images.map(image => ({ name: image.name, url: URL.createObjectURL(image.blob) }));
    preview.replaceChildren();
    for (const item of current) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      image.src = item.url;
      image.alt = item.name;
      const caption = document.createElement("figcaption");
      caption.textContent = item.name;
      figure.append(image, caption);
      preview.append(figure);
    }
    status.textContent = current.length ? `已保存${current.length}张背景${current.length > 1 ? "，将自动轮换" : ""}。` : "正在使用默认风景。";
    document.dispatchEvent(new CustomEvent("saul:backgrounds", { detail: current }));
    old.forEach(item => URL.revokeObjectURL(item.url));
    return current;
  }

  window.saulBackgroundsReady = storage().then(useImages).catch(() => {
    status.textContent = "暂时无法读取已保存的背景，当前使用默认风景。";
    return [];
  });
  document.getElementById("openBackgroundSettings").addEventListener("click", () => dialog.showModal());
  document.getElementById("closeBackgroundSettings").addEventListener("click", () => dialog.close());
  document.getElementById("chooseBackgrounds").addEventListener("click", () => picker.click());
  dialog.addEventListener("click", event => { if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  } });
  const actions = () => dialog.querySelectorAll("button:not(#closeBackgroundSettings)");
  picker.addEventListener("change", async () => {
    const files = Array.from(picker.files);
    if (!files.length) return;
    actions().forEach(button => button.disabled = true);
    status.textContent = "正在准备背景…";
    try {
      await window.saulBackgroundsReady;
      const images = [];
      for (const file of files) {
        const bitmap = await createImageBitmap(file);
        try {
          const scale = Math.min(1, 3840 / bitmap.width, 2160 / bitmap.height);
          const canvas = document.createElement("canvas");
          canvas.width = Math.max(1, Math.round(bitmap.width * scale));
          canvas.height = Math.max(1, Math.round(bitmap.height * scale));
          canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
          const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/webp", 0.9));
          if (!blob) throw new Error("图片处理失败");
          images.push({ name: file.name, blob });
        } finally { bitmap.close(); }
      }
      await storage(images);
      useImages(images);
    } catch {
      status.textContent = "背景未更改，请选择可打开的图片，并确认浏览器有可用存储空间。";
    } finally {
      picker.value = "";
      actions().forEach(button => button.disabled = false);
    }
  });
  document.getElementById("restoreDefaultBackgrounds").addEventListener("click", async () => {
    actions().forEach(button => button.disabled = true);
    try { await window.saulBackgroundsReady; await storage([]); useImages([]); }
    catch { status.textContent = "恢复默认背景失败，请重试。"; }
    finally { actions().forEach(button => button.disabled = false); }
  });
})();
