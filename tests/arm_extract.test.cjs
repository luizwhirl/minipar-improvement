const test = require("node:test");
const assert = require("node:assert/strict");
const { START, END, extract, armFilename } = require("../static/js/arm-extract.js");

const asm = "    .global _start\n_start:\n    MOV R0, #2\n    BX LR";

test("extrai o bloco entre as marcas e ignora o resto da saída", () => {
    const output = `Expressao: (2+4)*7\nResultado: 42\n${START}\n${asm}\n${END}\nFim.\n`;
    assert.deepEqual(extract(output), { status: "found", code: asm + "\n" });
});

test("aceita fim de linha do Windows e espaços em volta das marcas", () => {
    const output = `  ${START}  \r\n${asm.replaceAll("\n", "\r\n")}\r\n${END}\r\n`;
    const result = extract(output);
    assert.equal(result.status, "found");
    assert.equal(result.code, asm + "\n");
    assert.ok(!result.code.includes("\r"));
});

test("tira linhas vazias do começo e do fim do bloco", () => {
    const result = extract(`${START}\n\n${asm}\n\n${END}`);
    assert.equal(result.code, asm + "\n");
});

test("sem marca de início não há Assembly", () => {
    assert.equal(extract("Resultado: 42\n").status, "missing");
    assert.equal(extract("").status, "missing");
    assert.equal(extract(undefined).status, "missing");
    assert.equal(extract(`${START}\n\n${END}`).status, "missing");
});

test("marca de início sem fim avisa que o bloco ficou aberto", () => {
    assert.equal(extract(`${START}\n${asm}\n`).status, "unclosed");
    assert.equal(extract(`${END}\n${START}\n${asm}\n`).status, "unclosed");
});

test("dois blocos não são juntados", () => {
    const one = `${START}\n${asm}\n${END}\n`;
    assert.equal(extract(one + one).status, "repeated");
    assert.equal(extract(`${START}\n${asm}\n${END}\n${END}\n`).status, "repeated");
});

test("o nome do .arm vem do nome do programa", () => {
    assert.equal(armFilename("teste11_minicompilador.minipar"), "teste11_minicompilador.arm");
    assert.equal(armFilename("C:\\pasta\\Meu Teste.MINIPAR"), "Meu_Teste.arm");
    assert.equal(armFilename(""), "programa.arm");
});
