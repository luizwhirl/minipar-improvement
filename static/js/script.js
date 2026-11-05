document.addEventListener("DOMContentLoaded", () => {
    const byId = id => document.getElementById(id);
    const source = byId("editor-minipar");
    const editor = window.CodeMirror?.fromTextArea(source, {
        mode: "text/x-c++src", theme: "dracula", lineNumbers: true,
        indentUnit: 4, lineWrapping: true
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
    let spec = null;

    function showTab(selected) {
        for (const tab of tabs) {
            const active = tab === selected;
            tab.setAttribute("aria-selected", String(active));
            tab.tabIndex = active ? 0 : -1;
            byId(tab.getAttribute("aria-controls")).hidden = !active;
        }
    }
    tabs.forEach((tab, index) => {
        tab.onclick = () => showTab(tab);
        tab.onkeydown = event => {
            const next = { ArrowRight: (index + 1) % tabs.length,
                ArrowLeft: (index + tabs.length - 1) % tabs.length,
                Home: 0, End: tabs.length - 1 }[event.key];
            if (next === undefined) return;
            event.preventDefault();
            showTab(tabs[next]);
            tabs[next].focus();
        };
    });

    function status(label) { byId("status").textContent = label; }
    function lock(value) { run.disabled = clear.disabled = examples.disabled = value; }
    function resetResults(message) {
        showTab(tabs[0]);
        terminalOutput.textContent = message;
        terminalOutput.classList.remove("error-text");
        byId("cpp-code").textContent = "Compile o programa para ver o C++.";
        byId("tac-code").textContent = "Compile o programa para ver o TAC.";
    }
    async function post(url, body) {
        const response = await fetch(url, { method: "POST",
            headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Falha na solicitação.");
        return data;
    }
    function showError(error) {
        status("Erro");
        terminalOutput.classList.add("error-text");
        terminalOutput.textContent = error.message;
    }

    connectSessionMonitor(terminalOutput, label => {
        status(label);
        lock(label === "Monitorando");
        showTab(tabs[0]);
    });
    fetch("/api/tests").then(res => res.json()).then(data => {
        for (const filename of data.tests) examples.add(new Option(filename, filename));
    }).catch(showError);

    examples.onchange = async () => {
        const filename = examples.value;
        if (!filename) return;
        lock(true);
        try {
            const [program, metadata] = await Promise.all([
                post("/api/get_test", { filename }), post("/api/test_spec", { filename })
            ]);
            setCode(program.code);
            spec = metadata;
            file.textContent = filename;
            resetResults("Programa carregado. Pronto para executar.");
            status("Pronto");
        } catch (error) { showError(error); }
        finally { lock(false); }
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
        lock(true);
        const filename = file.textContent;
        const code = getCode();
        resetResults("Preparando execução…");
        status("Preparando");
        try {
            const inputs = await collectInputs(spec);
            if (inputs === null || !await handleMultiComputer(spec, filename)) {
                status("Cancelado");
                terminalOutput.textContent = "Execução cancelada.";
                return;
            }
            status("Compilando");
            terminalOutput.textContent = "Compilando e executando o programa…";
            const data = await post("/api/compile", { code, filename, inputs });
            byId("cpp-code").textContent = data.cpp || "Nenhum código C++ gerado.";
            byId("tac-code").textContent = data.tac || "Nenhum TAC gerado.";
            if (!data.success) throw new Error(data.stderr || data.error || "Erro na execução.");
            terminalOutput.textContent = data.stdout || "Execução concluída.";
            status("Concluído");
        } catch (error) { showError(error); }
        finally { lock(false); }
    };

    clear.onclick = () => {
        setCode("");
        spec = null;
        examples.value = "";
        file.textContent = "ide_temp.minipar";
        resetResults("Compile o programa para ver a saída.");
        status("Pronto");
        if (editor?.focus) editor.focus();
        else source.focus();
    };
});
