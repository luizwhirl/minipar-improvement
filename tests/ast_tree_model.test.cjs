const test = require('node:test');
const assert = require('node:assert/strict');
const { buildASTTree } = require('../static/js/ast-tree-model.js');

function nodes(tree) {
    return [tree, ...tree.children.flatMap(nodes)];
}

function freeze(value) {
    if (value && typeof value === 'object') {
        Object.values(value).forEach(freeze);
        Object.freeze(value);
    }
    return value;
}

test('conditions and binary operands follow semantic order rather than JSON field order', () => {
    const source = {
        node_type: 'Program', line: 1, statements: [{
            node_type: 'IfStmt', line: 2,
            else_branch: { node_type: 'SeqBlock', line: 4, statements: [] },
            then_branch: { node_type: 'SeqBlock', line: 3, statements: [] },
            condition: {
                node_type: 'BinaryExpr', line: 2, op: '<',
                right: { node_type: 'NumberExpr', value: '3', line: 2 },
                left: { node_type: 'NumberExpr', value: '2', line: 2 }
            }
        }]
    };
    const tree = buildASTTree(source);
    const branch = tree.children[0];
    assert.equal(tree.id, 'root');
    assert.deepEqual(branch.children.map(child => child.relation), ['condition', 'then_branch', 'else_branch']);
    assert.deepEqual(branch.children.map(child => child.relationLabel), ['Condição', 'Então', 'Senão']);
    const condition = branch.children[0];
    assert.deepEqual(condition.children.map(child => child.relation), ['left', 'right']);
    assert.deepEqual(condition.children.map(child => child.attributes.value), ['2', '3']);
    assert.equal(condition.line, 2);
    assert.equal(nodes(tree).length, 7);
});

test('AST lists preserve each node and position while parameter lists remain metadata', () => {
    const source = {
        node_type: 'FuncDecl', name: 'greet', params: ['name', 'count'], line: 1,
        body: {
            node_type: 'SeqBlock', line: 1, statements: [{
                node_type: 'PrintStmt', line: 2, arguments: [
                    { node_type: 'StringExpr', value: 'Olá', line: 2 },
                    { node_type: 'IdentifierExpr', name: 'name', line: 2 }
                ]
            }, {
                node_type: 'ReturnStmt', value: { node_type: 'NumberExpr', value: '0', line: 3 }, line: 3
            }]
        }
    };
    const tree = buildASTTree(source);
    assert.deepEqual(tree.attributes.params, ['name', 'count']);
    assert.notEqual(tree.attributes.params, source.params);
    assert.deepEqual(tree.children.map(child => child.relation), ['body']);
    const statements = tree.children[0].children;
    assert.deepEqual(statements.map(child => child.relation), ['statements[0]', 'statements[1]']);
    assert.deepEqual(statements[0].children.map(child => child.relation), ['arguments[0]', 'arguments[1]']);
    assert.deepEqual(statements[0].children.map(child => child.nodeType), ['StringExpr', 'IdentifierExpr']);
    assert.equal(statements[1].children[0].attributes.value, '0');
    assert.equal(new Set(nodes(tree).map(node => node.id)).size, nodes(tree).length);
});

test('zero, false and Unicode or HTML-like strings are preserved as content', () => {
    const text = 'Ação <img src=x onerror="alert(1)"> & "aspas"';
    const tree = buildASTTree({
        node_type: 'Program', line: 1, statements: [
            { node_type: 'NumberExpr', value: 0, line: 2 },
            { node_type: 'BoolExpr', value: false, line: 3 },
            { node_type: 'StringExpr', value: text, line: 4 }
        ]
    });
    assert.equal(tree.children[0].attributes.value, 0);
    assert.equal(tree.children[1].attributes.value, false);
    assert.equal(tree.children[2].attributes.value, text);
    assert.ok(tree.children[2].summary.includes('Ação <img src=x'));
    assert.equal(tree.children[2].line, 4);
    assert.equal(tree.children.length, 3);
});

test('building or interacting with the derived tree cannot mutate source AST data', () => {
    const source = freeze({
        node_type: 'FuncDecl', name: 'read', params: ['a', 'b'], line: 1,
        body: { node_type: 'SeqBlock', line: 1, statements: [] }
    });
    const original = JSON.stringify(source);
    const first = buildASTTree(source);
    assert.deepEqual(buildASTTree(source), first);
    first.attributes.params.push('derived-only');
    first.children.length = 0;
    assert.equal(JSON.stringify(source), original);
    assert.deepEqual(buildASTTree(source).attributes.params, ['a', 'b']);
    assert.equal(buildASTTree(source).children.length, 1);
});

test('an empty program remains a visible root without fabricated child nodes', () => {
    const tree = buildASTTree({ node_type: 'Program', statements: [], line: 1 });
    assert.equal(tree.nodeType, 'Program');
    assert.equal(tree.label, 'Programa');
    assert.equal(tree.relation, 'root');
    assert.deepEqual(tree.children, []);
    assert.deepEqual(tree.attributes.statements, []);
    assert.equal(tree.line, 1);
});

test('new node types keep nested nodes and metadata instead of silently dropping them', () => {
    const tree = buildASTTree({
        node_type: 'FutureExpr', line: 8, enabled: false, options: [0, false, 'ação'],
        payload: { node_type: 'IdentifierExpr', name: 'work', line: 8 },
        items: [{ node_type: 'NumberExpr', value: '9', line: 8 }, 'metadata']
    });
    assert.equal(tree.nodeType, 'FutureExpr');
    assert.equal(tree.label, 'FutureExpr');
    assert.equal(tree.attributes.enabled, false);
    assert.deepEqual(tree.attributes.options, [0, false, 'ação']);
    assert.equal(tree.attributes['items[1]'], 'metadata');
    assert.deepEqual(tree.children.map(child => child.nodeType), ['IdentifierExpr', 'NumberExpr']);
    assert.deepEqual(tree.children.map(child => child.relation), ['payload', 'items[0]']);
    assert.equal(tree.children[0].id, 'root/payload');
    assert.equal(tree.children[1].id, 'root/items/0');
});
