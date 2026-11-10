(function (root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    else root.MiniParExecutionStream = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    async function consume(response, onEvent) {
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Não foi possível iniciar a execução.");
        }
        if (!response.body || !response.headers.get("content-type")?.includes("application/x-ndjson")) {
            throw new Error("O servidor não retornou o fluxo de execução esperado.");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = "";
        let completed = null;
        let finished = false;
        function dispatch(line) {
            if (!line.trim()) return;
            let event;
            try { event = JSON.parse(line); }
            catch { throw new Error("O servidor enviou uma mensagem de execução inválida."); }
            if (!event || !["phase", "output", "error", "complete"].includes(event.type)
                || completed
                || (event.type === "output" && (typeof event.text !== "string"
                    || !["stdout", "stderr"].includes(event.stream)))
                || (event.type === "complete" && typeof event.success !== "boolean")) {
                throw new Error("O servidor enviou uma mensagem de execução inválida.");
            }
            if (event.type === "complete") completed = event;
            onEvent(event);
        }
        try {
            while (true) {
                const { value, done } = await reader.read();
                pending += done ? decoder.decode() : decoder.decode(value, { stream: true });
                let newline;
                while ((newline = pending.indexOf("\n")) !== -1) {
                    dispatch(pending.slice(0, newline));
                    pending = pending.slice(newline + 1);
                }
                if (done) break;
            }
            if (pending.trim()) dispatch(pending);
            if (!completed) throw new Error("A conexão foi interrompida antes do fim da execução. Tente novamente.");
            finished = true;
            return completed;
        } finally {
            if (!finished) await reader.cancel().catch(() => {});
            reader.releaseLock();
        }
    }
    return { consume };
});
