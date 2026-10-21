/* Shared option rows: draft rename/delete and handle-only sorting. */
(() => {
  "use strict";
  window.saulBindOptionOrder = (list, onOrder) => {
    const rows = [...list.children];
    let dragging = null;
    const finish = () => {
      if (!dragging) return;
      dragging.classList.remove("dragging");
      dragging = null;
      onOrder([...list.children].map(row => Number(row.dataset.optionIndex)));
    };
    const move = (row, y) => {
      if (!row || row === dragging || row.parentElement !== list) return;
      const rect = row.getBoundingClientRect();
      list.insertBefore(dragging, y < rect.top + rect.height / 2 ? row : row.nextSibling);
    };
    rows.forEach((row, index) => {
      row.dataset.optionIndex = String(index);
      row.classList.add("option-manager-row");
      row.draggable = false;
      const handle = row.querySelector(".option-manager-handle");
      if (!handle) return;
      handle.draggable = true;
      handle.title = "拖动排序，也可用键盘上下箭头调整";
      handle.setAttribute("aria-label", "调整选项顺序");
      handle.addEventListener("keydown", event => {
        if (!["ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        const position = [...list.children].indexOf(row);
        const target = position + (event.key === "ArrowUp" ? -1 : 1);
        if (target < 0 || target >= list.children.length) return;
        dragging = row;
        const sibling = list.children[target];
        list.insertBefore(row, event.key === "ArrowUp" ? sibling : sibling.nextSibling);
        finish();
        list.children[target]?.querySelector(".option-manager-handle")?.focus();
      });
      handle.addEventListener("dragstart", event => {
        dragging = row;
        row.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(index));
      });
      row.addEventListener("dragover", event => {
        if (!dragging) return;
        event.preventDefault();
        move(row, event.clientY);
      });
      row.addEventListener("drop", event => { event.preventDefault(); finish(); });
      handle.addEventListener("dragend", finish);
      handle.addEventListener("pointerdown", event => {
        if (event.pointerType === "mouse") return;
        dragging = row;
        row.classList.add("dragging");
        handle.setPointerCapture(event.pointerId);
      });
      handle.addEventListener("pointermove", event => {
        if (!dragging || event.pointerType === "mouse") return;
        move(document.elementFromPoint(event.clientX, event.clientY)?.closest(".option-manager-row"), event.clientY);
      });
      handle.addEventListener("pointerup", finish);
      handle.addEventListener("pointercancel", () => {
        if (!dragging) return;
        // Cancel restores the original order and never updates the draft.
        rows.forEach(item => list.append(item));
        dragging.classList.remove("dragging");
        dragging = null;
      });
    });
  };
  window.saulRenderOptionList = (list, values, onChange, onError = () => {}) => {
    list.classList.add("option-manager-list");
    list.replaceChildren();
    list.commitOptionEdit = () => true;
    values.forEach((name, index) => {
      const row = document.createElement("div");
      row.className = "option-manager-row";
      const left = document.createElement("div");
      left.className = "option-manager-label";
      const handle = document.createElement("button");
      handle.type = "button";
      handle.className = "option-manager-handle";
      handle.textContent = "≡";
      const label = document.createElement("span");
      label.textContent = name;
      left.append(handle, label);
      const actions = document.createElement("div");
      actions.className = "option-manager-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.dataset.micro = "edit";
      edit.setAttribute("aria-label", `修改${name}`);
      edit.title = "修改名称";
      edit.addEventListener("click", () => {
        if (label.querySelector("input")) { list.commitOptionEdit(); return; }
        if (!list.commitOptionEdit()) return;
        const input = document.createElement("input");
        input.value = name;
        input.maxLength = 80;
        input.setAttribute("aria-label", "选项名称");
        label.replaceChildren(input);
        let active = true;
        const commit = () => {
          if (!active) return true;
          const value = input.value.trim();
          if (!value || values.some((item, i) => i !== index && item === value)) {
            onError("名称不能为空或与其他选项重复。");
            input.focus();
            return false;
          }
          active = false;
          const next = [...values]; next[index] = value;
          onError(""); onChange(next);
          return true;
        };
        list.commitOptionEdit = commit;
        input.addEventListener("keydown", event => {
          if (event.key === "Enter") { event.preventDefault(); commit(); }
          if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); active = false; onChange([...values]); }
        });
        input.focus(); input.select();
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.dataset.micro = "delete";
      remove.setAttribute("aria-label", `删除${name}`);
      remove.title = "删除选项";
      remove.addEventListener("click", () => onChange(values.filter((_, i) => i !== index)));
      actions.append(edit, remove);
      row.append(left, actions);
      list.append(row);
    });
    window.saulBindOptionOrder(list, order => onChange(order.map(index => values[index])));
  };
})();
