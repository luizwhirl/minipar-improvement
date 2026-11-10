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

Se houver uma sessão de teste ativa, aparece antes um aviso com outras opções.
Nesse aviso, **[1] Executar de forma independente** permite chegar ao menu acima;
**[2] Continuar e participar** abre o monitor da execução existente. Para abrir a
Web independentemente de um teste, escolha **1 no aviso e 2 no menu principal**.

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

**Compilar e baixar** compila o código atual e inicia o download do executável,
sem executar o programa nem solicitar entradas. O painel mantém um link para
baixar o mesmo arquivo novamente. Alterar o código ou iniciar uma nova compilação
remove o link anterior. O binário é gerado para o sistema do servidor (no Windows,
um arquivo `.exe`).
Os links ficam disponíveis enquanto esta instância do servidor está em execução;
após reiniciá-la, compile novamente para obter um novo link.

**Executar** compila o código atual, executa o binário no servidor e apresenta as
mensagens e a saída à medida que são produzidas. Para programas com `input()`,
abra **Entradas do programa** na aba Execução e preencha uma linha por leitura,
antes de executar. As linhas são enviadas na ordem informada, preservando espaços
e linhas vazias; esse campo também funciona para código escrito diretamente no
editor. As entradas são fechadas após o envio, e a execução tem limite de tempo.
Erros de compilação, término com código diferente de zero e estouro do tempo
limite são apresentados no painel. Os logs técnicos ficam em **Mensagens da
compilação**, que se abre automaticamente quando a compilação falha.

Os onze exemplos interativos abaixo recebem seus dados por `input()`. Na Web, preencha as
linhas na ordem indicada e selecione **Executar**; no Terminal, responda aos
prompts do próprio programa. O Teste 2 mantém fatorial e Fibonacci em paralelo,
agora com duas entradas: número do fatorial e quantidade de termos. Por exemplo,
as linhas `5` e `8` produzem fatorial `120` e a sequência
`0, 1, 1, 2, 3, 5, 8, 13`. Há apenas uma versão desse teste.

| Programa | Entradas, em ordem (uma por linha) |
|---|---|
| Calculadora cliente-servidor | Operação (`+`, `-`, `*`, `/`), primeiro operando, segundo operando |
| Fatorial e Fibonacci em paralelo | Número inteiro para o fatorial (0–12), quantidade de termos (0–45) |
| Neurônio | Valor de entrada (-100–100), saída desejada (0 ou 1), taxa de aprendizado (0.001–1) |
| Rede XOR | Primeiro bit, segundo bit, épocas (1–50000), taxa de aprendizado (0.001–1) |
| Recomendação | 16 valores de histórico de compras (0 ou 1), um por linha, na ordem do catálogo |
| Quicksort com classes | Vetor de números separados por espaços, em uma linha |
| Quicksort iterativo | Vetor de números separados por espaços, em uma linha |
| Paralelismo com três computadores | Vetor a ordenar; duas linhas da matriz A (2 números em cada); duas linhas da matriz B (2 números em cada); número do fatorial (0–12) |
| Tapete de Sierpinski | Tamanho: 3, 9, 27 ou 81 |
| Fractal ASCII | Quantidade inteira de linhas do desenho (1–64) |
| Controles da BNF | Nome, limite do laço (0–1000), quantidade de tentativas (1–1000) |

Os testes oficiais 8, 9 e 10, adicionados no MINIP-18, usam `fork`/`join` e
mantêm os valores de referência definidos em seus fontes, sem leitura por
`input()`. Seus resultados esperados estão em `tests/expected_results/`.

As entradas dos algoritmos são configuráveis; a tabela-verdade do XOR, o
catálogo de produtos e os valores de inicialização continuam definindo os
respectivos modelos. Alterar os dados de execução não exige editar os fontes.
Código escrito no editor também pode usar valores fixos: se houver entradas
preenchidas e nenhuma chamada real a `input()`, a interface pede a correção antes
de executar. Menções a `input()` em textos e comentários não são leituras.

As ações usam pastas de artefatos exclusivas por pedido, assim como a CLI. A
interface anterior em `/legacy` continua usando sua API e seu fluxo existentes.
As duas rotas de execução Web atualizam somente a sessão do mesmo programa,
código-fonte e terminal iniciador. Falhas encerram a sessão correspondente para
que os participantes não fiquem presos no monitor. O monitor do terminal mantém
o vínculo com a execução original mesmo que outra sessão seja iniciada.

`POST /api/build` recebe `{"code": "seq { print(1); }", "filename": "exemplo.minipar"}`
e retorna o resultado da compilação, TAC, C++ e `download_url` em caso de sucesso.
O link dá acesso apenas ao executável daquela compilação.

`POST /api/execute` recebe os mesmos campos e `inputs` (lista de textos). A resposta
é um fluxo `application/x-ndjson`: eventos `phase`, `output` (com `stream` e `text`),
eventuais `error` e um evento final `complete` com `success`, `exit_code`, TAC e C++.
Os limites padrão são 15 segundos para compilar, 30 segundos para executar e
2 MiB de saída por processo. Tempo limite ou encerramento da conexão durante a
execução interrompem os processos envolvidos.

A API de fases usa `POST /api/analyze` com JSON no formato
`{"code": "seq { print(1); }", "phase": "tokens"}`. As fases aceitas são `tokens`,
`ast`, `semantic`, `tac` e `cpp`. A resposta contém `success`, `phase`,
`failed_phase`, `result` e `diagnostics`. Cada análise é executada em um processo
isolado, com limite de 15 segundos, sem gerar arquivos ou invocar `g++`.

O gerador C++ traduz `fork`/`join` para tarefas assíncronas e permite consultar
o código gerado, compilar e executar esses programas pela Web e pelo terminal.
O `join` atual retorna resultados numéricos; tarefas sem retorno produzem zero.

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
node --test tests/execution_stream.test.cjs
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
