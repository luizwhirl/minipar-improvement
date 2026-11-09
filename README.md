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

Após iniciar o servidor, as duas interfaces Web ficam disponíveis:

- **Interface didática (2026.2):** http://127.0.0.1:5000/
- **Interface anterior (2026.1):** http://127.0.0.1:5000/legacy

A interface anterior mantém o editor, as abas C++/TAC e a ação **Compile & Run**.
O modo Terminal continua disponível pelo menu, independentemente da interface Web.

A IDE permite:

- Editar código MiniPar
- Compilar o programa
- Visualizar o código TAC gerado
- Visualizar o código C++ gerado
- Executar o programa e ver a saída

Na interface didática, a barra de fases do MINIP-11 prepara os painéis de
**Tokens**, **AST** e **Semântica**; a integração dessas fases com a API ainda está
pendente. As opções **TAC** e **Código C++** exibem os artefatos retornados pela
última execução. **Compilar/Baixar** permanece indisponível enquanto não houver
suporte ao download do executável. **Executar** mantém a operação atual: compila
o programa, executa o binário no servidor e apresenta a saída.

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
