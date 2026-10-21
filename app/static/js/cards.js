document.addEventListener("DOMContentLoaded", () => {
    const cardNoticeForm = document.getElementById("cardNoticeForm");
    const toggleCardNoticeForm = document.getElementById("toggleCardNoticeForm");
    const cardNoticesPanel = document.querySelector(".card-notices-panel");
    toggleCardNoticeForm?.addEventListener("click", () => {
        const expanded = cardNoticeForm?.classList.contains("is-collapsed") ?? false;
        window.saulSetFormExpanded(cardNoticeForm, expanded);
        cardNoticesPanel?.classList.toggle("is-managing", expanded);
        toggleCardNoticeForm.setAttribute("aria-expanded", String(expanded));
        toggleCardNoticeForm.textContent = expanded ? "收起" : "添加事项";
    });

    const editCardNoticeModal = document.getElementById("editCardNoticeModal");
    const editCardNoticeForm = document.getElementById("editCardNoticeForm");
    const editCardNoticeContent = document.getElementById("editCardNoticeContent");
    const closeEditCardNoticeBtn = document.getElementById("closeEditCardNoticeBtn");
    const cancelEditCardNoticeBtn = document.getElementById("cancelEditCardNoticeBtn");
    let activeCardNoticeItem = null;

    const hideCardNoticeModal = () => {
        if (editCardNoticeModal) editCardNoticeModal.style.display = "none";
        activeCardNoticeItem = null;
    };

    document.querySelectorAll(".edit-card-notice-btn").forEach((button) => {
        button.addEventListener("click", () => {
            activeCardNoticeItem = button.closest(".card-notice-item");
            editCardNoticeForm.action = `/cards/notices/${button.dataset.id}/update`;
            editCardNoticeContent.value = button.dataset.content || "";
            editCardNoticeModal.style.display = "flex";
            window.setTimeout(() => editCardNoticeContent.focus(), 0);
        });
    });

    closeEditCardNoticeBtn?.addEventListener("click", hideCardNoticeModal);
    cancelEditCardNoticeBtn?.addEventListener("click", hideCardNoticeModal);

    editCardNoticeForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            const response = await fetch(editCardNoticeForm.action, {
                method: "POST",
                body: new FormData(editCardNoticeForm),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || "保存失败");
            const content = data.content || editCardNoticeContent.value.trim();
            activeCardNoticeItem?.querySelector(".card-notice-content")?.replaceChildren(content);
            const editButton = activeCardNoticeItem?.querySelector(".edit-card-notice-btn");
            if (editButton) editButton.dataset.content = content;
            hideCardNoticeModal();
            showToast("注意事项已更新");
        } catch (error) {
            showToast(`注意事项更新失败：${error.message}`, true);
        }
    });

    const cardAddForm = document.getElementById("cardAddForm");
    const toggleCardAddForm = document.getElementById("toggleCardAddForm");
    toggleCardAddForm?.addEventListener("click", () => {
        const expanded = cardAddForm?.classList.contains("is-collapsed") ?? false;
        window.saulSetFormExpanded(cardAddForm, expanded);
        toggleCardAddForm.setAttribute("aria-expanded", String(expanded));
        toggleCardAddForm.textContent = expanded ? "收起" : "添加工具";
    });

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
    const customPromptCancelBtn = document.getElementById("customPromptCancelBtn");
    const customPromptOkBtn = document.getElementById("customPromptOkBtn");

    function showCustomPrompt(title, label, defaultValue = "") {
        return new Promise((resolve) => {
            customPromptTitle.textContent = title || "输入内容";
            customPromptLabel.textContent = label || "内容：";
            customPromptInput.value = defaultValue;
            
            customPromptModal.style.display = "flex";
            customPromptInput.focus();
            
            const cleanUp = () => {
                customPromptModal.style.display = "none";
                customPromptOkBtn.removeEventListener("click", onOk);
                customPromptCancelBtn.removeEventListener("click", onCancel);
            };
            
            const onOk = () => {
                const val = customPromptInput.value.trim();
                cleanUp();
                resolve(val);
            };
            const onCancel = () => { cleanUp(); resolve(null); };
            
            customPromptOkBtn.addEventListener("click", onOk);
            customPromptCancelBtn.addEventListener("click", onCancel);
        });
    }

    // Dynamic Options Management
    const manageModal = document.getElementById("manageOptionsModal");
    const manageTitle = document.getElementById("manageOptionsTitle");
    const newOptionInput = document.getElementById("newOptionInput");
    const addOptionBtn = document.getElementById("addOptionBtn");
    const optionsContainer = document.getElementById("optionsListContainer");
    const closeManageBtn = document.getElementById("closeManageModalBtn");
    const closeManageBtn2 = document.getElementById("closeManageModalBtn2");

    let currentManageType = ""; // "kyc", "type", "country", "login", "phone", "color", or "address"
    let currentOptions = { kyc_methods: [], types: [], countries: [], login_methods: [], phones: [], colors: [], addresses: [] };

    async function openManageModal(type) {
        currentManageType = type;
        if (type === "kyc") {
            manageTitle.textContent = "管理 KYC 申请方式选项";
            newOptionInput.placeholder = "输入新选项名称...";
        } else if (type === "kyc_provider") {
            manageTitle.textContent = "管理 KYC 提供商选项";
            newOptionInput.placeholder = "输入新 KYC 提供商名称...";
        } else if (type === "type") {
            manageTitle.textContent = "管理工具类型选项";
            newOptionInput.placeholder = "输入新选项名称...";
        } else if (type === "login") {
            manageTitle.textContent = "管理登录方式选项";
            newOptionInput.placeholder = "输入新登录方式...";
        } else if (type === "phone") {
            manageTitle.textContent = "管理电话号码选项";
            newOptionInput.placeholder = "输入新电话号码...";
        } else if (type === "address") {
            manageTitle.textContent = "管理证明地址选项";
            newOptionInput.placeholder = "输入新证明地址...";
        } else if (type === "color") {
            manageTitle.textContent = "管理行高亮颜色选项";
            newOptionInput.placeholder = "输入新颜色展示名(如:粉色)...";
        } else {
            manageTitle.textContent = "管理国家 / 地区选项";
            newOptionInput.placeholder = "输入新国家 / 地区名称...";
        }
        newOptionInput.value = "";
        
        try {
            const res = await fetch("/api/cards/options");
            if (!res.ok) throw new Error("加载选项失败");
            currentOptions = await res.json();
            if (!currentOptions.countries) currentOptions.countries = [];
            if (!currentOptions.login_methods) currentOptions.login_methods = [];
            if (!currentOptions.kyc_providers) currentOptions.kyc_providers = [];
            if (!currentOptions.phones) currentOptions.phones = [];
            if (!currentOptions.addresses) currentOptions.addresses = [];
            if (!currentOptions.colors) currentOptions.colors = [];
            renderManageOptionsList();
            manageModal.style.display = "flex";
        } catch (err) {
            showToast("加载选项失败: " + err.message, true);
        }
    }

    function renderManageOptionsList() {
        optionsContainer.innerHTML = "";
        let list = [];
        if (currentManageType === "kyc") {
            list = currentOptions.kyc_methods;
        } else if (currentManageType === "kyc_provider") {
            list = currentOptions.kyc_providers;
        } else if (currentManageType === "type") {
            list = currentOptions.types;
        } else if (currentManageType === "login") {
            list = currentOptions.login_methods;
        } else if (currentManageType === "phone") {
            list = currentOptions.phones;
        } else if (currentManageType === "address") {
            list = currentOptions.addresses;
        } else if (currentManageType === "color") {
            list = currentOptions.colors;
        } else {
            list = currentOptions.countries;
        }
        
        optionsContainer.classList.add("option-manager-list");
        list.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "draggable-option-item option-manager-row";
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
            
            const isColorType = currentManageType === "color";
            const itemName = isColorType ? item.name : item;
            const itemValue = isColorType ? item.value : item;
            
            row.dataset.value = itemValue;
            if (isColorType) {
                row.dataset.name = itemName;
            }

            // Drag event listeners
            const leftPart = document.createElement("div");
            leftPart.className = "option-manager-label";
            leftPart.style.display = "flex";
            leftPart.style.alignItems = "center";
            leftPart.style.gap = "10px";

            const handle = document.createElement("button");
            handle.type = "button";
            handle.className = "option-manager-handle";
            handle.textContent = "≡";
            handle.style.color = "var(--muted)";
            handle.style.cursor = "grab";
            handle.style.userSelect = "none";
            leftPart.appendChild(handle);
            
            const textSpan = document.createElement("span");
            if (isColorType) {
                textSpan.innerHTML = `${itemName} <span style="display:inline-block; width:12px; height:12px; border-radius:3px; background-color:${itemValue}; border:1px solid #ccc; vertical-align:middle; margin-left:6px;"></span> (${itemValue})`;
            } else {
                textSpan.textContent = itemName;
            }
            textSpan.style.fontWeight = "500";
            leftPart.appendChild(textSpan);
            row.appendChild(leftPart);
            
            // Right: Actions (Edit + Delete)
            const actions = document.createElement("div");
            actions.className = "option-manager-actions";
            actions.style.display = "flex";
            actions.style.gap = "8px";
            
            // Edit button
            const editBtn = document.createElement("button");
            editBtn.type = "button";
            editBtn.innerHTML = "✏️";
            editBtn.style.background = "none";
            editBtn.style.border = "none";
            editBtn.style.cursor = "pointer";
            editBtn.style.padding = "2px";
            editBtn.title = "重命名";
            editBtn.dataset.micro = "edit";
            editBtn.setAttribute("aria-label", "修改选项名称");
            editBtn.addEventListener("click", async () => {
                let titleText = "修改选项";
                let labelText = "名称：";
                if (currentManageType === "kyc") {
                    titleText = "修改 KYC 选项";
                    labelText = "KYC 方式：";
                } else if (currentManageType === "type") {
                    titleText = "修改工具类型选项";
                    labelText = "类型名称：";
                } else if (currentManageType === "login") {
                    titleText = "修改登录方式选项";
                    labelText = "登录方式：";
                } else if (currentManageType === "phone") {
                    titleText = "修改电话号码选项";
                    labelText = "电话号码：";
                } else if (currentManageType === "provider") {
                    titleText = "修改账户提供方选项";
                    labelText = "账户提供方：";
                } else if (currentManageType === "color") {
                    titleText = "修改行高亮颜色选项";
                    labelText = "颜色展示名：";
                } else {
                    titleText = "修改国家 / 地区选项";
                    labelText = "国家 / 地区名称：";
                }
                const newName = await showCustomPrompt(titleText, labelText, itemName);
                if (newName && newName.trim() && newName.trim() !== itemName) {
                    if (isColorType) {
                        const newValue = await showCustomPrompt("修改颜色背景值", "CSS 颜色 / Hex 值 (例如: #fff5f5 或 pink)：", itemValue);
                        if (newValue && newValue.trim()) {
                            list[index] = { name: newName.trim(), value: newValue.trim() };
                            saveOptionsToServer();
                        }
                    } else {
                        list[index] = newName.trim();
                        saveOptionsToServer();
                    }
                }
            });
            actions.appendChild(editBtn);
            
            // Delete button
            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.innerHTML = "❌";
            delBtn.style.background = "none";
            delBtn.style.border = "none";
            delBtn.style.cursor = "pointer";
            delBtn.style.padding = "2px";
            delBtn.title = "删除";
            delBtn.dataset.micro = "delete";
            delBtn.addEventListener("click", async () => {
                const ok = await showCustomConfirm("删除确认", `确定要删除选项 "${itemName}" 吗？`);
                if (ok) {
                    list.splice(index, 1);
                    saveOptionsToServer();
                }
            });
            actions.appendChild(delBtn);
            
            row.appendChild(actions);
            optionsContainer.appendChild(row);
        });
        window.saulBindOptionOrder(optionsContainer, () => { reorderOptionsFromDOM(); renderManageOptionsList(); });
    }

    function reorderOptionsFromDOM() {
        const rows = Array.from(optionsContainer.querySelectorAll(".draggable-option-item"));
        if (currentManageType === "color") {
            const newValues = rows.map(r => ({
                name: r.dataset.name,
                value: r.dataset.value
            }));
            currentOptions.colors = newValues;
        } else {
            const newValues = rows.map(r => r.dataset.value);
            if (currentManageType === "kyc") {
                currentOptions.kyc_methods = newValues;
            } else if (currentManageType === "kyc_provider") {
                currentOptions.kyc_providers = newValues;
            } else if (currentManageType === "type") {
                currentOptions.types = newValues;
            } else if (currentManageType === "login") {
                currentOptions.login_methods = newValues;
            } else if (currentManageType === "phone") {
                currentOptions.phones = newValues;
            } else if (currentManageType === "address") {
                currentOptions.addresses = newValues;
            } else {
                currentOptions.countries = newValues;
            }
        }
        saveOptionsToServer(true);
    }

    async function saveOptionsToServer(skipRender = false, persist = false) {
        if (!persist) {
            if (!skipRender) renderManageOptionsList();
            return;
        }
        try {
            const res = await fetch("/api/cards/options", {
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
            document.getElementById("manageOptionsModal").style.display = "none";
        } catch (err) {
            showToast("保存选项失败: " + err.message, true);
        }
    }

    document.getElementById("saveManageOptionsBtn").addEventListener("click", async event => {
        const button = event.currentTarget;
        button.disabled = true;
        try { await saveOptionsToServer(false, true); }
        finally { button.disabled = false; }
    });

    function updateAllDOMSelects() {
        const addKycSelect = document.getElementById("addCardKyc");
        const addKycProviderSelect = document.getElementById("addCardKycProvider");
        const addTypeSelect = document.getElementById("addCardType");
        const addCountrySelect = document.getElementById("addCardCountry");
        const addLoginSelect = document.getElementById("addCardLogin");
        const addPhoneSelect = document.getElementById("addCardPhone");
        const addAddressSelect = document.getElementById("addCardAddress");
        const addColorSelect = document.getElementById("addCardColor");

        const editKycSelect = document.getElementById("editCardKyc");
        const editKycProviderSelect = document.getElementById("editCardKycProvider");
        const editTypeSelect = document.getElementById("editCardType");
        const editCountrySelect = document.getElementById("editCardCountry");
        const editLoginSelect = document.getElementById("editCardLogin");
        const editPhoneSelect = document.getElementById("editCardPhone");
        const editAddressSelect = document.getElementById("editCardAddress");
        const editColorSelect = document.getElementById("editCardColor");
        
        const addKycVal = addKycSelect ? addKycSelect.value : "";
        const addKycProviderVal = addKycProviderSelect ? addKycProviderSelect.value : "";
        const addTypeVal = addTypeSelect ? addTypeSelect.value : "";
        const addCountryVal = addCountrySelect ? addCountrySelect.value : "";
        const addLoginVal = addLoginSelect ? addLoginSelect.value : "";
        const addPhoneVal = addPhoneSelect ? addPhoneSelect.value : "";
        const addAddressVal = addAddressSelect ? addAddressSelect.value : "";
        const addColorVal = addColorSelect ? addColorSelect.value : "";
        
        const editKycVal = editKycSelect ? editKycSelect.value : "";
        const editKycProviderVal = editKycProviderSelect ? editKycProviderSelect.value : "";
        const editTypeVal = editTypeSelect ? editTypeSelect.value : "";
        const editCountryVal = editCountrySelect ? editCountrySelect.value : "";
        const editLoginVal = editLoginSelect ? editLoginSelect.value : "";
        const editPhoneVal = editPhoneSelect ? editPhoneSelect.value : "";
        const editAddressVal = editAddressSelect ? editAddressSelect.value : "";
        const editColorVal = editColorSelect ? editColorSelect.value : "";
        
        // 1. KYC
        if (addKycSelect && editKycSelect) {
            [addKycSelect, editKycSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.kyc_methods.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addKycSelect, addKycVal);
            selectOrAddOption(editKycSelect, editKycVal);
        }

        // 1b. KYC Provider
        if (addKycProviderSelect && editKycProviderSelect) {
            [addKycProviderSelect, editKycProviderSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.kyc_providers.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addKycProviderSelect, addKycProviderVal);
            selectOrAddOption(editKycProviderSelect, editKycProviderVal);
        }
        
        // 2. Type
        if (addTypeSelect && editTypeSelect) {
            [addTypeSelect, editTypeSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.types.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addTypeSelect, addTypeVal);
            selectOrAddOption(editTypeSelect, editTypeVal);
        }

        // 3. Country
        if (addCountrySelect && editCountrySelect) {
            [addCountrySelect, editCountrySelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.countries.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addCountrySelect, addCountryVal);
            selectOrAddOption(editCountrySelect, editCountryVal);
        }

        // 4. Login Method
        if (addLoginSelect && editLoginSelect) {
            [addLoginSelect, editLoginSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.login_methods.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addLoginSelect, addLoginVal);
            selectOrAddOption(editLoginSelect, editLoginVal);
        }

        // 5. Phone
        if (addPhoneSelect && editPhoneSelect) {
            [addPhoneSelect, editPhoneSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.phones.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addPhoneSelect, addPhoneVal);
            selectOrAddOption(editPhoneSelect, editPhoneVal);
        }

        // 5b. Address
        if (addAddressSelect && editAddressSelect) {
            [addAddressSelect, editAddressSelect].forEach(select => {
                select.innerHTML = "";
                currentOptions.addresses.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.textContent = opt;
                    select.appendChild(o);
                });
            });
            selectOrAddOption(addAddressSelect, addAddressVal);
            selectOrAddOption(editAddressSelect, editAddressVal);
        }


        // 7. Colors
        if (addColorSelect && editColorSelect) {
            [addColorSelect, editColorSelect].forEach(select => {
                select.innerHTML = "";
                const def = document.createElement("option");
                def.value = "";
                def.textContent = "默认 (无颜色)";
                select.appendChild(def);

                currentOptions.colors.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt.value;
                    o.textContent = opt.name;
                    select.appendChild(o);
                });
            });
            addColorSelect.value = addColorVal;
            editColorSelect.value = editColorVal;
        }
    }

    addOptionBtn.addEventListener("click", async () => {
        const val = newOptionInput.value.trim();
        if (!val) return;
        
        let list = [];
        if (currentManageType === "kyc") {
            list = currentOptions.kyc_methods;
        } else if (currentManageType === "kyc_provider") {
            list = currentOptions.kyc_providers;
        } else if (currentManageType === "type") {
            list = currentOptions.types;
        } else if (currentManageType === "login") {
            list = currentOptions.login_methods;
        } else if (currentManageType === "phone") {
            list = currentOptions.phones;
        } else if (currentManageType === "address") {
            list = currentOptions.addresses;
        } else if (currentManageType === "color") {
            list = currentOptions.colors;
        } else {
            list = currentOptions.countries;
        }
        
        const exists = list.some(item => {
            const name = (currentManageType === "color") ? item.name : item;
            return name.toLowerCase() === val.toLowerCase();
        });
        if (exists) {
            showToast("该选项已存在", true);
            return;
        }
        
        if (currentManageType === "color") {
            const hex = await showCustomPrompt("输入颜色背景值", "CSS 颜色 / Hex 值 (例如: #fff5f5 或 pink)：", "#ffffff");
            if (hex && hex.trim()) {
                list.push({ name: val, value: hex.trim() });
                newOptionInput.value = "";
                saveOptionsToServer();
            }
        } else {
            list.push(val);
            newOptionInput.value = "";
            saveOptionsToServer();
        }
    });

    newOptionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            addOptionBtn.click();
        }
    });

    // Wire up all manage option buttons in the DOM
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


    const table = document.getElementById("cardsTable");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    const headers = table.querySelectorAll("thead th");
    const searchInput = document.getElementById("cardsSearchInput");
    
    // Store all initial rows in an array
    const originalRows = Array.from(tbody.querySelectorAll("tr"));
    let filteredRows = [...originalRows];
    let sortColumnIndex = -1;
    let sortDirection = 1; // 1 = asc, -1 = desc

    let currentPage = parseInt(sessionStorage.getItem("cards_current_page")) || 1;
    const rowsPerPage = 10;
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

    // Create pagination container below table-wrap
    const tableWrap = table.closest(".table-wrap");
    const paginationContainer = document.createElement("div");
    paginationContainer.className = "pagination-container";
    tableWrap.parentNode.insertBefore(paginationContainer, tableWrap.nextSibling);

    function updateTable() {
        // 1. Filter rows by search input and color legend
        const query = (searchInput.value || "").toLowerCase().trim();
        filteredRows = originalRows.filter(row => {
            const rowColor = (row.dataset.color || "").toLowerCase();

            // Active Legend Badge Filter check
            if (selectedColorFilter) {
                const targetColor = selectedColorFilter.toLowerCase();
                let matchesColor = false;
                if (targetColor === '#fff5f5' && (rowColor === '#fff5f5' || rowColor === 'red')) matchesColor = true;
                else if (targetColor === '#fefbeb' && (rowColor === '#fefbeb' || rowColor === 'yellow')) matchesColor = true;
                else if (targetColor === '#eff6ff' && (rowColor === '#eff6ff' || rowColor === 'blue')) matchesColor = true;
                else if (targetColor === '#f0fdf4' && (rowColor === '#f0fdf4' || rowColor === 'green')) matchesColor = true;
                else if (targetColor === '#f3f4f6' && (rowColor === '#f3f4f6' || rowColor === 'gray' || rowColor === 'grey')) matchesColor = true;
                
                if (!matchesColor) return false;
            }

            if (!query) return true;

            // Semantic Color Meaning Query Matching (好用/注销/待验证/开户/待/重新注册)
            let queryMatchesColor = false;
            if ((query === '好用' || query === '红色' || query === '红') && (rowColor === '#fff5f5' || rowColor === 'red')) queryMatchesColor = true;
            if ((query === '注销' || query === '黄色' || query === '黄') && (rowColor === '#fefbeb' || rowColor === 'yellow')) queryMatchesColor = true;
            if ((query === '待验证' || query === '开户' || query === '待验证/开户' || query === '蓝色' || query === '蓝') && (rowColor === '#eff6ff' || rowColor === 'blue')) queryMatchesColor = true;
            if ((query === '待注册' || query === '待/重新注册' || query === '重新注册' || query === '绿色' || query === '绿') && (rowColor === '#f0fdf4' || rowColor === 'green')) queryMatchesColor = true;
            if ((query === '无法使用' || query === '不可用' || query === '灰色' || query === '灰' || query === '无') && (rowColor === '#f3f4f6' || rowColor === 'gray' || rowColor === 'grey')) queryMatchesColor = true;
            if (queryMatchesColor) return true;

            return Array.from(row.querySelectorAll("td")).some((td, idx) => {
                // Skip the last cell (actions button container)
                if (idx === row.querySelectorAll("td").length - 1) return false;
                
                // If it's the address button column, search in button dataset
                if (idx === 8) {
                    const btn = td.querySelector(".view-address-btn");
                    const addressText = btn ? (btn.dataset.address || "") : "";
                    return addressText.toLowerCase().includes(query);
                }
                
                // If it's the provider button column, search in button dataset
                if (idx === 5) {
                    const btn = td.querySelector(".view-provider-btn");
                    const providerText = btn ? (btn.dataset.provider || "") : "";
                    if (providerText) {
                        return providerText.toLowerCase().includes(query);
                    }
                }

                // If it's the KYC provider button column, search in button dataset
                if (idx === 2) {
                    const btn = td.querySelector(".view-kyc-provider-btn");
                    const kycProviderText = btn ? (btn.dataset.kycProvider || "") : "";
                    if (kycProviderText) {
                        return kycProviderText.toLowerCase().includes(query);
                    }
                }
                
                return td.textContent.toLowerCase().includes(query);
            });
        });

        // 2. Sort rows
        if (sortColumnIndex !== -1) {
            filteredRows.sort((a, b) => {
                let cellA = a.querySelectorAll("td")[sortColumnIndex].textContent.trim();
                let cellB = b.querySelectorAll("td")[sortColumnIndex].textContent.trim();

                // If sorting by address column, sort by dataset attribute
                if (sortColumnIndex === 8) {
                    const btnA = a.querySelectorAll("td")[8].querySelector(".view-address-btn");
                    const btnB = b.querySelectorAll("td")[8].querySelector(".view-address-btn");
                    cellA = btnA ? (btnA.dataset.address || "") : "";
                    cellB = btnB ? (btnB.dataset.address || "") : "";
                }

                // If sorting by provider column, sort by dataset attribute
                if (sortColumnIndex === 5) {
                    const btnA = a.querySelectorAll("td")[5].querySelector(".view-provider-btn");
                    const btnB = b.querySelectorAll("td")[5].querySelector(".view-provider-btn");
                    cellA = btnA ? (btnA.dataset.provider || "") : "";
                    cellB = btnB ? (btnB.dataset.provider || "") : "";
                }

                // If sorting by KYC provider column, sort by dataset attribute
                if (sortColumnIndex === 2) {
                    const btnA = a.querySelectorAll("td")[2].querySelector(".view-kyc-provider-btn");
                    const btnB = b.querySelectorAll("td")[2].querySelector(".view-kyc-provider-btn");
                    cellA = btnA ? (btnA.dataset.kycProvider || "") : "";
                    cellB = btnB ? (btnB.dataset.kycProvider || "") : "";
                }

                // If sorting by creation date column
                if (sortColumnIndex === 10) {
                    const dateA = cellA === '--' ? 0 : new Date(cellA).getTime() || 0;
                    const dateB = cellB === '--' ? 0 : new Date(cellB).getTime() || 0;
                    return (dateA - dateB) * sortDirection;
                }

                return cellA.localeCompare(cellB, 'zh-CN') * sortDirection;
            });
        }

        // 3. Paginate rows
        const totalRows = filteredRows.length;
        const totalPages = Math.ceil(totalRows / rowsPerPage) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;
        sessionStorage.setItem("cards_current_page", currentPage);

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;

        // Clear tbody and append only the current page rows
        tbody.innerHTML = "";
        filteredRows.forEach((row, idx) => {
            if (idx >= startIndex && idx < endIndex) {
                tbody.appendChild(row);
            }
        });

        // 4. Render pagination controls
        renderPagination(totalRows, totalPages);
    }

    function renderPagination(totalRows, totalPages) {
        paginationContainer.innerHTML = "";
        
        // Buttons container
        const btnGroup = document.createElement("div");
        btnGroup.className = "pagination-controls";

        // Prev Button
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

        // Page Numbers
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

        // Next Button
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

    // Add search input listener
    searchInput.addEventListener("input", () => {
        currentPage = 1;
        updateTable();
    });

    // Add sorting support to headers
    headers.forEach((th, idx) => {
        // Skip operation column (last column)
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
            // Reset indicators on other headers
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

        // Setup default arrows
        const text = th.textContent.trim();
        th.innerHTML = `${text} <span class="sort-indicator" data-direction="none" aria-hidden="true"></span>`;
    });

    // Run initial update
    updateTable();

    // Edit Card Modal
    const editModal = document.getElementById("editCardModal");
    const editForm = document.getElementById("editCardForm");
    const closeBtn = document.getElementById("closeEditModalBtn");
    const cancelBtn = document.getElementById("cancelEditModalBtn");
    
    const editNameInput = document.getElementById("editCardName");
    const editKycInput = document.getElementById("editCardKyc");
    const editKycProviderInput = document.getElementById("editCardKycProvider");
    const editLoginInput = document.getElementById("editCardLogin");
    const editTypeInput = document.getElementById("editCardType");
    const editCountryInput = document.getElementById("editCardCountry");
    const editPhoneInput = document.getElementById("editCardPhone");
    const editAddressInput = document.getElementById("editCardAddress");
    const editAccountProviderInput = document.getElementById("editCardAccountProvider");
    const editNoteInput = document.getElementById("editCardNote");
    const editColorInput = document.getElementById("editCardColor");

    let activeEditingRow = null;
    let activeDeletingRow = null;

    // Helper to show custom toasts in place without page jump
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

    // We must use event delegation to handle clicks on edited and paginated rows!
    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".edit-card-btn");
        if (btn) {
            activeEditingRow = btn.closest("tr");
            const id = btn.dataset.id;
            const name = btn.dataset.name;
            const kyc = btn.dataset.kyc;
            const kycProvider = btn.dataset.kycProvider;
            const login = btn.dataset.login;
            const type = btn.dataset.type;
            const country = btn.dataset.country;
            const phone = btn.dataset.phone;
            const address = btn.dataset.address;
            const note = btn.dataset.note;
            const accountProvider = btn.dataset.accountProvider;
            const color = btn.dataset.color;

            editForm.action = `/cards/${id}/update`;
            editNameInput.value = name;
            selectOrAddOption(editKycInput, kyc);
            selectOrAddOption(editKycProviderInput, kycProvider || "");
            selectOrAddOption(editLoginInput, login || "");
            selectOrAddOption(editTypeInput, type || "");
            selectOrAddOption(editCountryInput, country);
            selectOrAddOption(editPhoneInput, phone || "");
            selectOrAddOption(editAddressInput, address || "");
            editAccountProviderInput.value = accountProvider === "--" ? "" : (accountProvider || "");
            editNoteInput.value = note || "";
            selectOrAddOption(editColorInput, color || "");

            editModal.style.display = "flex";
        }
    });

    const hideEditModal = () => {
        editModal.style.display = "none";
        activeEditingRow = null;
    };

    if (closeBtn) closeBtn.addEventListener("click", hideEditModal);
    if (cancelBtn) cancelBtn.addEventListener("click", hideEditModal);

    // Edit form AJAX submission
    editForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(editForm);
        try {
            const response = await fetch(editForm.action, {
                method: "POST",
                body: formData
            });
            if (!response.ok) throw new Error("HTTP error " + response.status);

            // Update row fields in DOM
            if (activeEditingRow) {
                const name = editNameInput.value;
                const kyc = editKycInput.value;
                const kyc_provider = editKycProviderInput.value;
                const login = editLoginInput.value;
                const type = editTypeInput.value;
                const country = editCountryInput.value;
                const phone = editPhoneInput.value;
                const address = editAddressInput.value;
                const account_provider = editAccountProviderInput.value;
                const note = editNoteInput.value;
                const color = editColorInput.value;

                // Cell updates (adjust indices)
                activeEditingRow.cells[0].querySelector("strong").textContent = name;
                activeEditingRow.cells[1].querySelector("span").textContent = kyc;
                
                // Update KYC提供商 cell
                // Update KYC提供商 cell
                const cell2 = activeEditingRow.cells[2];
                const box2 = cell2.querySelector(".stable-cell-content") || cell2;
                box2.innerHTML = "";
                if (kyc_provider && kyc_provider !== "--") {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "view-kyc-provider-btn";
                    btn.style.cssText = "background: var(--bg); border: 1px solid var(--line); color: var(--text); padding: 4px 10px; border-radius: 8px; font-size: 12px; cursor: pointer; transition: all 0.2s; font-weight: 500;";
                    btn.textContent = "👤 查看";
                    btn.dataset.kycProvider = kyc_provider;
                    box2.appendChild(btn);
                    cell2.dataset.sort = kyc_provider;
                } else {
                    const span = document.createElement("span");
                    span.style.cssText = "font-size: 13px; font-weight: 500; color: var(--muted);";
                    span.textContent = "--";
                    box2.appendChild(span);
                    cell2.dataset.sort = "";
                }
                cell2.style.textAlign = "center";

                activeEditingRow.cells[3].querySelector("span").textContent = login || "--";
                activeEditingRow.cells[4].querySelector("span").textContent = type || "--";
                
                // Update 账户提供方 cell
                const cell5 = activeEditingRow.cells[5];
                const box5 = cell5.querySelector(".stable-cell-content") || cell5;
                box5.innerHTML = "";
                if (account_provider && account_provider !== "--") {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "view-provider-btn";
                    btn.style.cssText = "background: var(--bg); border: 1px solid var(--line); color: var(--text); padding: 4px 10px; border-radius: 8px; font-size: 12px; cursor: pointer; transition: all 0.2s; font-weight: 500;";
                    btn.textContent = "🏦 查看";
                    btn.dataset.provider = account_provider;
                    box5.appendChild(btn);
                    cell5.dataset.sort = account_provider;
                } else {
                    const span = document.createElement("span");
                    span.style.cssText = "font-size: 13px; font-weight: 500; color: var(--muted);";
                    span.textContent = "--";
                    box5.appendChild(span);
                    cell5.dataset.sort = "";
                }
                cell5.style.textAlign = "center";
                
                activeEditingRow.cells[6].querySelector("span").textContent = country;
                activeEditingRow.cells[7].querySelector("span").textContent = phone || "--";
                
                // Update 证明地址 cell
                const cell8 = activeEditingRow.cells[8];
                const box8 = cell8.querySelector(".stable-cell-content") || cell8;
                box8.innerHTML = "";
                if (address && address !== "--") {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "view-address-btn";
                    btn.style.cssText = "background: var(--bg); border: 1px solid var(--line); color: var(--text); padding: 4px 10px; border-radius: 8px; font-size: 12px; cursor: pointer; transition: all 0.2s; font-weight: 500;";
                    btn.textContent = "📍 查看";
                    btn.dataset.address = address;
                    box8.appendChild(btn);
                    cell8.dataset.sort = address;
                } else {
                    const span = document.createElement("span");
                    span.style.cssText = "font-size: 13px; font-weight: 500; color: var(--muted);";
                    span.textContent = "--";
                    box8.appendChild(span);
                    cell8.dataset.sort = "";
                }
                cell8.style.textAlign = "center";

                activeEditingRow.cells[9].textContent = note || "--";

                // Update styling
                activeEditingRow.style.backgroundColor = "";
                activeEditingRow.dataset.color = color || "";
                if (color) {
                    let bg = color;
                    if (color === "red") bg = "#fff5f5";
                    else if (color === "yellow") bg = "#fefbeb";
                    else if (color === "green") bg = "#f0fdf4";
                    else if (color === "blue") bg = "#eff6ff";
                    activeEditingRow.style.setProperty("background-color", bg, "important");
                }

                // Dataset updates on buttons
                const editBtn = activeEditingRow.querySelector(".edit-card-btn");
                if (editBtn) {
                    editBtn.dataset.name = name;
                    editBtn.dataset.kyc = kyc;
                    editBtn.dataset.kycProvider = kyc_provider || "--";
                    editBtn.dataset.login = login;
                    editBtn.dataset.type = type;
                    editBtn.dataset.country = country;
                    editBtn.dataset.phone = phone;
                    editBtn.dataset.address = address;
                    editBtn.dataset.note = note;
                    editBtn.dataset.accountProvider = account_provider || "--";
                    editBtn.dataset.color = color;
                }
                const deleteBtn = activeEditingRow.querySelector(".delete-card-btn");
                if (deleteBtn) {
                    deleteBtn.dataset.name = name;
                }
            }

            hideEditModal();
            updateTable();
            showToast("成功更新卡片记录");
        } catch (error) {
            console.error("更新卡片失败:", error);
            showToast("更新卡片失败: " + error.message, true);
        }
    });

    // Delete Card Modal with delegation
    const deleteModal = document.getElementById("deleteCardModal");
    const deleteForm = document.getElementById("deleteCardForm");
    const closeDeleteBtn = document.getElementById("closeDeleteModalBtn");
    const cancelDeleteBtn = document.getElementById("cancelDeleteModalBtn");
    const deleteNameSpan = document.getElementById("deleteCardNameSpan");

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".delete-card-btn");
        if (btn) {
            activeDeletingRow = btn.closest("tr");
            const id = btn.dataset.id;
            const name = btn.dataset.name;

            deleteForm.action = `/cards/${id}/delete`;
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

    // Delete form AJAX submission
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
            showToast("成功删除卡片记录");
        } catch (error) {
            console.error("删除卡片失败:", error);
            showToast("删除卡片失败: " + error.message, true);
        }
    });

    // Address View Modal
    const addressModal = document.getElementById("addressViewModal");
    const addressContent = document.getElementById("addressModalContent");
    const closeAddressBtn = document.getElementById("closeAddressModalBtn");
    const closeAddressBtn2 = document.getElementById("closeAddressModalBtn2");

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".view-address-btn");
        if (btn) {
            const address = btn.dataset.address;
            addressContent.textContent = address || "无地址信息。";
            addressModal.style.display = "flex";
        }
    });

    const hideAddressModal = () => {
        addressModal.style.display = "none";
    };

    if (closeAddressBtn) closeAddressBtn.addEventListener("click", hideAddressModal);
    if (closeAddressBtn2) closeAddressBtn2.addEventListener("click", hideAddressModal);

    // Provider View Modal
    const providerModal = document.getElementById("providerViewModal");
    const providerContent = document.getElementById("providerModalContent");
    const closeProviderBtn = document.getElementById("closeProviderModalBtn");
    const closeProviderBtn2 = document.getElementById("closeProviderModalBtn2");

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".view-provider-btn");
        if (btn) {
            const provider = btn.dataset.provider;
            providerContent.textContent = provider || "无提供商信息。";
            providerModal.style.display = "flex";
        }
    });

    const hideProviderModal = () => {
        providerModal.style.display = "none";
    };

    if (closeProviderBtn) closeProviderBtn.addEventListener("click", hideProviderModal);
    if (closeProviderBtn2) closeProviderBtn2.addEventListener("click", hideProviderModal);

    // KYC Provider View Modal
    const kycProviderModal = document.getElementById("kycProviderViewModal");
    const kycProviderContent = document.getElementById("kycProviderModalContent");
    const closeKycProviderBtn = document.getElementById("closeKycProviderModalBtn");
    const closeKycProviderBtn2 = document.getElementById("closeKycProviderModalBtn2");

    tbody.addEventListener("click", (event) => {
        const btn = event.target.closest(".view-kyc-provider-btn");
        if (btn) {
            const kycProvider = btn.dataset.kycProvider;
            kycProviderContent.textContent = kycProvider || "无提供商信息。";
            kycProviderModal.style.display = "flex";
        }
    });

    const hideKycProviderModal = () => {
        kycProviderModal.style.display = "none";
    };

    if (closeKycProviderBtn) closeKycProviderBtn.addEventListener("click", hideKycProviderModal);
    if (closeKycProviderBtn2) closeKycProviderBtn2.addEventListener("click", hideKycProviderModal);

    // Close modals on window click outside
    const handleCardModalWindowClick = (event) => {
        if (event.target === editModal) {
            hideEditModal();
        }
        if (event.target === deleteModal) {
            hideDeleteModal();
        }
        if (event.target === addressModal) {
            hideAddressModal();
        }
        if (event.target === providerModal) {
            hideProviderModal();
        }
        if (event.target === kycProviderModal) {
            hideKycProviderModal();
        }
        if (event.target === manageModal) {
            hideManageModal();
        }
    };
    window.addEventListener("click", handleCardModalWindowClick);

    // Register PJAX cleanup
    window.pjaxCleanupTasks = window.pjaxCleanupTasks || [];
    window.pjaxCleanupTasks.push(() => {
        window.removeEventListener("click", handleCardModalWindowClick);
    });

    // Listen for sidebar nav clicks to card records to reset page to 1
    const sidebarCardLinks = document.querySelectorAll('a[href="/cards"]');
    sidebarCardLinks.forEach(link => {
        link.addEventListener("click", () => {
            sessionStorage.setItem("cards_current_page", 1);
        });
    });
});
