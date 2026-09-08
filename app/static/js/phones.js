document.addEventListener("DOMContentLoaded", () => {
    const phoneAddForm = document.getElementById("phoneAddForm");
    const togglePhoneAddForm = document.getElementById("togglePhoneAddForm");
    togglePhoneAddForm?.addEventListener("click", () => {
        const expanded = phoneAddForm?.classList.contains("is-collapsed") ?? false;
        phoneAddForm?.classList.toggle("is-collapsed", !expanded);
        togglePhoneAddForm.setAttribute("aria-expanded", String(expanded));
        togglePhoneAddForm.textContent = expanded ? "收起" : "添加号码";
        if (expanded) window.setTimeout(() => phoneAddForm?.querySelector("input")?.focus(), 220);
    });

    // Date helpers
    function addDays(dateStr, days) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return "";
        date.setDate(date.getDate() + parseInt(days));
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    function syncExpiryDate(rechargeId, intervalId, expiryId) {
        const rechargeInput = document.getElementById(rechargeId);
        const intervalSelect = document.getElementById(intervalId);
        const expiryInput = document.getElementById(expiryId);
        
        if (!rechargeInput || !intervalSelect || !expiryInput) return;
        
        const val = rechargeInput.value;
        const interval = intervalSelect.value;
        
        if (interval === "custom") {
            return;
        }
        
        const days = parseInt(interval);
        if (isNaN(days)) return;
        
        const calculatedDate = addDays(val, days);
        if (calculatedDate) {
            expiryInput.value = calculatedDate;
        }
    }

    // Custom Dialog helper functions returning Promises
    const customConfirmModal = document.getElementById("customConfirmModal");
    const customConfirmTitle = document.getElementById("customConfirmTitle");
    const customConfirmMessage = document.getElementById("customConfirmMessage");
    const customConfirmCancelBtn = document.getElementById("customConfirmCancelBtn");
    const customConfirmOkBtn = document.getElementById("customConfirmOkBtn");

    function showCustomConfirm(title, message) {
        return new Promise((resolve) => {
            customConfirmTitle.textContent = title || "确认操作";
            customConfirmMessage.textContent = message || "确定要执行此操作吗？";
            customConfirmModal.style.display = "flex";
            
            const cleanUp = () => {
                customConfirmModal.style.display = "none";
                customConfirmOkBtn.removeEventListener("click", onOk);
                customConfirmCancelBtn.removeEventListener("click", onCancel);
            };
            
            const onOk = () => { cleanUp(); resolve(true); };
            const onCancel = () => { cleanUp(); resolve(false); };
            
            customConfirmOkBtn.addEventListener("click", onOk);
            customConfirmCancelBtn.addEventListener("click", onCancel);
        });
    }

    const customPromptModal = document.getElementById("customPromptModal");
    const customPromptTitle = document.getElementById("customPromptTitle");
    const customPromptLabel = document.getElementById("customPromptLabel");
    const customPromptInput = document.getElementById("customPromptInput");
    const customPromptDaysLabel = document.getElementById("customPromptDaysLabel");
    const customPromptDaysInput = document.getElementById("customPromptDaysInput");
    const customPromptCancelBtn = document.getElementById("customPromptCancelBtn");
    const customPromptOkBtn = document.getElementById("customPromptOkBtn");

    function showCustomPrompt(title, label, defaultValue = "", showDays = false, defaultDays = "") {
        return new Promise((resolve) => {
            customPromptTitle.textContent = title || "输入内容";
            customPromptLabel.textContent = label || "内容：";
            customPromptInput.value = defaultValue;
            
            if (showDays) {
                customPromptDaysLabel.style.display = "flex";
                customPromptDaysInput.value = defaultDays;
            } else {
                customPromptDaysLabel.style.display = "none";
            }
            
            customPromptModal.style.display = "flex";
            customPromptInput.focus();
            
            const cleanUp = () => {
                customPromptModal.style.display = "none";
                customPromptOkBtn.removeEventListener("click", onOk);
                customPromptCancelBtn.removeEventListener("click", onCancel);
            };
            
            const onOk = () => {
                const val = customPromptInput.value.trim();
                if (showDays) {
                    const daysVal = parseInt(customPromptDaysInput.value.trim());
                    cleanUp();
                    resolve({ value: val, days: daysVal });
                } else {
                    cleanUp();
                    resolve(val);
                }
            };
            const onCancel = () => { cleanUp(); resolve(null); };
            
            customPromptOkBtn.addEventListener("click", onOk);
            customPromptCancelBtn.addEventListener("click", onCancel);
        });
    }

    // Default current date on Add recharge date input
    const addRecharge = document.getElementById("addPhoneRecharge");
    if (addRecharge && !addRecharge.value) {
        const today = new Date();
        const y = today.getFullYear();
        const m = String(today.getMonth() + 1).padStart(2, '0');
        const d = String(today.getDate()).padStart(2, '0');
        addRecharge.value = `${y}-${m}-${d}`;
    }

    // Auto-calculate on Add Phone form changes
    if (addRecharge) {
        addRecharge.addEventListener("change", () => syncExpiryDate("addPhoneRecharge", "addPhoneInterval", "addPhoneExpiry"));
        document.getElementById("addPhoneInterval").addEventListener("change", () => syncExpiryDate("addPhoneRecharge", "addPhoneInterval", "addPhoneExpiry"));
        // Run initial calculation
        syncExpiryDate("addPhoneRecharge", "addPhoneInterval", "addPhoneExpiry");
    }

    // Select helper
    function selectOrAddOption(selectElement, val) {
        if (!val) return;
        let exists = false;
        for (let i = 0; i < selectElement.options.length; i++) {
            if (selectElement.options[i].value === val) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = val;
            selectElement.appendChild(opt);
        }
        selectElement.value = val;
    }

    // Dynamic Options Management
    const manageModal = document.getElementById("manageOptionsModal");
    const manageTitle = document.getElementById("manageOptionsTitle");
    const newOptionInput = document.getElementById("newOptionInput");
    const addOptionBtn = document.getElementById("addOptionBtn");
    const optionsContainer = document.getElementById("optionsListContainer");
    const closeManageBtn = document.getElementById("closeManageModalBtn");
    const closeManageBtn2 = document.getElementById("closeManageModalBtn2");

    // Dynamic addition of days input for duration type
    let daysInput = document.getElementById("newOptionDaysInput");
    if (!daysInput) {
        daysInput = document.createElement("input");
        daysInput.type = "number";
        daysInput.id = "newOptionDaysInput";
        daysInput.placeholder = "天数";
        daysInput.min = "1";
        daysInput.style.width = "70px";
        daysInput.style.padding = "8px";
        daysInput.style.borderRadius = "8px";
        daysInput.style.border = "1px solid var(--line)";
        daysInput.style.fontSize = "14px";
        daysInput.style.outline = "none";
        daysInput.style.background = "white";
        daysInput.style.color = "var(--text)";
        daysInput.style.display = "none";
        newOptionInput.parentNode.insertBefore(daysInput, addOptionBtn);
    }

    let currentOptions = { countries: [], durations: [], phones: [] };
    let activeOptionType = "country"; // "country", "duration", or "phone"

    async function openManageModal(type) {
        activeOptionType = type || "country";
        newOptionInput.value = "";
        if (daysInput) {
            daysInput.value = "";
            daysInput.style.display = activeOptionType === "duration" ? "block" : "none";
        }
        
        if (activeOptionType === "country") {
            manageTitle.textContent = "管理国家选项";
            newOptionInput.placeholder = "输入新国家名称...";
        } else {
            manageTitle.textContent = "管理到期时长选项";
            newOptionInput.placeholder = "输入展示名称(如: 30天)...";
        }

        try {
            const res = await fetch("/api/phones/options");
            if (!res.ok) throw new Error("加载选项失败");
            currentOptions = await res.json();
            if (!currentOptions.durations) currentOptions.durations = [];
            renderManageOptionsList();
            manageModal.style.display = "flex";
        } catch (err) {
            showToast("加载选项失败: " + err.message, true);
        }
    }

    function renderManageOptionsList() {
        optionsContainer.innerHTML = "";
        const list = activeOptionType === "country" ? currentOptions.countries : currentOptions.durations;
        
        list.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "draggable-option-item";
            row.draggable = true;
            row.style.display = "flex";
            row.style.justifyContent = "space-between";
            row.style.alignItems = "center";
            row.style.padding = "8px 12px";
            row.style.background = "white";
            row.style.borderRadius = "8px";
            row.style.border = "1px solid var(--line)";
            row.style.fontSize = "14px";
            row.style.marginBottom = "6px";
            row.style.cursor = "grab";
            row.style.transition = "all 0.15s ease";

            if (activeOptionType === "country") {
                row.dataset.value = item;
            } else {
                row.dataset.name = item.name;
                row.dataset.days = item.days;
            }

            // Drag event listeners
            row.addEventListener("dragstart", (e) => {
                row.classList.add("dragging");
                e.dataTransfer.effectAllowed = "move";
                setTimeout(() => {
                    row.style.opacity = "0.4";
                    row.style.background = "var(--bg)";
                }, 0);
            });

            row.addEventListener("dragend", () => {
                row.classList.remove("dragging");
                row.style.opacity = "";
                row.style.background = "white";
                reorderOptionsFromDOM();
            });

            // Touch event listeners for mobile drag
            row.addEventListener("touchstart", (e) => {
                row.classList.add("dragging");
                row.style.opacity = "0.4";
                row.style.background = "var(--bg)";
            });

            row.addEventListener("touchmove", (e) => {
                e.preventDefault();
                const touch = e.touches[0];
                const draggingElement = document.querySelector(".dragging");
                if (!draggingElement) return;

                const elementAtTouch = document.elementFromPoint(touch.clientX, touch.clientY);
                if (!elementAtTouch) return;
                
                const targetRow = elementAtTouch.closest(".draggable-option-item");
                if (targetRow && targetRow !== draggingElement && targetRow.parentNode === optionsContainer) {
                    const bounding = targetRow.getBoundingClientRect();
                    const offset = touch.clientY - bounding.top - bounding.height / 2;
                    if (offset < 0) {
                        optionsContainer.insertBefore(draggingElement, targetRow);
                    } else {
                        optionsContainer.insertBefore(draggingElement, targetRow.nextSibling);
                    }
                }
            });

            row.addEventListener("touchend", () => {
                row.classList.remove("dragging");
                row.style.opacity = "";
                row.style.background = "white";
                reorderOptionsFromDOM();
            });
            
            const leftPart = document.createElement("div");
            leftPart.style.display = "flex";
            leftPart.style.alignItems = "center";
            leftPart.style.gap = "10px";

            const handle = document.createElement("span");
            handle.textContent = "☰";
            handle.style.color = "var(--muted)";
            handle.style.cursor = "grab";
            handle.style.userSelect = "none";
            leftPart.appendChild(handle);
            
            const textSpan = document.createElement("span");
            if (activeOptionType === "country") {
                textSpan.textContent = item;
            } else {
                textSpan.textContent = `${item.name} (${item.days}天)`;
            }
            textSpan.style.fontWeight = "500";
            leftPart.appendChild(textSpan);
            row.appendChild(leftPart);
            
            const actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "8px";
            
            const editBtn = document.createElement("button");
            editBtn.type = "button";
            editBtn.innerHTML = "✏️";
            editBtn.style.background = "none";
            editBtn.style.border = "none";
            editBtn.style.cursor = "pointer";
            editBtn.style.padding = "2px";
            editBtn.title = "重命名";
            editBtn.addEventListener("click", async () => {
                if (activeOptionType === "country") {
                    const newName = await showCustomPrompt("修改国家名称", "国家名称：", item);
                    if (newName && newName.trim() && newName.trim() !== item) {
                        currentOptions.countries[index] = newName.trim();
                        saveOptionsToServer();
                    }
                } else {
                    const result = await showCustomPrompt("修改到期时长", "展示名称：", item.name, true, item.days);
                    if (result && result.value) {
                        if (!isNaN(result.days) && result.days > 0) {
                            currentOptions.durations[index] = {
                                name: result.value.trim(),
                                days: result.days
                            };
                            saveOptionsToServer();
                        } else {
                            showToast("天数必须为大于 0 的数字", true);
                        }
                    }
                }
            });
            actions.appendChild(editBtn);
            
            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.innerHTML = "❌";
            delBtn.style.background = "none";
            delBtn.style.border = "none";
            delBtn.style.cursor = "pointer";
            delBtn.style.padding = "2px";
            delBtn.title = "删除";
            delBtn.addEventListener("click", async () => {
                const nameToDelete = activeOptionType === "country" ? item : item.name;
                const ok = await showCustomConfirm("删除确认", `确定要删除此选项 "${nameToDelete}" 吗？`);
                if (ok) {
                    if (activeOptionType === "country") {
                        currentOptions.countries.splice(index, 1);
                    } else {
                        currentOptions.durations.splice(index, 1);
                    }
                    saveOptionsToServer();
                }
            });
            actions.appendChild(delBtn);
            
            row.appendChild(actions);
            optionsContainer.appendChild(row);
        });
    }

    function reorderOptionsFromDOM() {
        const rows = Array.from(optionsContainer.querySelectorAll(".draggable-option-item"));
        if (activeOptionType === "country") {
            const newCountries = rows.map(r => r.dataset.value);
            currentOptions.countries = newCountries;
        } else {
            const newDurations = rows.map(r => ({
                name: r.dataset.name,
                days: parseInt(r.dataset.days)
            }));
            currentOptions.durations = newDurations;
        }
        saveOptionsToServer(true);
    }

    async function saveOptionsToServer(skipRender = false) {
        try {
            const res = await fetch("/api/phones/options", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(currentOptions)
            });
            if (!res.ok) throw new Error("保存选项失败");
            
            if (!skipRender) {
                renderManageOptionsList();
            }
            updateAllDOMSelects();
            showToast("选项已更新");
        } catch (err) {
            showToast("保存选项失败: " + err.message, true);
        }
    }

    function updateAllDOMSelects() {
        if (activeOptionType === "country") {
            const addCountrySelect = document.getElementById("addPhoneCountry");
            const editCountrySelect = document.getElementById("editPhoneCountry");
            
            const addVal = addCountrySelect.value;
            const editVal = editCountrySelect.value;
            
            [addCountrySelect, editCountrySelect].forEach(select => {
                if (!select) return;
                select.innerHTML = "";
                currentOptions.countries.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            
            if (addCountrySelect) selectOrAddOption(addCountrySelect, addVal);
            if (editCountrySelect) selectOrAddOption(editCountrySelect, editVal);
        } else {
            const addIntervalSelect = document.getElementById("addPhoneInterval");
            const editIntervalSelect = document.getElementById("editPhoneInterval");
            
            const addVal = addIntervalSelect.value;
            const editVal = editIntervalSelect.value;
            
            [addIntervalSelect, editIntervalSelect].forEach(select => {
                if (!select) return;
                select.innerHTML = "";
                
                const customOpt = document.createElement("option");
                customOpt.value = "custom";
                customOpt.textContent = "自定义";
                select.appendChild(customOpt);
                
                currentOptions.durations.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt.days;
                    o.textContent = opt.name;
                    select.appendChild(o);
                });
            });
            
            if (addIntervalSelect) addIntervalSelect.value = addVal;
            if (editIntervalSelect) editIntervalSelect.value = editVal;
            
            syncExpiryDate("addPhoneRecharge", "addPhoneInterval", "addPhoneExpiry");
            syncExpiryDate("editPhoneRecharge", "editPhoneInterval", "editPhoneExpiry");
        }
    }

    addOptionBtn.addEventListener("click", () => {
        const val = newOptionInput.value.trim();
        if (!val) return;
        
        if (activeOptionType === "country") {
            if (currentOptions.countries.includes(val)) {
                showToast("该国家选项已存在", true);
                return;
            }
            currentOptions.countries.push(val);
            newOptionInput.value = "";
            saveOptionsToServer();
        } else {
            const dVal = parseInt(daysInput.value.trim());
            if (isNaN(dVal) || dVal <= 0) {
                showToast("请输入有效天数", true);
                return;
            }
            if (currentOptions.durations.some(d => d.name === val)) {
                showToast("该展示名称已存在", true);
                return;
            }
            currentOptions.durations.push({
                name: val,
                days: dVal
            });
            newOptionInput.value = "";
            daysInput.value = "";
            saveOptionsToServer();
        }
    });

    newOptionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            addOptionBtn.click();
        }
    });

    document.querySelectorAll(".btn-manage-options").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            openManageModal(btn.dataset.type);
        });
    });

    const hideManageModal = () => { manageModal.style.display = "none"; };
    if (closeManageBtn) closeManageBtn.addEventListener("click", hideManageModal);
    if (closeManageBtn2) closeManageBtn2.addEventListener("click", hideManageModal);

    optionsContainer.addEventListener("dragover", (e) => {
        e.preventDefault();
        const draggingElement = document.querySelector(".dragging");
        if (!draggingElement) return;
        const afterElement = getDragAfterElement(optionsContainer, e.clientY);
        if (afterElement == null) {
            optionsContainer.appendChild(draggingElement);
        } else {
            optionsContainer.insertBefore(draggingElement, afterElement);
        }
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll(".draggable-option-item:not(.dragging)")];
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }


    const table = document.getElementById("phonesTable");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    const headers = table.querySelectorAll("thead th");
    const searchInput = document.getElementById("phonesSearchInput");
    
    const originalRows = Array.from(tbody.querySelectorAll("tr"));
    let filteredRows = [...originalRows];
    let sortColumnIndex = -1;
    let sortDirection = 1;

    let currentPage = parseInt(sessionStorage.getItem("phones_current_page")) || 1;
    const rowsPerPage = 10;

    const tableWrap = table.closest(".table-wrap");
    const paginationContainer = document.createElement("div");
    paginationContainer.className = "pagination-container";
    tableWrap.parentNode.insertBefore(paginationContainer, tableWrap.nextSibling);

    const expiryFilter = document.getElementById("expiryFilterCheckbox");
    if (expiryFilter) {
        expiryFilter.addEventListener("change", () => {
            currentPage = 1;
            updateTable();
        });
    }

    let selectedColorFilter = "";

    // Legend Badges Interactive Script
    const legendBadges = document.querySelectorAll(".color-legend-badge");
    const legendResetBtn = document.getElementById("colorLegendReset");

    legendBadges.forEach(badge => {
        badge.addEventListener("click", () => {
            const targetColor = badge.dataset.color;
            if (selectedColorFilter === targetColor) {
                // Toggle off
                selectedColorFilter = "";
                legendBadges.forEach(b => {
                    b.style.transform = "scale(1)";
                    b.style.opacity = "1";
                    b.style.boxShadow = "none";
                });
                if (legendResetBtn) legendResetBtn.style.display = "none";
            } else {
                selectedColorFilter = targetColor;
                legendBadges.forEach(b => {
                    if (b.dataset.color === targetColor) {
                        b.style.transform = "scale(1.06)";
                        b.style.opacity = "1";
                        b.style.boxShadow = "0 2px 8px rgba(0,0,0,0.15)";
                    } else {
                        b.style.transform = "scale(0.96)";
                        b.style.opacity = "0.5";
                        b.style.boxShadow = "none";
                    }
                });
                if (legendResetBtn) legendResetBtn.style.display = "inline-block";
            }
            currentPage = 1;
            updateTable();
        });
    });

    if (legendResetBtn) {
        legendResetBtn.addEventListener("click", () => {
            selectedColorFilter = "";
            legendBadges.forEach(b => {
                b.style.transform = "scale(1)";
                b.style.opacity = "1";
                b.style.boxShadow = "none";
            });
            legendResetBtn.style.display = "none";
            currentPage = 1;
            updateTable();
        });
    }

    function getDaysToExpiry(row) {
        const tds = row.querySelectorAll("td");
        if (tds.length < 6) return null;
        
        const statusCell = tds[3].textContent.trim();
        if (statusCell === "已关闭" || statusCell === "关闭") return null;
        
        const expiryTd = tds[5];
        const dateSpan = expiryTd.querySelector("span");
        const expiryCell = dateSpan ? dateSpan.textContent.trim() : expiryTd.textContent.trim();
        if (!expiryCell || expiryCell === "--") return null;
        
        const expiryDate = new Date(expiryCell);
        if (isNaN(expiryDate.getTime())) return null;
        
        const today = new Date();
        today.setHours(0,0,0,0);
        expiryDate.setHours(0,0,0,0);
        
        const diffTime = expiryDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
    }

    function updateTable() {
        // Highlight rows and add badges dynamically
        originalRows.forEach(row => {
            row.style.background = "";
            row.dataset.rowColor = "";
            const tds = row.querySelectorAll("td");
            if (tds.length < 6) return;
            
            const statusCell = tds[3].textContent.trim();
            const expiryTd = tds[5];
            
            const oldBadge = expiryTd.querySelector(".expiry-badge");
            if (oldBadge) oldBadge.remove();
            
            const days = getDaysToExpiry(row);

            // Rule 1: Closed status -> Yellow (#fefbeb)
            if (statusCell === "已关闭" || statusCell === "关闭") {
                row.style.background = "#fefbeb";
                row.dataset.rowColor = "#fefbeb";
            }
            // Rule 2: Pending/To-do status -> Green (#f0fdf4)
            else if (statusCell === "待激活" || statusCell.includes("待办")) {
                row.style.background = "#f0fdf4";
                row.dataset.rowColor = "#f0fdf4";
            }
            // Rule 3: Expiring or Expired -> Red (#fff5f5)
            else if (days !== null && days <= 15) {
                row.style.background = "#fff5f5";
                row.dataset.rowColor = "#fff5f5";

                const badge = document.createElement("span");
                badge.className = "expiry-badge";
                if (days < 0) {
                    badge.textContent = "已过期";
                } else {
                    badge.textContent = `临期 (${days}天)`;
                }
                badge.style.display = "inline-block";
                badge.style.marginLeft = "6px";
                badge.style.background = "#e53e3e";
                badge.style.color = "white";
                badge.style.fontSize = "11px";
                badge.style.padding = "1px 6px";
                badge.style.borderRadius = "4px";
                badge.style.fontWeight = "bold";
                expiryTd.appendChild(badge);
            }
        });

        const query = (searchInput.value || "").toLowerCase().trim();
        const showOnlyExpiring = expiryFilter ? expiryFilter.checked : false;

        filteredRows = originalRows.filter(row => {
            const rowColor = (row.dataset.rowColor || "").toLowerCase();

            // Legend Badge filter
            if (selectedColorFilter) {
                if (rowColor !== selectedColorFilter.toLowerCase()) return false;
            }

            // Expiry warning filter checkbox
            if (showOnlyExpiring) {
                const days = getDaysToExpiry(row);
                if (days === null || days > 15) return false;
            }

            if (!query) return true;

            // Semantic color search
            let queryMatchesColor = false;
            if ((query === '临期' || query === '过期' || query === '红色' || query === '红') && rowColor === '#fff5f5') queryMatchesColor = true;
            if ((query === '关闭' || query === '已关闭' || query === '黄色' || query === '黄') && rowColor === '#fefbeb') queryMatchesColor = true;
            if ((query === '待激活' || query === '待办' || query === '绿色' || query === '绿') && rowColor === '#f0fdf4') queryMatchesColor = true;
            if (queryMatchesColor) return true;

            return Array.from(row.querySelectorAll("td")).some((td, idx) => {
                if (idx === row.querySelectorAll("td").length - 1) return false;
                return td.textContent.toLowerCase().includes(query);
            });
        });

        if (sortColumnIndex !== -1) {
            filteredRows.sort((a, b) => {
                let cellA = a.querySelectorAll("td")[sortColumnIndex].textContent.trim();
                let cellB = b.querySelectorAll("td")[sortColumnIndex].textContent.trim();

                if (sortColumnIndex === 4 || sortColumnIndex === 5) {
                    const dateA = cellA === '--' ? 0 : new Date(cellA).getTime() || 0;
                    const dateB = cellB === '--' ? 0 : new Date(cellB).getTime() || 0;
                    return (dateA - dateB) * sortDirection;
                }

                return cellA.localeCompare(cellB, 'zh-CN') * sortDirection;
            });
        }

        const totalRows = filteredRows.length;
        const totalPages = Math.ceil(totalRows / rowsPerPage) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;
        sessionStorage.setItem("phones_current_page", currentPage);

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;

        tbody.innerHTML = "";
        filteredRows.forEach((row, idx) => {
            if (idx >= startIndex && idx < endIndex) {
                tbody.appendChild(row);
            }
        });

        renderPagination(totalRows, totalPages);
    }

    function renderPagination(totalRows, totalPages) {
        paginationContainer.innerHTML = "";
        
        const btnGroup = document.createElement("div");
        btnGroup.className = "pagination-controls";

        const prevBtn = document.createElement("button");
        prevBtn.type = "button";
        prevBtn.className = "page-btn";
        prevBtn.textContent = "« 上一页";
        prevBtn.disabled = currentPage === 1;
        prevBtn.addEventListener("click", () => {
            currentPage--;
            updateTable();
        });
        btnGroup.appendChild(prevBtn);

        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }

        for (let i = startPage; i <= endPage; i++) {
            if (i < 1 || i > totalPages) continue;
            const pageBtn = document.createElement("button");
            pageBtn.type = "button";
            pageBtn.textContent = i;
            pageBtn.className = "page-btn" + (i === currentPage ? " active" : "");
            pageBtn.addEventListener("click", () => {
                currentPage = i;
                updateTable();
            });
            btnGroup.appendChild(pageBtn);
        }

        const nextBtn = document.createElement("button");
        nextBtn.type = "button";
        nextBtn.className = "page-btn";
        nextBtn.textContent = "下一页 »";
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.addEventListener("click", () => {
            currentPage++;
            updateTable();
        });
        btnGroup.appendChild(nextBtn);

        paginationContainer.appendChild(btnGroup);
    }

    searchInput.addEventListener("input", () => {
        currentPage = 1;
        updateTable();
    });

    headers.forEach((th, idx) => {
        if (idx === headers.length - 1) return;

        th.style.cursor = "pointer";
        th.style.userSelect = "none";
        th.style.transition = "all 0.2s";
        th.style.paddingRight = "18px";
        th.style.position = "relative";

        th.addEventListener("mouseenter", () => {
            th.style.color = "#ff4a3d";
        });
        th.addEventListener("mouseleave", () => {
            if (sortColumnIndex !== idx) {
                th.style.color = "";
            }
        });

        th.addEventListener("click", () => {
            headers.forEach((h, hidx) => {
                if (hidx === headers.length - 1) return;
                h.style.color = "";
                h.setAttribute("aria-sort", "none");
                const text = h.textContent.replace(/[⇅▲▼]/g, "").trim();
                h.innerHTML = `${text} <span class="sort-indicator" data-direction="none" aria-hidden="true"></span>`;
            });

            if (sortColumnIndex === idx) {
                sortDirection = -sortDirection;
            } else {
                sortColumnIndex = idx;
                sortDirection = 1;
            }

            th.setAttribute("aria-sort", sortDirection === 1 ? "ascending" : "descending");
            const text = th.textContent.replace(/[⇅▲▼]/g, "").trim();
            th.innerHTML = `${text} <span class="sort-indicator" data-direction="${sortDirection === 1 ? 'asc' : 'desc'}" aria-hidden="true"></span>`;
            th.style.color = "#ff4a3d";

            updateTable();
        });

        const text = th.textContent.trim();
        th.innerHTML = `${text} <span class="sort-indicator" data-direction="none" aria-hidden="true"></span>`;
    });

    updateTable();

    // Edit Phone Modal
    const editModal = document.getElementById("editPhoneModal");
    const editForm = document.getElementById("editPhoneForm");
    const closeBtn = document.getElementById("closeEditModalBtn");
    const cancelBtn = document.getElementById("cancelEditModalBtn");
    
    const editNameInput = document.getElementById("editPhoneName");
    const editPhoneInput = document.getElementById("editPhoneNo");
    const editCountryInput = document.getElementById("editPhoneCountry");
    const editStatusInput = document.getElementById("editPhoneStatus");
    const editRechargeInput = document.getElementById("editPhoneRecharge");
    const editExpiryInput = document.getElementById("editPhoneExpiry");
    const editRenewalInput = document.getElementById("editPhoneRenewal");
    const editNoteInput = document.getElementById("editPhoneNote");

    if (editRechargeInput) {
        editRechargeInput.addEventListener("change", () => syncExpiryDate("editPhoneRecharge", "editPhoneInterval", "editPhoneExpiry"));
        document.getElementById("editPhoneInterval").addEventListener("change", () => syncExpiryDate("editPhoneRecharge", "editPhoneInterval", "editPhoneExpiry"));
    }

    let activeEditingRow = null;
    let activeDeletingRow = null;

    function showToast(message, isError = false) {
        let banner = document.getElementById("noticeBanner");
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "noticeBanner";
            banner.className = isError ? "banner banner-error" : "banner banner-notice";
            banner.style.position = "fixed";
            banner.style.top = "20px";
            banner.style.right = "20px";
            banner.style.zIndex = "9999";
            banner.style.display = "flex";
            banner.style.justifyContent = "space-between";
            banner.style.alignItems = "center";
            banner.style.transition = "opacity 0.5s ease";
            banner.style.boxShadow = "var(--shadow)";
            banner.style.minWidth = "300px";
            document.body.appendChild(banner);
        } else {
            banner.className = isError ? "banner banner-error" : "banner banner-notice";
        }
        banner.style.display = "flex";
        banner.style.opacity = "1";
        banner.innerHTML = `
            <span>${message}</span>
            <button type="button" onclick="const b = document.getElementById('noticeBanner'); if(b){b.style.opacity='0'; setTimeout(()=>b.style.display='none', 500);}" style="background: none; border: none; color: inherit; font-size: 20px; cursor: pointer; line-height: 1; padding: 0 4px;">&times;</button>
        `;
        setTimeout(() => {
            banner.style.opacity = "0";
            setTimeout(() => banner.style.display = "none", 500);
        }, 3000);
    }

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".edit-phone-btn");
        if (btn) {
            activeEditingRow = btn.closest("tr");
            const id = btn.dataset.id;
            const name = btn.dataset.name;
            const phone = btn.dataset.phone;
            const country = btn.dataset.country;
            const status = btn.dataset.status;
            const recharge = btn.dataset.recharge;
            const expiry = btn.dataset.expiry;
            const renewal = btn.dataset.renewal;
            const note = btn.dataset.note;

            editForm.action = `/phones/${id}/update`;
            editNameInput.value = name;
            editPhoneInput.value = phone;
            selectOrAddOption(editCountryInput, country);
            editStatusInput.value = status;
            
            const cleanRecharge = (recharge && recharge !== "--") ? recharge : "";
            const cleanExpiry = (expiry && expiry !== "--") ? expiry : "";
            editRechargeInput.value = cleanRecharge;
            editExpiryInput.value = cleanExpiry;
            editRenewalInput.value = renewal || "";
            editNoteInput.value = note || "";

            // Guess interval
            let guessedInterval = "custom";
            if (cleanRecharge && cleanExpiry) {
                const rDate = new Date(cleanRecharge);
                const eDate = new Date(cleanExpiry);
                if (!isNaN(rDate.getTime()) && !isNaN(eDate.getTime())) {
                    const diffTime = Math.abs(eDate - rDate);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    const intervalSelect = document.getElementById("editPhoneInterval");
                    for (let i = 0; i < intervalSelect.options.length; i++) {
                        if (intervalSelect.options[i].value === String(diffDays)) {
                            guessedInterval = String(diffDays);
                            break;
                        }
                    }
                }
            }
            document.getElementById("editPhoneInterval").value = guessedInterval;

            editModal.style.display = "flex";
        }
    });

    const hideEditModal = () => {
        editModal.style.display = "none";
        activeEditingRow = null;
    };

    if (closeBtn) closeBtn.addEventListener("click", hideEditModal);
    if (cancelBtn) cancelBtn.addEventListener("click", hideEditModal);

    editForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(editForm);
        try {
            const response = await fetch(editForm.action, {
                method: "POST",
                body: formData
            });
            if (!response.ok) throw new Error("HTTP error " + response.status);

            if (activeEditingRow) {
                const name = editNameInput.value;
                const phone = editPhoneInput.value;
                const country = editCountryInput.value;
                const status = editStatusInput.value;
                const recharge = editRechargeInput.value;
                const expiry = editExpiryInput.value;
                const renewal = editRenewalInput.value;
                const note = editNoteInput.value;

                activeEditingRow.cells[0].querySelector("strong").textContent = name;
                activeEditingRow.cells[1].querySelector("span").textContent = phone;
                activeEditingRow.cells[2].querySelector("span").textContent = country;
                
                const statusSpan = activeEditingRow.cells[3].querySelector(".badge-status");
                if (statusSpan) {
                    statusSpan.textContent = status;
                    statusSpan.className = "badge-status " + (
                        status === '已激活' ? 'badge-status-active' :
                        status === '待激活' ? 'badge-status-pending' : 'badge-status-closed'
                    );
                }
                
                activeEditingRow.cells[4].querySelector("span").textContent = recharge || "--";
                activeEditingRow.cells[5].querySelector("span").textContent = expiry || "--";
                activeEditingRow.cells[6].querySelector("span").textContent = renewal || "--";
                activeEditingRow.cells[7].textContent = note || "--";

                const editBtn = activeEditingRow.querySelector(".edit-phone-btn");
                if (editBtn) {
                    editBtn.dataset.name = name;
                    editBtn.dataset.phone = phone;
                    editBtn.dataset.country = country;
                    editBtn.dataset.status = status;
                    editBtn.dataset.recharge = recharge;
                    editBtn.dataset.expiry = expiry;
                    editBtn.dataset.renewal = renewal;
                    editBtn.dataset.note = note;
                }
                const deleteBtn = activeEditingRow.querySelector(".delete-card-btn");
                if (deleteBtn) {
                    deleteBtn.dataset.name = `${name} (${phone})`;
                }
            }

            hideEditModal();
            updateTable();
            showToast("成功更新号码记录");
        } catch (error) {
            console.error("更新号码失败:", error);
            showToast("更新号码失败: " + error.message, true);
        }
    });

    // Delete Phone Modal
    const deleteModal = document.getElementById("deletePhoneModal");
    const deleteForm = document.getElementById("deletePhoneForm");
    const closeDeleteBtn = document.getElementById("closeDeleteModalBtn");
    const cancelDeleteBtn = document.getElementById("cancelDeleteModalBtn");
    const deleteNameSpan = document.getElementById("deletePhoneNameSpan");

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".delete-phone-btn");
        if (btn) {
            activeDeletingRow = btn.closest("tr");
            const id = btn.dataset.id;
            const name = btn.dataset.name;

            deleteForm.action = `/phones/${id}/delete`;
            deleteNameSpan.textContent = name;

            deleteModal.style.display = "flex";
        }
    });

    const hideDeleteModal = () => {
        deleteModal.style.display = "none";
        activeDeletingRow = null;
    };

    if (closeDeleteBtn) closeDeleteBtn.addEventListener("click", hideDeleteModal);
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener("click", hideDeleteModal);

    deleteForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            const response = await fetch(deleteForm.action, {
                method: "POST"
            });
            if (!response.ok) throw new Error("HTTP error " + response.status);

            if (activeDeletingRow) {
                const idx = originalRows.indexOf(activeDeletingRow);
                if (idx !== -1) {
                    originalRows.splice(idx, 1);
                }
                updateTable();
            }

            hideDeleteModal();
            showToast("成功删除号码记录");
        } catch (error) {
            console.error("删除号码失败:", error);
            showToast("删除号码失败: " + error.message, true);
        }
    });

    const handlePhoneModalWindowClick = (event) => {
        if (event.target === editModal) {
            hideEditModal();
        }
        if (event.target === deleteModal) {
            hideDeleteModal();
        }
        if (event.target === manageModal) {
            hideManageModal();
        }
    };
    window.addEventListener("click", handlePhoneModalWindowClick);

    window.pjaxCleanupTasks = window.pjaxCleanupTasks || [];
    window.pjaxCleanupTasks.push(() => {
        window.removeEventListener("click", handlePhoneModalWindowClick);
    });

    const sidebarPhoneLinks = document.querySelectorAll('a[href="/phones"]');
    sidebarPhoneLinks.forEach(link => {
        link.addEventListener("click", () => {
            sessionStorage.setItem("phones_current_page", 1);
        });
    });
});
