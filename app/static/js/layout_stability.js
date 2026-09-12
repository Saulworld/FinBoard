(() => {
    if (window.siteLayoutStability) return;
    window.siteLayoutStability = true;
    const tables = {
        cardsTable: { widths: [125, 80, 90, 120, 80, 95, 85, 145, 85, 140, 130, 100], height: 686 },
        phonesTable: { widths: [160, 165, 120, 110, 130, 130, 180, 260, 110], height: 558 },
        watchlistTable: { widths: [190, 95, 110, 110, 110, 135, 180, 100], height: 366 },
        holdingsTable: { widths: [165, 70, 85, 95, 100, 100, 100, 105, 105, 100, 90], height: 366 },
        transactionsTable: { widths: [140, 150, 100, 95, 120, 120, 220, 170], height: 366 },
    };
    function stabilize() {
        for (const [id, config] of Object.entries(tables)) {
            const table = document.getElementById(id);
            if (!table) continue;
            if (!table.classList.contains('stable-table')) {
                table.classList.add('stable-table');
                const cols = document.createElement('colgroup');
                config.widths.forEach(width => {
                    const col = document.createElement('col');
                    col.style.width = ["cardsTable", "phonesTable"].includes(id) ? `${width / config.widths.reduce((a, b) => a + b, 0) * 100}%` : `${width}px`;
                    cols.append(col);
                });
                table.prepend(cols);
                table.style.setProperty('--table-min-width', `${config.widths.reduce((a, b) => a + b, 0)}px`);
                table.parentElement.classList.add('stable-table-region');
                table.parentElement.style.setProperty('--table-region-height', `${config.height}px`);
            }
            // Count all data rows, including hidden pages, so the last page never shrinks.
            const dataRows = [...table.querySelectorAll('tbody tr')].filter(row =>
                row.children.length > 1 || !row.querySelector('td[colspan]'));
            table.parentElement.classList.toggle('compact-table-region', dataRows.length < 5);
            // Also covers cells replaced by existing in-place edit handlers.
            table.querySelectorAll('tbody td').forEach(cell => {
                if (['cardsTable', 'phonesTable'].includes(id) && cell.title !== cell.textContent.trim()) cell.title = cell.textContent.trim();
                if (cell.children.length === 1 && cell.firstElementChild.classList.contains('stable-cell-content')) return;
                const box = document.createElement('div');
                box.className = 'stable-cell-content';
                box.tabIndex = 0;
                while (cell.firstChild) box.append(cell.firstChild);
                cell.append(box);
            });
        }
        document.querySelectorAll('.briefing-grid').forEach(grid => {
            if (!grid.clientWidth) return;
            if (grid.children.length < 5) { if (grid.style.height !== 'auto') grid.style.height = 'auto'; return; }
            const columns = getComputedStyle(grid).gridTemplateColumns.split(' ').length;
            const rows = Math.ceil(9 / columns);
            const height = `${rows * 220 + (rows - 1) * 16}px`;
            if (grid.style.height !== height) grid.style.height = height;
        });
        const gallery = document.getElementById('walletCardGrid');
        if (gallery && gallery.clientWidth) {
            if (gallery.children.length < 5) { if (gallery.style.height !== 'auto') gallery.style.height = 'auto'; return; }
            const style = getComputedStyle(gallery);
            const columns = style.gridTemplateColumns.split(' ').length;
            const gap = parseFloat(style.rowGap) || 20;
            const width = parseFloat(style.gridTemplateColumns.split(' ')[0]);
            const rowHeight = Math.max(170, width / 1.586);
            const rows = Math.ceil(Math.min(9, gallery.children.length) / columns);
            const height = `${Math.ceil(rows * rowHeight + Math.max(0, rows - 1) * gap)}px`;
            if (gallery.style.height !== height) gallery.style.height = height;
        }
    }
    let queued = false;
    function schedule() {
        if (queued) return;
        queued = true;
        requestAnimationFrame(() => { queued = false; stabilize(); });
    }
    // One observer survives PJAX and preserves existing control event listeners.
    new MutationObserver(schedule).observe(document.querySelector('.content-area'), { childList: true, subtree: true });
    window.addEventListener('resize', schedule);
    stabilize();
})();
