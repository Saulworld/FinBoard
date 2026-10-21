/* Persistent scenery and lightweight motion. Never recreated by PJAX page swaps. */
(() => {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const formAnimations = new WeakMap();
  window.saulSetFormExpanded = (form, expanded) => {
    if (!form) return;
    const before = getComputedStyle(form);
    const from = { height: `${form.getBoundingClientRect().height}px`, marginTop: before.marginTop, opacity: before.opacity };
    formAnimations.get(form)?.cancel();
    form.classList.toggle("is-collapsed", !expanded);
    form.inert = !expanded;
    const after = getComputedStyle(form);
    const to = { height: `${form.getBoundingClientRect().height}px`, marginTop: after.marginTop, opacity: after.opacity };
    const focus = () => {
      if (expanded && form.isConnected && !form.classList.contains("is-collapsed")) {
        form.querySelector("input,textarea,select")?.focus({ preventScroll: true });
      }
    };
    if (reduced.matches) { focus(); return; }
    const animation = form.animate([from, to], { duration: 300, easing: "cubic-bezier(.22,.7,.2,1)" });
    formAnimations.set(form, animation);
    animation.onfinish = () => { formAnimations.delete(form); focus(); };
  };
  const names = ["远山湖泊", "辽阔海岸", "起伏草原", "风吹沙丘"];
  let customScenes = [];
  const sceneCount = () => customScenes.length || 4;
  const layers = [
    document.querySelector(".landscape-a"),
    document.querySelector(".landscape-b"),
  ];
  const atlas = new Image();
  atlas.src = "/static/images/landscapes/panoramas.png";
  let current = 0,
    front = 0,
    timer = null,
    transitionTimer = null,
    changing = false,
    ready = false;
  const read = (key, fallback) => {
    try {
      return localStorage.getItem(key) ?? fallback;
    } catch {
      return fallback;
    }
  };
  const save = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch {}
  };
  current = Math.max(0, Math.min(3, Number(read("glass_scene", "0")) || 0));
  let paused = reduced.matches;
  function fit(layer, index) {
    if (customScenes.length) {
      const scene = customScenes[index % customScenes.length];
      layer.style.backgroundImage = `url("${scene.url}")`;
      layer.style.backgroundSize = "cover";
      layer.style.backgroundPosition = "center";
      layer.dataset.scene = String(index % customScenes.length);
      return;
    }
    layer.style.backgroundImage = "";
    const ratio = (atlas.naturalWidth || 1586) / (atlas.naturalHeight || 992);
    const width = Math.max(innerWidth, innerHeight * ratio),
      height = width / ratio;
    const x = (index % 2) * width + (width - innerWidth) / 2,
      y = Math.floor(index / 2) * height + (height - innerHeight) / 2;
    layer.style.backgroundSize = `${width * 2}px ${height * 2}px`;
    layer.style.backgroundPosition = `${-x}px ${-y}px`;
    layer.dataset.scene = String(index);
  }
  function controls() {
    const title = document.getElementById("sceneName");
    if (title) title.textContent = customScenes[current]?.name || names[current];
    document.body.dataset.scene = String(current);
  }
  function schedule() {
    clearTimeout(timer);
    timer = null;
    if (ready && sceneCount() > 1 && !paused && !document.hidden && !changing)
      timer = setTimeout(next, 18000);
  }
  function next() {
    if (!ready || changing) return;
    clearTimeout(timer);
    current = (current + 1) % sceneCount();
    save("glass_scene", String(current));
    const back = 1 - front;
    fit(layers[back], current);
    if (reduced.matches) {
      layers[back].style.transition = "none";
      layers[front].style.transition = "none";
    }
    layers[back].style.opacity = "1";
    layers[front].style.opacity = "0";
    front = back;
    controls();
    changing = true;
    transitionTimer = setTimeout(
      () => {
        changing = false;
        schedule();
      },
      reduced.matches ? 0 : 2450,
    );
  }
  function applyBackgrounds(images) {
    clearTimeout(timer);
    clearTimeout(transitionTimer);
    changing = false;
    customScenes = images;
    current = 0;
    front = 0;
    layers.forEach((layer, index) => {
      fit(layer, index % sceneCount());
      layer.style.opacity = index === 0 ? "1" : "0";
    });
    controls();
    schedule();
  }
  document.addEventListener("saul:backgrounds", event => applyBackgrounds(event.detail));
  Promise.all([atlas.decode().catch(() => {}), window.saulBackgroundsReady || Promise.resolve([])])
    .then(([, images]) => {
      customScenes = images;
      current %= sceneCount();
      ready = true;
      fit(layers[front], current);
      fit(layers[1 - front], (current + 1) % sceneCount());
      controls();
      schedule();
    });
  document.addEventListener("visibilitychange", schedule);
  reduced.addEventListener("change", (e) => {
    paused = e.matches;
    layers.forEach((l) => (l.style.transition = ""));
    controls();
    schedule();
  });
  let resizeQueued = false;
  addEventListener("resize", () => {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => {
      resizeQueued = false;
      layers.forEach((l) => fit(l, Number(l.dataset.scene) || 0));
      selection();
    });
  });

  const nav = document.querySelector(".sidebar-nav");
  const marker = document.createElement("i");
  marker.className = "nav-selection";
  marker.setAttribute("aria-hidden", "true");
  nav.prepend(marker);
  nav.classList.add("is-animated");
  function selection() {
    const active = nav.querySelector("a.active");
    marker.hidden = !active;
    if (active) {
      marker.style.height = active.offsetHeight + "px";
      marker.style.transform = `translateY(${active.offsetTop}px)`;
    }
    nav.querySelectorAll("a").forEach((a) => {
      if (a === active) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }
  new MutationObserver(selection).observe(nav, {
    subtree: true,
    attributes: true,
    attributeFilter: ["class"],
  });
  selection();

  let modalObserver = null;
  function animatePage() {
    selection();
    document.querySelectorAll(".overseas-add-panel > .card-head, .card-notices-panel > .card-head").forEach((head) => {
      const button = head.querySelector(".form-toggle-btn");
      if (button) button.setAttribute("aria-label", `${head.querySelector("h2")?.textContent || "表单"}：展开或收起`);
    });
    modalObserver?.disconnect();
    const visibility = new WeakMap();
    modalObserver = new MutationObserver((records) => {
      for (const { target } of records) {
        const shown =
          getComputedStyle(target).display !== "none" &&
          getComputedStyle(target).visibility !== "hidden";
        const was = visibility.get(target);
        visibility.set(target, shown);
        if (shown && !was && !reduced.matches) {
          const panel =
            target.querySelector(
              ".board-card,.modal-dialog-card,.wallet-modal-dialog,.wallet-modal-content,.card-notice-modal-content",
            ) || target.firstElementChild;
          if (panel)
            panel.animate(
              [
                { opacity: 0, transform: "translateY(9px) scale(.98)" },
                { opacity: 1, transform: "translateY(0) scale(1)" },
              ],
              { duration: 260, easing: "cubic-bezier(.2,.8,.25,1)" },
            );
        }
      }
    });
    document
      .querySelectorAll('.modal,.modal-overlay,.wallet-modal,[id$="Modal"]')
      .forEach((el) => {
        visibility.set(el, getComputedStyle(el).display !== "none");
        modalObserver.observe(el, {
          attributes: true,
          attributeFilter: ["class", "style"],
        });
      });
  }
  document.addEventListener("saul:page-ready", animatePage);
  animatePage();
  const disclosureAnimations = new WeakMap();
  document.addEventListener("click", (event) => {
    const summary = event.target.closest("details.sidebar-utility > summary, details.expiry-disclosure > summary");
    if (!summary) return;
    const details = summary.parentElement;
    event.preventDefault();
    const initial = details.getBoundingClientRect().height;
    const closing = details.dataset.expanded === undefined ? details.open : details.dataset.expanded === "true";
    disclosureAnimations.get(details)?.cancel();
    details.dataset.expanded = String(!closing);
    summary.setAttribute("aria-expanded", String(!closing));
    if (reduced.matches) {
      details.open = !closing;
      details.style.overflow = "";
      disclosureAnimations.delete(details);
      return;
    }
    details.open = true;
    const style = getComputedStyle(details);
    const final = closing
      ? summary.getBoundingClientRect().height +
        parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) +
        parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth)
      : details.getBoundingClientRect().height;
    details.style.overflow = "hidden";
    const animation = details.animate([{ height: initial + "px" }, { height: final + "px" }], {
        duration: 140,
        easing: "cubic-bezier(.2,.8,.25,1)",
      });
    disclosureAnimations.set(details, animation);
    animation.onfinish = () => {
        if (disclosureAnimations.get(details) !== animation) return;
        details.open = !closing;
        details.style.overflow = "";
        disclosureAnimations.delete(details);
      };
  });
})();
