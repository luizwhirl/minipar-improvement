(function (root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    else root.MiniParArmExtract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    // Combinado com o Teste 11: o programa imprime o Assembly ARMv7
    // entre estas duas linhas. Tudo o que estiver entre elas vira o .arm.
    const START = "=== INICIO ARM ===";
    const END = "=== FIM ARM ===";

    // Procura o bloco na saída do programa.
    // Respostas possíveis:
    //   { status: "found", code }  bloco encontrado (code termina com "\n")
    //   { status: "missing" }      a saída não tem a linha de início
    //   { status: "unclosed" }     tem início, mas falta a linha de fim
    //   { status: "repeated" }     mais de um bloco; não dá para saber qual baixar
    function extract(output) {
        const lines = String(output ?? "").split("\n")
            .map(line => line.endsWith("\r") ? line.slice(0, -1) : line);
        const starts = [];
        const ends = [];
        lines.forEach((line, index) => {
            const mark = line.trim();
            if (mark === START) starts.push(index);
            else if (mark === END) ends.push(index);
        });
        if (!starts.length) return { status: "missing" };
        if (starts.length > 1) return { status: "repeated" };
        const end = ends.find(index => index > starts[0]);
        if (end === undefined) return { status: "unclosed" };
        if (ends.length > 1) return { status: "repeated" };
        const block = lines.slice(starts[0] + 1, end);
        while (block.length && block[block.length - 1].trim() === "") block.pop();
        while (block.length && block[0].trim() === "") block.shift();
        if (!block.length) return { status: "missing" };
        return { status: "found", code: block.join("\n") + "\n" };
    }

    // Nome do arquivo baixado: o nome do programa com a extensão .arm.
    function armFilename(sourceName) {
        const base = String(sourceName || "").split(/[\\/]/).pop()
            .replace(/\.minipar$/i, "").replace(/[^\w.-]+/g, "_");
        return (base || "programa") + ".arm";
    }

    return { START, END, extract, armFilename };
});
