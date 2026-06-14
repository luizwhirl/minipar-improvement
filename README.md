# Compilador MiniPar

arquitetura orientada a objetos da versão C++ original e gerando o mesmo
código C++ de saída.

## Estrutura do projeto

```bash
minipar_python/
├── src/
│   ├── ast_nodes.py   # Nós da AST (dataclasses)
│   ├── lexer.py       # Analisador Léxico
│   ├── parser.py      # Analisador Sintático
│   ├── semantic.py    # Analisador Semântico
│   ├── codegen.py     # Gerador de Código C++
│   └── cpp_template.py# Template base em C++
├── examples/          # Pasta para exemplos de código
│   └── teste.minipar  # Exemplo de programa MiniPar
├── output/            # Arquivos .cpp e .exe gerados
├── main.py            # Ponto de entrada principal
└── README.md
```

## Requisitos

- Python 3.8 ou superior (sem dependências externas)
- `g++` disponível no PATH (para compilar o C++ gerado)

## Como usar

```bash
# A partir da raiz do projeto
python main.py tests/teste.minipar teste_math_print

# Executar o binário gerado (Windows)
.\output\teste_math_print.exe

# Executar o binário gerado (Linux/macOS)
./output/teste_math_print
```

## Fases do compilador

| Fase | Arquivo         | Descrição                                          |
|------|-----------------|----------------------------------------------------|
| 1    | `lexer.py`      | Tokenização do código-fonte MiniPar                |
| 1    | `parser.py`     | Construção da AST a partir dos tokens              |
| 2    | `semantic.py`   | Verificação de variáveis declaradas / redeclaradas |
| 3    | `codegen.py`    | Transpilação para C++ e chamada do `g++ -O3`       |

## Sintaxe MiniPar (teste)

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

- `seq { ... }` — bloco sequencial
- `par { ... }` — bloco paralelo (cada instrução vira uma thread)
- `var nome = expr;` — declaração de variável
- `nome = expr;` — atribuição
- `print(expr, ...);` — impressão na saída padrão
- `#` inicia um comentário de linha
