(() => {
    const page = document.getElementById("walletCardsPage");
    if (!page || page.dataset.initialized === "true") return;
    page.dataset.initialized = "true";

    const ITEMS_PER_PAGE = 9;
    const schemeModal = document.getElementById("walletSchemeModal");
    let schemeDraft = [];
    function renderSchemes() {
        window.saulRenderOptionList(document.getElementById("walletSchemeList"), schemeDraft, values => { schemeDraft = values; renderSchemes(); }, message => { document.getElementById("walletSchemeError").textContent = message; });
    }
    page.querySelectorAll(".wallet-manage-schemes").forEach(button => button.addEventListener("click", async () => {
        openModal(schemeModal);
        document.getElementById("walletSchemeError").textContent = "";
        try { const r = await fetch('/api/wallet-card-options'); if (!r.ok) throw Error(); schemeDraft = (await r.json()).schemes; renderSchemes(); }
        catch (_) { document.getElementById("walletSchemeError").textContent = "加载失败，请重试。"; }
    }));
    document.getElementById("walletAddScheme").addEventListener("click", () => {
        const input = document.getElementById("walletNewScheme"); const name = input.value.trim();
        if (name && !schemeDraft.includes(name)) { schemeDraft.push(name); input.value = ""; renderSchemes(); }
    });
    document.getElementById("walletSaveSchemes").addEventListener("click", async (event) => {
        if (document.getElementById("walletSchemeList").commitOptionEdit?.() === false) return;
        event.currentTarget.disabled = true;
        try {
            const r = await fetch('/api/wallet-card-options', {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify({schemes:schemeDraft})});
            const result = await r.json(); if (!r.ok) throw Error(result.message || "保存失败");
            page.querySelectorAll('select[name="scheme"]').forEach(select => {
                const selected = select.value; select.replaceChildren();
                const values = [...result.schemes]; if (selected && !values.includes(selected)) values.push(selected);
                values.forEach(v => select.add(new Option(v,v))); select.value = selected;
            }); closeModal(schemeModal);
        } catch (e) { document.getElementById("walletSchemeError").textContent = e.message; }
        finally { document.getElementById("walletSaveSchemes").disabled = false; }
    });

    const addForm = document.getElementById("walletCardAddForm");
    const toggleFormButton = document.getElementById("toggleWalletCardForm");
    const grid = document.getElementById("walletCardGrid");
    const searchInput = document.getElementById("walletCardSearch");
    const emptySearch = document.getElementById("walletCardsEmptySearch");
    const pagination = document.getElementById("walletCardsPagination");
    const detailModal = document.getElementById("walletCardDetailModal");
    const editModal = document.getElementById("walletCardEditModal");
    const editButton = document.getElementById("editWalletCardButton");
    const copyButton = document.getElementById("copyWalletCardNumber");
    const toggleCvcButton = document.getElementById("toggleWalletCardCvc");
    const deleteForm = document.getElementById("deleteWalletCardForm");
    const editForm = document.getElementById("walletCardEditForm");
    const addSourceTool = document.getElementById("addWalletCardSourceTool");
    const editSourceTool = document.getElementById("editWalletCardSourceTool");
    let currentCard = null;
    let cvcVisible = false;
    let currentPage = Number.parseInt(sessionStorage.getItem("wallet_cards_current_page") || "1", 10) || 1;

    function bindSourceTool(select, softwareInput, addressInput) {
        select?.addEventListener("change", () => {
            const option = select.options[select.selectedIndex];
            if (!option || select.value === "0") return;
            if (softwareInput) softwareInput.value = option.dataset.toolName || "";
            if (addressInput) addressInput.value = option.dataset.toolAddress || "";
        });
    }

    bindSourceTool(
        addSourceTool,
        document.getElementById("addWalletCardSoftware"),
        document.getElementById("addWalletCardAddress"),
    );
    bindSourceTool(
        editSourceTool,
        document.getElementById("editWalletCardSoftware"),
        document.getElementById("editWalletCardAddress"),
    );

    function setFormExpanded(expanded) {
        if (!addForm || !toggleFormButton) return;
        window.saulSetFormExpanded(addForm, expanded);
        toggleFormButton.setAttribute("aria-expanded", String(expanded));
        toggleFormButton.textContent = expanded ? "收起" : "添加卡片";
    }

    toggleFormButton?.addEventListener("click", () => {
        setFormExpanded(addForm?.classList.contains("is-collapsed") ?? false);
    });

    addForm?.addEventListener("submit", () => {
        sessionStorage.setItem("wallet_cards_current_page", "1");
    });

    function createPageButton(label, targetPage, active = false, disabled = false) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `page-btn${active ? " active" : ""}`;
        button.textContent = label;
        button.disabled = disabled;
        if (active) button.setAttribute("aria-current", "page");
        button.addEventListener("click", () => {
            currentPage = targetPage;
            renderCards();
        });
        return button;
    }

    function renderPagination(totalPages) {
        if (!pagination) return;
        pagination.innerHTML = "";
        if (totalPages <= 1) {
            pagination.hidden = true;
            return;
        }
        pagination.hidden = false;
        const controls = document.createElement("div");
        controls.className = "pagination-controls";
        controls.appendChild(createPageButton("« 上一页", currentPage - 1, false, currentPage === 1));

        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        startPage = Math.max(1, endPage - 4);
        for (let pageNumber = startPage; pageNumber <= endPage; pageNumber += 1) {
            controls.appendChild(createPageButton(String(pageNumber), pageNumber, pageNumber === currentPage));
        }

        controls.appendChild(createPageButton("下一页 »", currentPage + 1, false, currentPage === totalPages));
        pagination.appendChild(controls);
    }

    function renderCards() {
        if (!grid) return;
        const query = (searchInput?.value || "").trim().toLocaleLowerCase("zh-CN");
        const cards = Array.from(grid.querySelectorAll(".wallet-card-tile"));
        const matches = cards.filter((card) => (card.dataset.search || "").toLocaleLowerCase("zh-CN").includes(query));
        const totalPages = Math.max(1, Math.ceil(matches.length / ITEMS_PER_PAGE));
        currentPage = Math.min(Math.max(currentPage, 1), totalPages);
        sessionStorage.setItem("wallet_cards_current_page", String(currentPage));
        const visibleCards = new Set(matches.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE));
        cards.forEach((card) => {
            card.hidden = !visibleCards.has(card);
        });
        if (emptySearch) emptySearch.hidden = matches.length !== 0;
        renderPagination(matches.length ? totalPages : 0);
    }

    searchInput?.addEventListener("input", () => {
        currentPage = 1;
        renderCards();
    });

    function setText(id, value, fallback = "--") {
        const element = document.getElementById(id);
        if (element) element.textContent = value || fallback;
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        if (!document.querySelector(".wallet-modal.is-open")) document.body.style.overflow = "";
    }

    function openModal(modal) {
        if (!modal) return;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        modal.querySelector(".wallet-modal-close")?.focus();
    }

    function populateDetail(card) {
        currentCard = card;
        cvcVisible = false;
        setText("walletCardDetailTitle", card.name, "卡片详情");
        setText("walletDetailSoftware", card.software);
        const brandImage = document.createElement("img");
        brandImage.src = card.brand_icon || "/static/images/wallet-brands/card.svg";
        brandImage.alt = "";
        document.getElementById("walletDetailAppMark").replaceChildren(brandImage);
        setText("walletDetailScheme", card.scheme, "CARD");
        setText("walletDetailNumber", card.card_number);
        setText("walletDetailExpiry", card.expiry);
        setText("walletDetailCvc", card.cvc ? "•".repeat(card.cvc.length) : "--");
        if (toggleCvcButton) toggleCvcButton.textContent = "显示";
        setText("walletDetailHolder", card.holder_name);
        setText("walletDetailVariant", card.card_variant);
        setText("walletDetailBinCountry", card.bin_info_display || "--");
        setText("walletDetailAddress", card.billing_address);
        setText("walletDetailCountry", card.country);
        setText("walletDetailPhone", card.phone);
        setText("walletDetailLogin", card.login_method);
        setText("walletDetailKycProvider", card.kyc_provider);
        setText("walletDetailAccountProvider", card.account_provider);
        setText("walletDetailNote", card.note);
        document.getElementById("walletDetailNote").parentElement.hidden = !card.note;
        if (deleteForm) deleteForm.action = `/wallet-cards/${card.id}/delete`;
    }

    async function showCard(cardId, trigger) {
        trigger?.setAttribute("aria-busy", "true");
        try {
            const response = await fetch(`/api/wallet-cards/${cardId}`, { cache: "no-store" });
            const payload = await response.json();
            if (!response.ok || payload.status !== "success") {
                throw new Error(payload.message || "卡片资料加载失败。");
            }
            populateDetail(payload.card);
            openModal(detailModal);
        } catch (error) {
            window.alert(error.message || "卡片资料加载失败。");
        } finally {
            trigger?.removeAttribute("aria-busy");
        }
    }

    grid?.addEventListener("click", (event) => {
        const card = event.target.closest(".wallet-card-tile");
        if (card) showCard(card.dataset.cardId, card);
    });

    copyButton?.addEventListener("click", async () => {
        if (!currentCard?.card_number) return;
        try {
            await navigator.clipboard.writeText(currentCard.card_number.replace(/\s/g, ""));
            const oldText = copyButton.textContent;
            copyButton.textContent = "已复制";
            window.setTimeout(() => { copyButton.textContent = oldText; }, 1200);
        } catch (_error) {
            window.alert("浏览器未允许自动复制，请手动选择卡号复制。");
        }
    });

    toggleCvcButton?.addEventListener("click", () => {
        if (!currentCard?.cvc) return;
        cvcVisible = !cvcVisible;
        setText("walletDetailCvc", cvcVisible ? currentCard.cvc : "•".repeat(currentCard.cvc.length));
        toggleCvcButton.textContent = cvcVisible ? "隐藏" : "显示";
    });

    editButton?.addEventListener("click", () => {
        if (!currentCard || !editForm) return;
        editForm.action = `/wallet-cards/${currentCard.id}/update`;
        document.getElementById("editWalletCardName").value = currentCard.name || "";
        document.getElementById("editWalletCardSoftware").value = currentCard.software || "";
        document.getElementById("editWalletCardSourceTool").value = String(currentCard.source_tool_id || 0);
        const schemeSelect = document.getElementById("editWalletCardScheme");
        const savedScheme = currentCard.scheme || "其他";
        if (![...schemeSelect.options].some(o => o.value === savedScheme)) schemeSelect.add(new Option(savedScheme, savedScheme));
        schemeSelect.value = savedScheme;
        document.getElementById("editWalletCardVariant").value = currentCard.card_variant || "";
        document.getElementById("editWalletCardCoverStyle").value = currentCard.cover_style || "standard";
        document.getElementById("editWalletCardNumber").value = currentCard.card_number || "";
        document.getElementById("editWalletCardExpiry").value = currentCard.expiry || "";
        document.getElementById("editWalletCardCvc").value = currentCard.cvc || "";
        document.getElementById("editWalletCardHolder").value = currentCard.holder_name || "";
        document.getElementById("editWalletCardAddress").value = currentCard.billing_address || "";
        document.getElementById("editWalletCardNote").value = currentCard.note || "";
        closeModal(detailModal);
        openModal(editModal);
    });

    const deleteModal = document.getElementById("walletCardDeleteModal");
    deleteForm?.addEventListener("submit", (event) => {
        event.preventDefault();
        setText("walletDeleteName", currentCard?.name || "这张卡");
        openModal(deleteModal);
        deleteModal.querySelector(".wallet-delete-actions button").focus();
    });
    document.getElementById("confirmWalletDelete").addEventListener("click", (event) => {
        event.currentTarget.disabled = true;
        HTMLFormElement.prototype.submit.call(deleteForm);
    });

    page.addEventListener("click", (event) => {
        const closeButton = event.target.closest("[data-wallet-modal-close]");
        if (closeButton) closeModal(closeButton.closest(".wallet-modal"));
        if (event.target.classList.contains("wallet-modal")) closeModal(event.target);
    });

    const handleKeydown = (event) => {
        if (event.key !== "Escape") return;
        closeModal(schemeModal);
        closeModal(deleteModal);
        closeModal(editModal);
        closeModal(detailModal);
    };
    document.addEventListener("keydown", handleKeydown);
    window.pjaxCleanupTasks = window.pjaxCleanupTasks || [];
    window.pjaxCleanupTasks.push(() => {
        document.removeEventListener("keydown", handleKeydown);
        document.body.style.overflow = "";
    });

    renderCards();
    const linkedCardId = new URLSearchParams(location.search).get("card_id");
    if (linkedCardId && /^\d+$/.test(linkedCardId)) showCard(linkedCardId);
})();
