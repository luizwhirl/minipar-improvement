# Compilador MiniPar
Trabalho de Compiladores - UFAL 


Arquitetura orientada a objetos baseada na versão C++ original, agora expandida para incluir **Geração de Código Intermediário (TAC)** de 3 endereços e uma nova **IDE Web**, capaz de gerar, compilar e executar o código C++ produzido pelo compilador.
Desenvolvido por:

Emanuele Vitória de Jesus Lima - [Manu-Vii](https://github.com/Manu-Vii)

José Lucas de Oliveira Quintela - [lucasqtl](https://github.com/lucasqtl)

Luiz Miguel de Melo Bomfim - [luizwhirl](https://github.com/luizwhirl)

---

## Estrutura do Projeto

```text
minipar_python/
├── src/
│   ├── ast_nodes.py      # Nós da AST (dataclasses)
│   ├── lexer.py          # Analisador Léxico
│   ├── parser.py         # Analisador Sintático
│   ├── semantic.py       # Analisador Semântico
│   ├── tac.py            # Gerador de Código Intermediário (TAC)
│   ├── codegen.py        # Gerador de Código C++
│   └── cpp_template.py   # Template base em C++
├── static/               # Arquivos estáticos da IDE Web (CSS, JS)
├── templates/            # Arquivos HTML da IDE Web
├── tests/                # Exemplos e testes .minipar
├── output/               # Arquivos gerados (.cpp, .tac e executáveis)
├── temp_code/            # Códigos temporários executados pela IDE
├── app.py                # Servidor Flask da Interface Web
├── main.py               # Ponto de entrada principal (CLI e Interativo)
├── menu.py               # Menu interativo para terminal
├── requirements.txt      # Dependências Python
└── README.md
```

---

## Requisitos

- Python 3.8 ou superior
- `g++` disponível no PATH (para compilar o código C++ gerado)
- Flask (para executar a IDE Web)

Instalação das dependências:

```bash
pip install -r requirements.txt
```

---

## Como Usar

O compilador oferece múltiplas formas de interação.

### 1. Menu Interativo (Terminal ou IDE Web)

Execute o programa sem argumentos:

```bash
python main.py
```

Opções disponíveis:

- **[1] Modo Terminal**: navegação pelos testes através de um menu textual.
- **[2] Modo Web Interface**: inicia o servidor Flask.

Após iniciar o servidor, acesse a interface Web:

- **Interface didática (2026.2):** http://127.0.0.1:5000/

O modo Terminal continua disponível pelo menu, independentemente da interface Web.

A IDE permite:

- Editar código MiniPar
- Compilar o programa
- Visualizar o código TAC gerado
- Visualizar o código C++ gerado
- Executar o programa e ver a saída

Na interface didática, cada opção da barra analisa o código atual do editor:

- **Tokens:** tipo, texto, linha e coluna dos tokens reconhecidos pelo lexer.
- **AST:** árvore gráfica dos nós produzidos pelo parser, com zoom, navegação,
  expansão de ramos e detalhes dos nós; o JSON completo também fica disponível.
- **Semântica:** resultado da validação e os diagnósticos encontrados.
- **TAC** e **Código C++:** código gerado sem compilar ou executar o programa.

As análises não solicitam entradas de `input()` nem iniciam sessões de execução.
Se uma fase anterior falhar, o painel informa onde a análise parou. Alterar o
código invalida os resultados anteriores; selecionar uma fase novamente analisa
a nova versão.

Na AST, selecione um nó para consultar seu tipo, a linha do código e seus
atributos. Os ramos podem ser expandidos ou recolhidos, e os controles de zoom e
ajuste ajudam a navegar em árvores maiores. A visualização pode ser ampliada em
uma janela própria; o JSON original permanece acessível para consulta.

A árvore utiliza uma cópia local do [D3.js 7.9.0](https://github.com/d3/d3/releases/tag/v7.9.0),
em `static/vendor/`, sem carregar essa biblioteca de um CDN. Sua licença ISC está
em `static/vendor/d3-LICENSE.txt`.

**Compilar/Baixar** permanece indisponível enquanto não houver suporte ao download
do executável. **Executar** mantém a operação atual: compila o programa, executa o
binário no servidor e apresenta a saída.

A API de fases usa `POST /api/analyze` com JSON no formato
`{"code": "seq { print(1); }", "phase": "tokens"}`. As fases aceitas são `tokens`,
`ast`, `semantic`, `tac` e `cpp`. A resposta contém `success`, `phase`,
`failed_phase`, `result` e `diagnostics`. Cada análise é executada em um processo
isolado, com limite de 15 segundos, sem gerar arquivos ou invocar `g++`.

Enquanto a geração C++ de `fork` e `join` não estiver implementada, a opção
**Código C++** informa essa limitação para programas que utilizam esses operadores.
Tokens, AST, Semântica e TAC continuam disponíveis para esses programas quando
as respectivas análises forem válidas.

### 2. Execução Direta (CLI)

Para compilar um arquivo específico:

```bash
python main.py tests/teste3_neuronio.minipar
```

O nome do arquivo de saída é opcional. Por padrão, será utilizado o mesmo nome do arquivo `.minipar`.

Cada compilação cria uma pasta exclusiva em `output/runs/run-.../`, contendo
os arquivos `.cpp`, `.tac` e o executável. O terminal informa essa pasta na linha
`[OUTPUT]`. Assim, execuções simultâneas do mesmo programa no terminal e na IDE
Web mantêm seus próprios arquivos. Na IDE, o código-fonte enviado também fica
na subpasta `source/` dessa execução.

O menu do terminal e a IDE executam o binário da respectiva pasta. Na CLI direta,
o comando acima compila; para executar, use o caminho do executável informado
em `[SUCESSO] Executavel:`. As pastas são mantidas para inspeção posterior.

Para ferramentas que precisam escolher a pasta explicitamente:

```bash
python main.py tests/teste3_neuronio.minipar --output-dir output/minha_execucao
```

Ao usar `--output-dir`, escolha uma pasta diferente para cada execução simultânea.

Para validar isolamento de arquivos e os limites entre sessão HTTP e terminal:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Os testes do modelo visual da AST usam o executor de testes do Node.js:

```bash
node --test tests/ast_tree_model.test.cjs
```

O teste de isolamento exige `g++` no PATH e compila simultaneamente dois pedidos
Web e uma execução CLI com o mesmo nome de arquivo e conteúdos diferentes.

---

## Fases do Compilador

| Fase | Arquivos | Descrição |
|------|----------|------------|
| 1 | `lexer.py` / `parser.py` | Tokenização do código-fonte e construção da AST |
| 2 | `semantic.py` | Verificação de declarações, redeclarações e escopo |
| 3 | `tac.py` | Geração de Código Intermediário (TAC) |
| 4 | `codegen.py` | Geração de código C++ e compilação automática via `g++ -O3` |

---

## Sintaxe MiniPar

Exemplo:

```minipar
seq {
    var x = 42;

    print("Valor:", x);

    par {
        print("Thread A");
        print("Thread B");
    }
}
```

### Comandos Disponíveis

| Sintaxe | Descrição |
|----------|------------|
| `seq { ... }` | Bloco sequencial |
| `par { ... }` | Bloco paralelo (cada instrução gera uma thread C++) |
| `var nome = expr;` | Declaração de variável |
| `nome = expr;` | Atribuição |
| `print(expr, ...);` | Impressão na saída padrão |
| `# comentário` | Comentário de linha |

---
