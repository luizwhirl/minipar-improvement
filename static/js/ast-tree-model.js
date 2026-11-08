(function (root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    if (root) root.MiniParASTModel = api;
})(typeof window !== "undefined" ? window : null, function () {
    "use strict";

    const labels = {
        Program: "Programa", SeqBlock: "Bloco sequencial", ParBlock: "Bloco paralelo",
        VarDecl: "Declaração de variável", Assignment: "Atribuição", PrintStmt: "Impressão",
        NumberExpr: "Número", StringExpr: "Texto", BoolExpr: "Booleano",
        IdentifierExpr: "Identificador", BinaryExpr: "Operação binária", UnaryExpr: "Operação unária",
        IfStmt: "Condicional", WhileStmt: "Laço enquanto", DoWhileStmt: "Laço faça-enquanto",
        ForStmt: "Laço para", BreakStmt: "Interromper laço", ContinueStmt: "Próxima iteração",
        FuncDecl: "Declaração de função", ClassDecl: "Declaração de classe", ReturnStmt: "Retorno",
        MethodCall: "Chamada de método", FuncCallExpr: "Chamada de função", PropertyAccess: "Acesso a atributo",
        PropertyAssign: "Atribuição de atributo", NewExpr: "Novo objeto", ThisExpr: "Objeto atual",
        CChannelExpr: "Canal de comunicação", SendStmt: "Envio", ReceiveExpr: "Recebimento",
        InputExpr: "Entrada de dados", ListLiteral: "Lista", MatrixCreateExpr: "Criação de matriz",
        IndexExpr: "Acesso por índice", IndexAssign: "Atribuição por índice",
        ForkExpr: "Fork · iniciar tarefa", JoinExpr: "Join · aguardar tarefa"
    };
    const fieldLabels = {
        statements: "Instrução", left: "Operando esquerdo", right: "Operando direito",
        operand: "Operando", init_value: "Valor inicial", value: "Valor", arguments: "Argumento",
        condition: "Condição", then_branch: "Então", else_branch: "Senão", body: "Corpo",
        initializer: "Inicialização", increment: "Incremento", iterable: "Coleção percorrida",
        attributes: "Atributo", methods: "Método", object: "Objeto", channel: "Canal",
        message: "Mensagem", ip: "Endereço", port: "Porta", prompt: "Mensagem de entrada",
        elements: "Elemento", rows: "Linhas", cols: "Colunas", index: "Índice", target: "Destino",
        function_call: "Chamada paralela", task: "Tarefa"
    };
    const fieldOrder = {
        Program: ["statements"], SeqBlock: ["statements"], ParBlock: ["statements"],
        BinaryExpr: ["left", "right"], UnaryExpr: ["operand"], VarDecl: ["init_value"],
        Assignment: ["value"], PrintStmt: ["arguments"], IfStmt: ["condition", "then_branch", "else_branch"],
        WhileStmt: ["condition", "body"], DoWhileStmt: ["body", "condition"],
        ForStmt: ["initializer", "condition", "increment", "iterable", "body"],
        ClassDecl: ["attributes", "methods"], FuncDecl: ["body"], ReturnStmt: ["value"],
        MethodCall: ["object", "arguments"], FuncCallExpr: ["arguments"],
        PropertyAccess: ["object"], PropertyAssign: ["object", "value"], NewExpr: ["arguments"],
        CChannelExpr: ["ip", "port"], SendStmt: ["channel", "message"], ReceiveExpr: ["channel"],
        InputExpr: ["prompt"], ListLiteral: ["elements"], MatrixCreateExpr: ["rows", "cols", "init_value"],
        IndexExpr: ["object", "index"], IndexAssign: ["target", "value"],
        ForkExpr: ["function_call"], JoinExpr: ["task"]
    };
    const isNode = value => value !== null && typeof value === "object"
        && !Array.isArray(value) && typeof value.node_type === "string";
    const pointer = key => String(key).replace(/~/g, "~0").replace(/\//g, "~1");
    const clone = value => value === undefined ? null : JSON.parse(JSON.stringify(value));
    const containsNode = value => isNode(value) || (value !== null && typeof value === "object"
        && Object.values(value).some(containsNode));

    function summarize(node) {
        switch (node.node_type) {
        case "Program": case "SeqBlock": case "ParBlock": {
            const count = Array.isArray(node.statements) ? node.statements.length : 0;
            return `${count} ${count === 1 ? "instrução" : "instruções"}`;
        }
        case "StringExpr": return JSON.stringify(node.value ?? "");
        case "BoolExpr": return node.value ? "verdadeiro" : "falso";
        case "NumberExpr": return String(node.value ?? "");
        case "FuncDecl": return `${node.name ?? ""}(${(node.params || []).join(", ")})`;
        case "MethodCall": return String(node.method_name ?? "");
        case "NewExpr": return String(node.class_name ?? "");
        case "BinaryExpr": case "UnaryExpr": return String(node.op ?? "");
        case "ListLiteral": return `${(node.elements || []).length} elemento(s)`;
        default:
            return node.name !== undefined ? String(node.name)
                : node.property_name !== undefined ? String(node.property_name)
                : node.iterator_name ? String(node.iterator_name) : "";
        }
    }

    function buildASTTree(ast) {
        if (!isNode(ast)) throw new TypeError("A AST deve conter um tipo de nó (node_type).");

        function build(source, id, relation, relationLabel) {
            const node = { id, nodeType: source.node_type,
                label: Object.hasOwn(labels, source.node_type) ? labels[source.node_type] : source.node_type,
                summary: summarize(source), line: Number.isInteger(source.line) ? source.line : null,
                relation, relationLabel, attributes: {}, children: [] };
            const preferred = Object.hasOwn(fieldOrder, source.node_type) ? fieldOrder[source.node_type] : [];
            const keys = [...preferred.filter(key => Object.hasOwn(source, key)),
                ...Object.keys(source).filter(key => !preferred.includes(key))];

            function metadata(key, value) {
                Object.defineProperty(node.attributes, key,
                    { value: clone(value), enumerable: true, configurable: true, writable: true });
            }
            function collect(value, path, field, caption) {
                if (isNode(value)) {
                    node.children.push(build(value, path, field, caption));
                } else if (!containsNode(value)) {
                    metadata(field, value);
                } else if (Array.isArray(value)) {
                    value.forEach((item, index) => collect(item, `${path}/${index}`,
                        `${field}[${index}]`, `${caption} ${index + 1}`));
                } else {
                    Object.entries(value).forEach(([key, item]) => collect(item,
                        `${path}/${pointer(key)}`, `${field}.${key}`,
                        `${caption} · ${Object.hasOwn(fieldLabels, key) ? fieldLabels[key] : key}`));
                }
            }
            keys.forEach(key => {
                if (key !== "node_type" && key !== "line")
                    collect(source[key], `${id}/${pointer(key)}`, key,
                        Object.hasOwn(fieldLabels, key) ? fieldLabels[key] : key);
            });
            return node;
        }
        return build(ast, "root", "root", "Programa");
    }

    return { buildASTTree };
});
