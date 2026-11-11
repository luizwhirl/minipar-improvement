const test = require("node:test");
const assert = require("node:assert/strict");
const { consume } = require("../static/js/execution-stream.js");

function response(chunks, onCancel = () => {}) {
    return new Response(new ReadableStream({
        start(controller) {
            for (const chunk of chunks) controller.enqueue(chunk);
            controller.close();
        },
        cancel: onCancel
    }), { headers: { "Content-Type": "application/x-ndjson; charset=utf-8" } });
}
const bytes = text => new TextEncoder().encode(text);

test("decodes split UTF-8 and JSON and accepts the final record without newline", async () => {
    const text = JSON.stringify({ type: "output", stream: "stdout", text: "Olá 🧵\n" })
        + "\n" + JSON.stringify({ type: "complete", success: true, exit_code: 0 });
    const encoded = bytes(text);
    const events = [];
    const result = await consume(response(Array.from(encoded, byte => new Uint8Array([byte]))), event => events.push(event));
    assert.equal(events[0].text, "Olá 🧵\n");
    assert.equal(events.length, 2);
    assert.equal(result.success, true);
});

test("dispatches output immediately before the completion chunk exists", async () => {
    let stream;
    const result = new Response(new ReadableStream({ start(controller) { stream = controller; } }),
        { headers: { "Content-Type": "application/x-ndjson" } });
    const events = [];
    let received;
    const first = new Promise(resolve => { received = resolve; });
    const consuming = consume(result, event => { events.push(event); received(); });
    stream.enqueue(bytes('{"type":"output","stream":"stdout","text":"primeiro"}\n'));
    await first;
    assert.deepEqual(events.map(event => event.type), ["output"]);
    stream.enqueue(bytes('{"type":"complete","success":true}\n'));
    stream.close();
    await consuming;
});

test("reports a non-successful execution without losing its output", async () => {
    const events = [];
    const completed = await consume(response([bytes(
        '{"type":"output","stream":"stderr","text":"falhou"}\n'
        + '{"type":"error","message":"código 2"}\n'
        + '{"type":"complete","success":false,"exit_code":2}\n'
    )]), event => events.push(event));
    assert.equal(completed.exit_code, 2);
    assert.equal(events[0].text, "falhou");
});

test("rejects premature EOF and malformed messages", async () => {
    for (const content of [
        '{"type":"output","stream":"stdout","text":"parcial"}\n',
        '{bad json}\n',
        '{"type":"complete","success":"true"}\n',
        '{"type":"output","stream":"stdin","text":"invalido"}\n',
        '{"type":"complete","success":true}\n{"type":"complete","success":true}\n'
    ]) await assert.rejects(consume(response([bytes(content)]), () => {}));
});

test("cancels an open response when its consumer fails", async () => {
    let cancelled = false;
    const result = new Response(new ReadableStream({
        start(controller) { controller.enqueue(bytes('{"type":"output","stream":"stdout","text":"x"}\n')); },
        cancel() { cancelled = true; }
    }), { headers: { "Content-Type": "application/x-ndjson" } });
    await assert.rejects(consume(result, () => { throw Error("UI removed"); }), /UI removed/);
    assert.equal(cancelled, true);
});

test("handles HTTP errors and rejects an unexpected response type", async () => {
    await assert.rejects(consume(new Response('{"error":"Código vazio"}', { status: 400 }), () => {}), /Código vazio/);
    await assert.rejects(consume(new Response("invalid"), () => {}), /fluxo de execução/);
});
