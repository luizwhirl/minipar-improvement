document.addEventListener("DOMContentLoaded", () => {
    const byId = id => document.getElementById(id);
    const source = byId("editor-minipar");
    const editor = window.CodeMirror?.fromTextArea(source, {
        mode: "text/x-c++src", theme: "dracula", lineNumbers: true,
        indentUnit: 4, lineWrapping: true,
        screenReaderLabel: source.getAttribute("aria-label")
    });
    const getCode = () => editor?.getValue ? editor.getValue() : source.value;
    function setCode(code) {
        if (editor?.setValue) editor.setValue(code);
        else source.value = code;
    }
    const examples = byId("examples");
    const terminalOutput = byId("terminal-output");
    const file = byId("current-file");
    const run = byId("btn-run");
    const clear = byId("btn-clear");
    const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
    const executionTab = byId("tab-exec");
    const results = document.querySelector(".results");
    const phases = ["tokens", "ast", "semantic", "tac", "cpp"];
    const phaseNames = {
        tokens: "Análise léxica", ast: "Análise sintática",
        semantic: "Análise semântica", tac: "Geração de TAC", cpp: "Geração de C++"
    };
    const phasePrompts = {
        tokens: "Selecione Tokens para analisar o código atual.",
        ast: "Selecione AST para analisar a estrutura do código atual.",
        semantic: "Selecione Semântica para verificar o código atual.",
        tac: "Selecione TAC para gerar o código intermediário.",
        cpp: "Selecione Código C++ para gerar a tradução do programa."
    };
    const loadingMessages = {
        tokens: "Reconhecendo tokens…", ast: "Construindo a árvore sintática…",
        semantic: "Verificando a semântica…", tac: "Gerando TAC…", cpp: "Gerando código C++…"
    };
    const phaseViews = Object.fromEntries(phases.map(phase => [phase, {
        panel: byId(`out-${phase}`), feedback: byId(`${phase}-feedback`),
        diagnostics: byId(`${phase}-diagnostics`),
        content: byId({ tac: "tac-code", cpp: "cpp-code" }[phase] || `${phase}-result`)
    }]));
    const phaseCache = new Map();
    let spec = null;
    let executionStatus = "Pronto";
    let sourceRevision = 0;
    let analysisSequence = 0;
    let activeAnalysis = null;
    let executionBusy = false;
    let monitoring = false;
    let loadingExample = false;
    let astViewer = null;
    let astSource = null;

    const controlsBusy = () => executionBusy || monitoring || loadingExample;

    function showTab(selected, revealResult = false) {
        for (const tab of tabs) {
            const active = tab === selected;
            tab.setAttribute("aria-selected", String(active));
            tab.tabIndex = active ? 0 : -1;
            byId(tab.getAttribute("aria-controls")).hidden = !active;
        }
        if (revealResult && window.matchMedia("(max-width: 800px)").matches) {
            results.scrollIntoView({ block: "nearest" });
        }
    }
    tabs.forEach((tab, index) => {
        tab.onclick = () => activateTab(tab, true);
        tab.onkeydown = event => {
            const next = { ArrowRight: (index + 1) % tabs.length,
                ArrowLeft: (index + tabs.length - 1) % tabs.length,
                Home: 0, End: tabs.length - 1 }[event.key];
            if (next === undefined) return;
            event.preventDefault();
            activateTab(tabs[next]);
            tabs[next].focus();
        };
    });

    function status(label, forExecution = false) {
        if (forExecution) executionStatus = label;
        byId("status").textContent = label;
        byId("status").dataset.state = label === "Erro" ? "error" : "ready";
    }
    function syncControls() {
        const value = controlsBusy();
        run.disabled = clear.disabled = examples.disabled = value;
        source.readOnly = value;
        editor?.setOption?.("readOnly", value);
        results.setAttribute("aria-busy", String(value));
    }

    function destroyASTViewer() {
        const previous = astViewer;
        astViewer = null;
        astSource = null;
        try {
            previous?.destroy();
        } catch {
            // Keep clearing obsolete results if a visual control could not close.
        }
    }

    function resetPhase(phase, message = phasePrompts[phase], preserveContent = false) {
        const view = phaseViews[phase];
        view.panel.removeAttribute("aria-busy");
        view.feedback.className = "phase-feedback";
        view.feedback.textContent = message;
        view.diagnostics.replaceChildren();
        view.diagnostics.hidden = true;
        if (preserveContent) return;
        if (phase === "ast") destroyASTViewer();
        view.content.replaceChildren();
        view.content.hidden = true;
    }

    function cancelAnalysis() {
        analysisSequence++;
        const pending = activeAnalysis;
        activeAnalysis = null;
        if (!pending) return;
        pending.controller.abort();
        resetPhase(pending.phase);
    }

    function clearPhaseResults() {
        cancelAnalysis();
        phaseCache.clear();
        phases.forEach(phase => resetPhase(phase));
    }

    function resetResults(message, selectExecution = true, clearPhases = true) {
        if (clearPhases) clearPhaseResults();
        else cancelAnalysis();
        if (selectExecution) showTab(executionTab);
        executionStatus = "Pronto";
        terminalOutput.textContent = message;
        terminalOutput.classList.remove("error-text");
    }

    async function post(url, body, signal) {
        const response = await fetch(url, { method: "POST",
            headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Falha na solicitação.");
        return data;
    }
    function showError(error) {
        if (monitoring) return;
        cancelAnalysis();
        status("Erro", true);
        showTab(executionTab);
        terminalOutput.classList.add("error-text");
        terminalOutput.textContent = error.message;
    }

    function invalidateResults() {
        sourceRevision++;
        resetResults("Código alterado. Execute novamente para atualizar os resultados.", false);
        if (!controlsBusy()) status("Código alterado", true);
    }
    if (editor?.on) editor.on("change", invalidateResults);
    else source.addEventListener("input", invalidateResults);

    function renderDiagnostics(phase, diagnostics) {
        const container = phaseViews[phase].diagnostics;
        container.replaceChildren();
        container.hidden = !diagnostics.length;
        if (!diagnostics.length) return;
        const list = document.createElement("ul");
        list.className = "diagnostic-list";
        for (const diagnostic of diagnostics) {
            const item = document.createElement("li");
            const location = document.createElement("strong");
            let label = phaseNames[diagnostic.phase] || "Análise";
            if (Number.isInteger(diagnostic.line) && diagnostic.line > 0) {
                label += ` · linha ${diagnostic.line}`;
                if (Number.isInteger(diagnostic.column) && diagnostic.column > 0) {
                    label += `, coluna ${diagnostic.column}`;
                }
            }
            location.textContent = label;
            const message = document.createElement("p");
            message.textContent = diagnostic.message;
            item.append(location, message);
            list.append(item);
        }
        container.append(list);
    }

    function renderTokens(container, tokens) {
        const scroller = document.createElement("div");
        scroller.className = "table-scroll";
        scroller.tabIndex = 0;
        scroller.setAttribute("role", "region");
        scroller.setAttribute("aria-label", "Tabela de tokens");
        const table = document.createElement("table");
        table.className = "token-table";
        const caption = document.createElement("caption");
        caption.textContent = "Tokens do código atual";
        const head = document.createElement("thead");
        const headings = document.createElement("tr");
        for (const label of ["Tipo", "Lexema", "Linha", "Coluna"]) {
            const cell = document.createElement("th");
            cell.scope = "col";
            cell.textContent = label;
            headings.append(cell);
        }
        head.append(headings);
        const body = document.createElement("tbody");
        for (const token of tokens) {
            const row = document.createElement("tr");
            if (token.type === "UNKNOWN") row.className = "token-error";
            for (const value of [token.type, JSON.stringify(token.lexeme), token.line, token.column]) {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.append(cell);
            }
            body.append(row);
        }
        table.append(caption, head, body);
        scroller.append(table);
        container.append(scroller);
    }

    function renderAST(ast) {
        const host = phaseViews.ast.content;
        host.hidden = false;
        if (astSource === ast && host.hasChildNodes()) return;
        destroyASTViewer();
        host.replaceChildren();
        astSource = ast;
        try {
            if (!window.MiniParASTViewer?.mount) throw new Error("Visualização indisponível.");
            astViewer = window.MiniParASTViewer.mount(host, ast);
        } catch {
            destroyASTViewer();
            host.replaceChildren();
            astSource = ast;
            const notice = document.createElement("p");
            notice.className = "ast-fallback";
            notice.textContent = "Não foi possível abrir a árvore interativa. A estrutura completa do programa continua disponível abaixo.";
            const json = document.createElement("pre");
            json.id = "ast-code";
            json.className = "structured-code";
            json.textContent = JSON.stringify(ast, null, 2);
            host.append(notice, json);
        }
    }

    function renderPhase(phase, data) {
        const view = phaseViews[phase];
        resetPhase(phase, phasePrompts[phase], phase === "ast" && data.success);
        view.feedback.classList.add(data.success ? "is-success" : "is-error");
        view.feedback.textContent = data.success ? "Etapa concluída para o código atual."
            : `A análise foi interrompida: ${phaseNames[data.failed_phase] || "falha em uma etapa anterior"}.`;
        renderDiagnostics(phase, data.diagnostics || []);

        if (phase === "tokens" && Array.isArray(data.result?.tokens)) {
            renderTokens(view.content, data.result.tokens);
            view.content.hidden = false;
        } else if (data.success) {
            if (phase === "ast") renderAST(data.result);
            else if (phase === "semantic") view.content.textContent = data.result.message;
            else view.content.textContent = data.result || "Nenhuma instrução foi gerada para este programa.";
            view.content.hidden = false;
        }
    }

    async function activateTab(tab, revealResult = false) {
        showTab(tab, revealResult);
        cancelAnalysis();
        if (tab === executionTab) {
            if (!controlsBusy()) status(executionStatus);
            return;
        }
        const phase = tab.id.replace("tab-", "");
        if (phaseCache.has(phase)) {
            const cached = phaseCache.get(phase);
            renderPhase(phase, cached);
            if (!controlsBusy()) status(cached.success ? "Concluído" : "Erro");
            return;
        }
        if (controlsBusy()) {
            resetPhase(phase, loadingExample ? "Aguarde o carregamento do programa para analisar esta etapa."
                : "Aguarde a conclusão da execução para analisar esta etapa.");
            return;
        }
        const request = {
            id: ++analysisSequence, phase, revision: sourceRevision,
            code: getCode(), controller: new AbortController()
        };
        activeAnalysis = request;
        const view = phaseViews[phase];
        resetPhase(phase, loadingMessages[phase]);
        view.panel.setAttribute("aria-busy", "true");
        status("Analisando");
        const isCurrent = () => activeAnalysis === request && request.id === analysisSequence
            && request.revision === sourceRevision && request.code === getCode() && !controlsBusy();
        try {
            const data = await post("/api/analyze", { code: request.code, phase }, request.controller.signal);
            if (!isCurrent()) return;
            phaseCache.set(phase, data);
            renderPhase(phase, data);
            status(data.success ? "Concluído" : "Erro");
        } catch (error) {
            if (error.name === "AbortError" || !isCurrent()) return;
            resetPhase(phase, error.message);
            view.feedback.classList.add("is-error");
            status("Erro");
        } finally {
            if (activeAnalysis === request) {
                activeAnalysis = null;
                view.panel.removeAttribute("aria-busy");
            }
        }
    }

    function cacheGeneratedPhase(phase, value) {
        if (typeof value !== "string" || !value.length) return;
        const data = { success: true, phase, failed_phase: null, result: value, diagnostics: [] };
        phaseCache.set(phase, data);
        renderPhase(phase, data);
    }

    connectSessionMonitor(terminalOutput, label => {
        monitoring = label === "Monitorando";
        cancelAnalysis();
        status(label, true);
        syncControls();
        showTab(executionTab);
    });
    fetch("/api/tests").then(res => res.json()).then(data => {
        for (const filename of data.tests) examples.add(new Option(filename, filename));
    }).catch(showError);

    examples.onchange = async () => {
        const filename = examples.value;
        if (!filename || controlsBusy()) return;
        loadingExample = true;
        sourceRevision++;
        resetResults("Carregando programa…");
        syncControls();
        if (!monitoring) status("Carregando", true);
        try {
            const [program, metadata] = await Promise.all([
                post("/api/get_test", { filename }), post("/api/test_spec", { filename })
            ]);
            if (monitoring) return;
            setCode(program.code);
            spec = metadata;
            file.textContent = filename;
            resetResults("Programa carregado. Pronto para executar.");
            status("Pronto", true);
        } catch (error) { showError(error); }
        finally {
            loadingExample = false;
            syncControls();
        }
    };

    async function collectInputs(spec) {
        if (!spec || !spec.requires_input || !spec.inputs.length) return [];

        let msg =
            `${spec.titulo}\n\n` +
            `Este programa possui ${spec.input_count || spec.inputs.length} entrada(s) input().\n` +
            `Informe os valores que serão enviados ao programa:\n\n`;
        spec.inputs.forEach((inp, i) => {
            const desc = inp.descricao || inp.prompt || `Entrada ${i + 1}`;
            msg += `[${i + 1}] ${desc}\n`;
        });
        alert(msg);

        const collected = [];
        for (let i = 0; i < spec.inputs.length; i++) {
            const inp = spec.inputs[i];
            const desc = inp.descricao || inp.prompt || `Entrada ${i + 1}`;
            const valor = prompt(`${desc}\n\nDigite o valor:`);
            if (valor === null) return null;
            collected.push(valor.trim());
        }
        return collected;
    }

    async function handleMultiComputer(spec, filename) {
        if (!spec || !spec.multi_computer || !spec.multi_computer.required) return true;

        const multi = spec.multi_computer;
        let msg =
            `${spec.titulo}\n\n${spec.descricao}\n\n` +
            `Este teste exige ${multi.count} computador(es/terminais).\n\n` +
            `Papéis:\n`;
        multi.roles.forEach((role, i) => { msg += `  [${i + 1}] ${role}\n`; });
        msg += `\n${multi.instrucoes}\n\n` +
            `Abra outro terminal e execute: python main.py\n` +
            `Escolha 'Continuar teste em andamento' no novo terminal.\n\n` +
            `Pressione OK quando o(s) outro(s) terminal(is) estiver(em) pronto(s).`;

        if (!confirm(msg)) return false;

        await fetch("/api/session/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename })
        });

        terminalOutput.textContent =
            "Aguardando participantes nos outros terminais...\n" +
            "Abra outro terminal com: python main.py\n";

        let connected = 1;
        const required = multi.count;
        for (let i = 0; i < 60; i++) {
            await new Promise(resolve => setTimeout(resolve, 500));
            const res = await fetch("/api/session");
            const data = await res.json();
            if (data.session) {
                connected = data.session.participants.length;
                terminalOutput.textContent =
                    `Aguardando participantes... ${connected}/${required} conectados (${i + 1}s)\n` +
                    (data.session.progress_log || []).slice(-5).map(e =>
                        `• [${e.time}] ${e.message}`
                    ).join("\n");
                if (connected >= required) break;
            }
        }

        await fetch("/api/session/ready", { method: "POST" });
        return true;
    }

    run.onclick = async () => {
        if (controlsBusy()) return;
        cancelAnalysis();
        executionBusy = true;
        syncControls();
        const filename = file.textContent;
        const code = getCode();
        const revision = sourceRevision;
        resetResults("Preparando execução…", true, false);
        status("Preparando", true);
        try {
            const inputs = await collectInputs(spec);
            if (monitoring) return;
            if (inputs === null || !await handleMultiComputer(spec, filename)) {
                if (!monitoring) {
                    status("Cancelado", true);
                    terminalOutput.textContent = "Execução cancelada.";
                }
                return;
            }
            if (monitoring) return;
            status("Compilando", true);
            terminalOutput.textContent = "Compilando e executando o programa…";
            const data = await post("/api/compile", { code, filename, inputs });
            if (revision !== sourceRevision || code !== getCode()) return;
            cacheGeneratedPhase("cpp", data.cpp);
            cacheGeneratedPhase("tac", data.tac);
            if (!data.success) throw new Error(data.stderr || data.error || "Erro na execução.");
            if (!monitoring) {
                terminalOutput.textContent = data.stdout || "Execução concluída.";
                status("Concluído", true);
            }
        } catch (error) { showError(error); }
        finally {
            executionBusy = false;
            syncControls();
        }
    };

    clear.onclick = () => {
        if (controlsBusy()) return;
        sourceRevision++;
        setCode("");
        spec = null;
        examples.value = "";
        file.textContent = "ide_temp.minipar";
        resetResults("Execute o programa para ver a saída.");
        status("Pronto", true);
        if (editor?.focus) editor.focus();
        else source.focus();
    };
});
