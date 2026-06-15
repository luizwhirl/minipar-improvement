document.addEventListener("DOMContentLoaded", () => {
    // Inicialização das Caixas de Texto com CodeMirror (Design de IDE)
    const editorMinipar = CodeMirror.fromTextArea(document.getElementById("editor-minipar"), {
        mode: "clike",
        theme: "dracula",
        lineNumbers: true,
        autoCloseBrackets: true
    });

    const editorCpp = CodeMirror.fromTextArea(document.getElementById("editor-cpp"), {
        mode: "text/x-c++src",
        theme: "dracula",
        lineNumbers: true,
        readOnly: true
    });

    const editorTac = CodeMirror.fromTextArea(document.getElementById("editor-tac"), {
        mode: "clike",
        theme: "dracula",
        lineNumbers: true,
        readOnly: true
    });

    const testList       = document.getElementById("test-list");
    const currentFileLabel = document.getElementById("current-file");
    const terminalOutput = document.getElementById("terminal-output");
    const btnRun         = document.getElementById("btn-run");
    const btnClear       = document.getElementById("btn-clear");
    const tabs           = document.querySelectorAll(".tab");

    // Lógica das Abas C++ / TAC
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(tab.dataset.target).classList.add("active");

            // Recarrega visualmente os editores após troca de aba
            editorCpp.refresh();
            editorTac.refresh();
        });
    });

    // Puxar os testes da pasta '/tests'
    fetch("/api/tests")
        .then(res => res.json())
        .then(data => {
            data.tests.forEach(test => {
                const li = document.createElement("li");
                li.textContent = test;
                li.onclick = () => loadTest(test, li);
                testList.appendChild(li);
            });
        });

    function loadTest(filename, element) {
        document.querySelectorAll(".test-list li").forEach(li => li.classList.remove("active"));
        if (element) element.classList.add("active");

        currentFileLabel.textContent = filename;
        terminalOutput.textContent = `Carregando ${filename}...`;
        terminalOutput.classList.remove("error-text");

        fetch("/api/get_test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename })
        })
        .then(res => res.json())
        .then(data => {
            if (data.code) {
                editorMinipar.setValue(data.code);
                editorCpp.setValue("");
                editorTac.setValue("");
                terminalOutput.textContent = "Arquivo carregado. Clique em 'Compile & Run'.";
            }
        });
    }

    // FIX: desabilita o botão enquanto compila para evitar cliques duplos
    // e garante que ele volte ao estado normal sempre (mesmo em caso de erro)
    function setCompiling(state) {
        btnRun.disabled = state;
        btnRun.textContent = state ? "⏳ Compilando..." : "▶ Compile & Run";
    }

    // Botão de Compilar
    btnRun.onclick = () => {
        const code     = editorMinipar.getValue();
        const filename = currentFileLabel.textContent;

        setCompiling(true);
        terminalOutput.textContent = "Rodando compilador...";
        terminalOutput.classList.remove("error-text");

        fetch("/api/compile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code, filename })
        })
        .then(res => res.json())
        .then(data => {
            if (data.cpp) editorCpp.setValue(data.cpp);
            if (data.tac) editorTac.setValue(data.tac);

            // FIX: força refresh nos dois editores após receber os dados,
            // independente de qual aba está ativa — resolve dessincronismo de layout
            setTimeout(() => {
                editorCpp.refresh();
                editorTac.refresh();
            }, 50);

            if (data.success) {
                terminalOutput.textContent = data.stdout || "Compilação concluída com sucesso!";
                terminalOutput.classList.remove("error-text");
            } else {
                terminalOutput.textContent = data.stderr || data.error || "Erro na execução.";
                terminalOutput.classList.add("error-text");
            }
        })
        .catch(err => {
            terminalOutput.textContent = "Erro de conexão com o servidor Backend.";
            terminalOutput.classList.add("error-text");
        })
        .finally(() => {
            // FIX: sempre reativa o botão ao fim, seja sucesso ou erro
            setCompiling(false);
        });
    };

    // Botão de Limpar (Novo arquivo)
    btnClear.onclick = () => {
        editorMinipar.setValue("");
        editorCpp.setValue("");
        editorTac.setValue("");
        currentFileLabel.textContent = "ide_temp.minipar";
        document.querySelectorAll(".test-list li").forEach(li => li.classList.remove("active"));
        terminalOutput.textContent = "Workspace limpo. Pode começar a digitar.";
        terminalOutput.classList.remove("error-text");
    };
});