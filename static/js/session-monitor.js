function connectSessionMonitor(terminalOutput, onStatus) {
    function formatProgressPanel(data) {
        const session = data.session;
        if (!session) return "";

        const myRole = session.participants?.find(
            p => p.terminal_id === data.terminal_id
        )?.role || "participante";

        const percent = session.progress_percent ?? 0;
        const filled = Math.floor(percent / 5);
        const bar = "█".repeat(filled) + "░".repeat(20 - filled);

        let text =
            "══ TERMINAL PARTICIPANTE — MONITOR DE PROGRESSO ══\n\n" +
            `Terminal : ${data.terminal_id}\n` +
            `Papel    : ${myRole}\n` +
            `Teste    : ${session.titulo || session.test_file}\n` +
            `Status   : ${session.phase_message || session.status}\n` +
            `[${bar}] ${percent}%\n\n` +
            "── LOG DE ATIVIDADE ──\n";

        (session.progress_log || []).forEach(entry => {
            const prefix = entry.source === "initiator" ? "→" : "•";
            text += `${prefix} [${entry.time}] ${entry.message}\n`;
        });

        if (session.execution_output) {
            text += "\n── SAÍDA DO INICIADOR ──\n";
            session.execution_output.trimEnd().split("\n").forEach(line => {
                text += `  ${line}\n`;
            });
        }

        if (session.status === "completed") {
            text += "\n✓ Teste concluído pelo terminal iniciador.\n";
        }

        return text;
    }

    function startProgressPoll(session) {
        onStatus("Monitorando");
        const url = "/api/session?created_at=" + encodeURIComponent(session.created_at);
        async function poll() {
            try {
                const response = await fetch(url, { cache: "no-store" });
                if (response.ok) {
                    const data = await response.json();
                    if (data.session) terminalOutput.textContent = formatProgressPanel(data);
                    if (!data.active) {
                        onStatus(data.session?.status === "completed" ? "Concluído" : "Encerrado");
                        return;
                    }
                }
            } catch {
                // Retry this session after a temporary connection failure.
            }
            setTimeout(poll, 500);
        }
        poll();
    }

    // Verifica sessão multi-terminal ativa ao carregar a IDE
    fetch("/api/session")
        .then(res => res.json())
        .then(data => {
            if (data.active && data.needs_choice) {
                showSessionChoiceDialog(data);
            } else if (data.active) {
                const isParticipant = data.session.participants?.some(
                    p => p.terminal_id === data.terminal_id
                );
                if (isParticipant && data.session.status !== "completed") {
                    startProgressPoll(data.session);
                } else {
                    terminalOutput.textContent =
                        `[Sessão ativa] Teste: ${data.session.titulo || data.session.test_file}\n` +
                        `Terminal: ${data.terminal_id}\n` +
                        `Participantes: ${data.session.participants.length}/${data.session.required_participants}`;
                }
            }
        });

    function showSessionChoiceDialog(sessionData) {
        const session = sessionData.session;
        const msg =
            `Teste em andamento: ${session.titulo || session.test_file}\n` +
            `Participantes: ${session.participants.length}/${session.required_participants}\n` +
            `Seu terminal: ${sessionData.terminal_id}\n\n` +
            `Deseja participar deste teste ou executar de forma independente?`;

        if (confirm(msg + "\n\nOK = Participar do teste\nCancelar = Modo independente")) {
            fetch("/api/session/join", { method: "POST" })
                .then(res => res.json())
                .then(result => {
                    if (result.success) {
                        const role = result.session.participants.slice(-1)[0].role;
                        terminalOutput.textContent =
                            `[OK] Você entrou como: ${role}\nIniciando monitor de progresso...\n`;
                        startProgressPoll(result.session);
                    }
                });
        }
    }

}
