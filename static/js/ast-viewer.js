(function (global) {
    "use strict";
    const mounts = new WeakMap();
    let serial = 0;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    const short = (value, limit = 27) => {
        const text = String(value).replace(/\s+/g, " ");
        const characters = Array.from(text);
        return characters.length > limit ? `${characters.slice(0, limit - 1).join("")}…` : text;
    };

    function mount(host, ast) {
        if (!(host instanceof Element)) throw new TypeError("O local da árvore AST não foi encontrado.");
        const d3 = global.d3;
        if (!d3?.hierarchy || !d3?.tree || !d3?.zoom)
            throw new Error("A biblioteca local de visualização não foi carregada.");
        const model = global.MiniParASTModel.buildASTTree(ast);
        mounts.get(host)?.destroy();
        const id = `ast-viewer-${++serial}`;
        const wrapper = element("section", "ast-viewer");
        const shell = element("div", "ast-interactive-shell");
        const toolbar = element("div", "ast-toolbar");
        toolbar.setAttribute("role", "group");
        toolbar.setAttribute("aria-label", "Controles da árvore sintática");
        const hint = element("p", "ast-hint",
            "Arraste para mover. Clique ou use Enter/Espaço nos nós para ver detalhes e abrir ou fechar ramos.");
        const layout = element("div", "ast-layout");
        const viewport = element("div", "ast-viewport");
        const inspector = element("aside", "ast-inspector ast-node-details");
        inspector.setAttribute("aria-label", "Detalhes do nó selecionado");
        const status = element("p", "ast-status");
        status.setAttribute("aria-live", "polite");
        status.setAttribute("aria-atomic", "true");
        const details = element("details", "ast-json");
        const json = element("pre", "structured-code");
        json.id = "ast-code";
        json.textContent = JSON.stringify(ast, null, 2);
        details.append(element("summary", "", "Ver AST em JSON"), json);
        layout.append(viewport, inspector);
        shell.append(toolbar, hint, layout, status);
        wrapper.append(shell, details);

        const dialog = element("dialog", "ast-dialog");
        const dialogHeader = element("header", "ast-dialog-header");
        const dialogTitle = element("h3", "", "Árvore sintática ampliada");
        dialogTitle.id = `${id}-dialog-title`;
        dialog.setAttribute("aria-labelledby", dialogTitle.id);
        const close = element("button", "ast-control", "Fechar");
        close.type = "button";
        close.setAttribute("aria-label", "Fechar visualização ampliada");
        const dialogBody = element("div", "ast-dialog-body");
        dialogHeader.append(dialogTitle, close);
        dialog.append(dialogHeader, dialogBody);
        wrapper.append(dialog);

        const listeners = [];
        const collapsed = new Set();
        const all = d3.hierarchy(model).descendants();
        if (all.length > 12) all.forEach(node => {
            if (node.depth >= 2 && node.children) collapsed.add(node.data.id);
        });
        let destroyed = false, observer, raf = 0, svg, canvas, zoom, currentRoot;
        let selected = model, fitted = false, size = { width: 0, height: 0 };
        let modalTrigger = null;

        function listen(target, event, handler) {
            target.addEventListener(event, handler);
            listeners.push(() => target.removeEventListener(event, handler));
        }
        function control(action, label, text) {
            const button = element("button", "ast-control", text || label);
            button.type = "button";
            button.dataset.action = action;
            button.setAttribute("aria-label", label);
            button.title = label;
            toolbar.append(button);
            return button;
        }
        const plus = control("zoom-in", "Aumentar zoom", "+");
        const minus = control("zoom-out", "Diminuir zoom", "−");
        const fitButton = control("fit", "Ajustar à tela", "Ajustar");
        const expand = control("expand-all", "Expandir ramos", "Expandir");
        const collapse = control("collapse-all", "Recolher ramos", "Recolher");
        const enlarge = control("enlarge", "Ampliar visualização", "Ampliar");

        function measure() {
            const box = viewport.getBoundingClientRect();
            if (box.width < 1 || box.height < 1) return false;
            size = { width: box.width, height: box.height };
            svg.attr("viewBox", `0 0 ${size.width} ${size.height}`);
            return true;
        }
        function fit() {
            if (destroyed || !svg || !currentRoot || !measure()) return;
            const nodes = currentRoot.descendants();
            const minX = d3.min(nodes, node => node.y) - 128;
            const maxX = d3.max(nodes, node => node.y) + 128;
            const minY = d3.min(nodes, node => node.x) - 60;
            const maxY = d3.max(nodes, node => node.x) + 60;
            const scale = Math.max(0.03, Math.min(1.1,
                (size.width - 24) / Math.max(1, maxX - minX),
                (size.height - 24) / Math.max(1, maxY - minY)));
            const transform = d3.zoomIdentity
                .translate(size.width / 2 - (minX + maxX) * scale / 2,
                    size.height / 2 - (minY + maxY) * scale / 2).scale(scale);
            svg.call(zoom.transform, transform);
            fitted = true;
        }
        function scheduleSize() {
            if (destroyed || raf) return;
            raf = requestAnimationFrame(() => {
                raf = 0;
                if (!destroyed && measure() && !fitted) fit();
            });
        }
        function showInspector(node) {
            inspector.replaceChildren();
            const heading = element("h4", "ast-inspector-title", "Nó selecionado");
            const properties = element("dl", "ast-properties");
            const property = (label, value, pre = false) => {
                const term = element("dt", "", label);
                const content = element("dd");
                if (pre) content.append(element("pre", "ast-attribute-value", value));
                else content.textContent = value;
                properties.append(term, content);
            };
            property("Tipo", `${node.label} (${node.nodeType})`);
            if (node.summary) property("Resumo", node.summary);
            property("Linha", node.line === null ? "Não informada" : String(node.line));
            property("Relação com o pai", node.relation === "root" ? "Raiz do programa"
                : `${node.relationLabel} (${node.relation})`);
            Object.entries(node.attributes).forEach(([key, value]) => property(key,
                typeof value === "string" ? value : JSON.stringify(value, null, 2), true));
            inspector.append(heading, properties);
        }
        function focusNode(nodeId) {
            svg.selectAll("g.ast-node").filter(node => node.data.id === nodeId).node()?.focus();
        }
        function revealFocusedNode(node) {
            if (!measure()) return;
            const transform = d3.zoomTransform(svg.node());
            const offset = (start, end, extent) => {
                const padding = 16;
                if (end - start > extent - padding * 2) return extent / 2 - (start + end) / 2;
                if (start < padding) return padding - start;
                if (end > extent - padding) return extent - padding - end;
                return 0;
            };
            const dx = offset(transform.applyX(node.y - 110), transform.applyX(node.y + 110), size.width);
            const dy = offset(transform.applyY(node.x - 40), transform.applyY(node.x + 40), size.height);
            if (dx || dy) svg.call(zoom.transform,
                d3.zoomIdentity.translate(transform.x + dx, transform.y + dy).scale(transform.k));
        }
        function activate(node, keyboard) {
            selected = node.data;
            if (node.data.children.length) {
                if (collapsed.has(node.data.id)) collapsed.delete(node.data.id);
                else collapsed.add(node.data.id);
            }
            render();
            if (keyboard) focusNode(selected.id);
        }
        function render() {
            currentRoot = d3.hierarchy(model, node => collapsed.has(node.id) ? null : node.children);
            d3.tree().nodeSize([108, 280])(currentRoot);
            const nodes = currentRoot.descendants();
            canvas.select(".ast-links").selectAll("path").data(currentRoot.links(), link => link.target.data.id)
                .join("path").attr("class", "ast-link").attr("aria-hidden", "true")
                .attr("d", link => {
                    const x1 = link.source.y + 110, x2 = link.target.y - 110;
                    const middle = (x1 + x2) / 2;
                    return `M${x1},${link.source.x}C${middle},${link.source.x} ${middle},${link.target.x} ${x2},${link.target.x}`;
                });
            const groups = canvas.select(".ast-nodes").selectAll("g.ast-node")
                .data(nodes, node => node.data.id).join(enter => {
                    const group = enter.append("g").attr("class", "ast-node")
                        .attr("role", "button").attr("tabindex", 0);
                    group.append("rect").attr("class", "ast-node-box")
                        .attr("x", -110).attr("y", -40).attr("width", 220).attr("height", 80).attr("rx", 10);
                    group.append("text").attr("class", "ast-node-type").attr("x", -96).attr("y", -17);
                    group.append("text").attr("class", "ast-node-summary").attr("x", -96).attr("y", 5);
                    group.append("text").attr("class", "ast-node-position").attr("x", -96).attr("y", 25);
                    group.append("text").attr("class", "ast-node-toggle").attr("x", 96).attr("y", -17)
                        .attr("text-anchor", "middle").attr("aria-hidden", "true");
                    group.append("title");
                    return group;
                });
            groups.attr("transform", node => `translate(${node.y},${node.x})`)
                .attr("data-node-id", node => node.data.id).attr("data-node-type", node => node.data.nodeType)
                .classed("is-selected", node => node.data.id === selected.id)
                .classed("is-collapsed", node => collapsed.has(node.data.id))
                .attr("aria-pressed", node => String(node.data.id === selected.id))
                .attr("aria-expanded", node => node.data.children.length ? String(!collapsed.has(node.data.id)) : null)
                .attr("aria-label", node => [node.data.label, node.data.nodeType, node.data.summary,
                    node.data.line === null ? "" : `linha ${node.data.line}`, node.data.relationLabel,
                    node.data.children.length ? (collapsed.has(node.data.id) ? "Expandir ramo" : "Recolher ramo") : "Ver detalhes"
                ].filter(Boolean).join(". "))
                .on("click.ast", (event, node) => { event.stopPropagation(); activate(node, false); })
                .on("focus.ast", (event, node) => {
                    if (event.currentTarget.matches(":focus-visible")) revealFocusedNode(node);
                })
                .on("keydown.ast", (event, node) => {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault(); event.stopPropagation(); activate(node, true);
                    }
                });
            groups.select(".ast-node-type").text(node => short(node.data.label, 26));
            groups.select(".ast-node-summary").text(node => short(node.data.summary || node.data.nodeType));
            groups.select(".ast-node-position").text(node => short(
                `${node.data.line === null ? "Linha não informada" : `Linha ${node.data.line}`} · ${node.data.relationLabel}`, 31));
            groups.select(".ast-node-toggle").text(node => node.data.children.length
                ? (collapsed.has(node.data.id) ? "+" : "−") : "");
            groups.select("title").text(node => [node.data.label, node.data.nodeType,
                node.data.summary, node.data.relationLabel].filter(Boolean).join(" · "));
            showInspector(selected);
            status.textContent = `${nodes.length} de ${all.length} nós visíveis. Nó selecionado: ${selected.label}.`;
        }
        function closeModal() {
            if (dialog.open) dialog.close();
        }
        function restoreShell() {
            if (destroyed) return;
            wrapper.insertBefore(shell, details);
            enlarge.hidden = false;
            fit();
            if (modalTrigger?.isConnected) modalTrigger.focus();
        }
        function destroy() {
            if (destroyed) return;
            destroyed = true;
            if (raf) cancelAnimationFrame(raf);
            observer?.disconnect();
            listeners.splice(0).forEach(remove => remove());
            if (dialog.open) dialog.close();
            if (svg) {
                svg.on(".zoom", null);
                svg.selectAll(".ast-node").on(".ast", null);
            }
            dialog.remove();
            wrapper.remove();
            if (mounts.get(host)?.destroy === destroy) mounts.delete(host);
        }

        try {
            host.append(wrapper);
            svg = d3.select(viewport).append("svg").attr("class", "ast-svg ast-tree")
                .attr("role", "group").attr("aria-labelledby", `${id}-svg-title ${id}-svg-description`)
                .attr("viewBox", "0 0 600 380").attr("width", "100%").attr("height", "100%");
            svg.append("title").attr("id", `${id}-svg-title`).text("Árvore sintática abstrata do programa MiniPar");
            svg.append("desc").attr("id", `${id}-svg-description`)
                .text("Nós conectados mostram a estrutura do programa. Use Tab para navegar e Enter ou Espaço para selecionar e expandir ou recolher um ramo.");
            canvas = svg.append("g").attr("class", "ast-canvas");
            canvas.append("g").attr("class", "ast-links");
            canvas.append("g").attr("class", "ast-nodes");
            zoom = d3.zoom().scaleExtent([0.03, 3.5])
                .extent(() => [[0, 0], [Math.max(1, size.width), Math.max(1, size.height)]])
                .on("zoom.ast", event => canvas.attr("transform", event.transform));
            svg.call(zoom).on("dblclick.zoom", null);
            listen(plus, "click", () => svg.call(zoom.scaleBy, 1.25));
            listen(minus, "click", () => svg.call(zoom.scaleBy, 0.8));
            listen(fitButton, "click", fit);
            listen(expand, "click", () => { collapsed.clear(); render(); fit(); });
            listen(collapse, "click", () => {
                all.forEach(node => { if (node.depth > 0 && node.children) collapsed.add(node.data.id); });
                selected = model; render(); fit();
            });
            listen(enlarge, "click", () => {
                modalTrigger = document.activeElement;
                dialogBody.append(shell);
                enlarge.hidden = true;
                dialog.showModal();
                fit();
                close.focus();
            });
            listen(close, "click", closeModal);
            listen(dialog, "cancel", event => { event.preventDefault(); closeModal(); });
            listen(dialog, "close", restoreShell);
            render();
            fit();
            if (global.ResizeObserver) {
                observer = new ResizeObserver(scheduleSize);
                observer.observe(viewport);
            } else listen(global, "resize", scheduleSize);
            const api = { destroy, fit };
            mounts.set(host, api);
            return api;
        } catch (error) {
            destroy();
            throw error;
        }
    }

    global.MiniParASTViewer = { mount };
})(window);
