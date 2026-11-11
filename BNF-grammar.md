# Gramática Formal BNF — Linguagem MiniPar 2026.2

**Projeto:** MiniPar-Improvement — Compilador da Linguagem MiniPar 2026.2 Orientada a Objetos  
**Autores:** Laura Mainero - Yuri Barbosa - Júlia Azevedo - João Felipe Brandão Jatobá 
**Instituição:** Universidade Federal de Alagoas — Instituto de Computação · Ciência da Computação  
**Disciplina:** Compiladores — Prof. Arturo Hernandez Dominguez  
**Repositório:** https://github.com/maineros/minipar-improvement-2026.2

---

> Esta gramática foi derivada diretamente da implementação real do compilador
> (arquivos `src/lexer.py`, `src/parser.py` e `src/ast_nodes.py`), cruzada com
> o relatório técnico do projeto e as especificações formais fornecidas pelo professor.
> Ela descreve **toda** a sintaxe aceita pelo compilador MiniPar 2026.2.

---

## Sumário

1. [Notação utilizada](#1-notação-utilizada)
2. [Tokens (Análise Léxica)](#2-tokens-análise-léxica)
3. [Programa](#3-programa)
4. [Declarações](#4-declarações)
5. [Comandos](#5-comandos)
6. [Blocos e Paralelismo (Seq, Par, Fork e Join)](#6-blocos-e-paralelismo-seq-par-fork-e-join)
7. [Estruturas de Controle](#7-estruturas-de-controle)
8. [Orientação a Objetos](#8-orientação-a-objetos)
9. [Funções](#9-funções)
10. [Expressões](#10-expressões)
11. [Comunicação por Canais](#11-comunicação-por-canais)
12. [Coleções](#12-coleções)
13. [Entrada e Saída](#13-entrada-e-saída)
14. [Tipos e Literais](#14-tipos-e-literais)
15. [Biblioteca Nativa](#15-biblioteca-nativa)
16. [Comentários](#16-comentários)
17. [Gramática Consolidada (BNF Completa)](#17-gramática-consolidada-bnf-completa)

---

## 1. Notação utilizada

| Símbolo | Significado |
|---------|-------------|
| `::=` | Definição de produção |
| `\|` | Alternativa (ou) |
| `{ x }` | Zero ou mais repetições de `x` |
| `[ x ]` | Opcional (zero ou uma ocorrência de `x`) |
| `( x )` | Agrupamento |
| `"token"` | Terminal literal (palavra reservada ou símbolo) |
| `<não-terminal>` | Símbolo não-terminal |

---

## 2. Tokens (Análise Léxica)

O analisador léxico (`src/lexer.py`) produz os seguintes tokens a partir do código-fonte.  
Comentários iniciados por `#` são descartados pelo lexer antes da geração de tokens.

### 2.1 Palavras Reservadas

```
class  extends  new  func  var
if  else  while  do  for  in
break  continue  return
seq  par  fork  join  this
c_channel  send  receive  input  print  matrix
true  false
number  int  string  bool  void  list  dict
```

### 2.2 Literais

```bnf
<NUMBER>         ::= <digito> { <digito> } [ "." { <digito> } ]
<STRING_LITERAL> ::= '"' { <caractere> } '"'
<BOOL_LITERAL>   ::= "true" | "false"
<IDENTIFIER>     ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }
```

### 2.3 Operadores

| Categoria | Tokens |
|-----------|--------|
| Aritméticos | `+`  `-`  `*`  `/`  `%` |
| Relacionais | `==`  `!=`  `<`  `>`  `<=`  `>=` |
| Lógicos | `&&`  `\|\|`  `!` |
| Atribuição | `=` |

### 2.4 Delimitadores

```
(  )  {  }  [  ]  .  ;  ,
```

### 2.5 Tipos declaráveis

```bnf
<tipo> ::= "number" | "int" | "string" | "bool" | "void" | "list" | "dict"
```

---

## 3. Programa

O programa MiniPar é uma sequência de zero ou mais comandos. Declarações de classe (`class`) e função (`func`) são comandos como os demais: o parser as aceita em qualquer posição onde um comando é aceito, inclusive dentro de blocos. Porém, o gerador de C++ só emite as declaradas no nível global; as aninhadas passam pela análise sintática e semântica, mas são ignoradas na geração de código.

```bnf
<programa> ::= { <comando> }
```

---

## 4. Declarações

### 4.1 Declaração de Variável

```bnf
<declaracao_variavel> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <tipo> <IDENTIFIER> [ "=" <expressao> ] ";"
```

**Exemplos:**

```minipar
var x = 42;
var nome = "MiniPar";
number total = 0;
bool ativo = true;
```

### 4.2 Declaração de Função

```bnf
<declaracao_funcao> ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_seq>

<lista_parametros> ::= <parametro> { "," <parametro> }

<parametro> ::= [ <tipo> ] <IDENTIFIER>
```

**Exemplos:**

```minipar
func somar(a, b) {
    return a + b;
}

func calcular(number x, number y) {
    return x * y;
}
```

### 4.3 Declaração de Classe

```bnf
<declaracao_classe> ::= "class" <IDENTIFIER> [ "extends" <IDENTIFIER> ] "{"
                            { <membro_classe> }
                        "}"

<membro_classe>   ::= <atributo_classe> | <metodo_classe>

<atributo_classe> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"

<metodo_classe>   ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_seq>
```

Atributos de classe só podem ser declarados com `var` (`number x;` dentro de uma classe é erro de sintaxe). Os tipos dos parâmetros de método são aceitos, mas ignorados.

**Exemplos:**

```minipar
class Animal {
    var nome = "Animal";
    func falar() {
        print("...");
    }
}

class Cachorro extends Animal {
    func falar() {
        print("Au!");
    }
}
```

---

## 5. Comandos

```bnf
<comando> ::= <declaracao_variavel>
            | <declaracao_classe>
            | <declaracao_funcao>
            | <atribuicao>
            | <bloco_seq>
            | <bloco_par>
            | <comando_if>
            | <comando_while>
            | <comando_do_while>
            | <comando_for>
            | <comando_print>
            | <comando_send>
            | <comando_fork>
            | <comando_join>
            | <comando_return>
            | <comando_break>
            | <comando_continue>
            | <chamada_funcao> ";"
            | <chamada_metodo> ";"
```

### 5.1 Atribuição

A atribuição suporta identificadores simples, propriedades de objetos e indexação de coleções:

```bnf
<atribuicao> ::= <alvo_atribuicao> "=" <expressao> ";"

<alvo_atribuicao> ::= <IDENTIFIER>
                    | <expressao_posfixo> "." <IDENTIFIER>
                    | <expressao_posfixo> "[" <expressao> "]"
```

**Exemplos:**

```minipar
x = 10;
objeto.campo = 42;
lista[0] = "primeiro";
```

### 5.2 Comando Print

```bnf
<comando_print> ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
```

**Exemplos:**

```minipar
print("Olá, mundo!");
print("Valor:", x, "e", y);
```

### 5.3 Comando Return

```bnf
<comando_return> ::= "return" ( <expressao> [ ";" ] | ";" )
```

### 5.4 Comandos Break e Continue

```bnf
<comando_break>    ::= "break" [ ";" ]
<comando_continue> ::= "continue" [ ";" ]
```

> `break` e `continue` são válidos somente dentro de laços (`while`, `do-while`, `for`).  
> O analisador semântico reporta erro se forem usados fora de laço.  
> O `;` final de `break`, `continue` e `return expressao` é opcional para o parser; `return` sem valor precisa do `;`.

---

## 6. Blocos e Paralelismo (Seq, Par, Fork e Join)

### 6.1 Bloco Sequencial (SEQ)

Executa os comandos internos em ordem, da mesma forma que um bloco tradicional.

```bnf
<bloco_seq> ::= "seq" "{" { <comando> } "}"
              | "{" { <comando> } "}"
```

O `seq` é opcional: blocos com chaves `{ }` são tratados como sequenciais por padrão.

### 6.2 Bloco Paralelo (PAR)

Cada comando interno é executado como uma `std::thread` independente em C++.  
As threads são sincronizadas por um join implícito ao final do bloco.

```bnf
<bloco_par> ::= "par" "{" { <comando> } "}"
```

**Exemplo:**

```minipar
par {
    seq { print("Thread A"); }
    seq { print("Thread B"); }
    seq { print("Thread C"); }
}
```

### 6.3 Criação Dinâmica de Subtarefas (Fork e Join)

Para dividir tarefas de forma recursiva ou dinâmica, a linguagem disponibiliza `fork` e `join`. O `fork` dispara uma chamada de função (ou método) em uma nova thread e retorna um manipulador (handle). O `join` recebe esse manipulador para aguardar o término e coletar o resultado.

```bnf
<expressao_fork> ::= "fork" <expressao>
<comando_fork>   ::= <expressao_fork> ";"
<comando_join>   ::= "join" "(" <expressao> ")" ";"
<expressao_join> ::= "join" "(" <expressao> ")"
```

Sintaticamente, o operando de `fork` é uma expressão qualquer; é o analisador semântico que exige que ela seja uma chamada de função ou de método. Por isso `fork f(x) + 1` é rejeitado na análise semântica, não na sintática. `fork` também pode aparecer como comando isolado (`fork f(x);`), descartando o resultado.

Em C++, cada `fork` vira uma tarefa `std::async` guardada em uma lista global; o handle é o número da tarefa (um `double`), que pode ser guardado em variáveis e listas. `join` em uma tarefa inexistente encerra o programa com `[ERRO EXECUCAO]`.

**Exemplos:**

```minipar
# Disparando tarefas recursivas/independentes
var t1 = fork calcular_parte(0, 50);
var t2 = fork calcular_parte(51, 100);

# O programa continua sua execução aqui

# Aguardando e coletando resultados
var res1 = join(t1);
var res2 = join(t2);
var total = res1 + res2;
```

---

## 7. Estruturas de Controle

### 7.1 If / Else

```bnf
<comando_if> ::= "if" "(" <expressao> ")" <comando>
                 [ "else" <comando> ]
```

**Exemplos:**

```minipar
if (x > 0) {
    print("positivo");
}

if (x > 0) {
    print("positivo");
} else {
    print("negativo ou zero");
}

# Encadeamento if-else-if
if (x > 0) {
    print("positivo");
} else if (x < 0) {
    print("negativo");
} else {
    print("zero");
}
```

### 7.2 While

```bnf
<comando_while> ::= "while" "(" <expressao> ")" <comando>
```

**Exemplo:**

```minipar
while (i < 10) {
    i = i + 1;
}
```

### 7.3 Do-While

```bnf
<comando_do_while> ::= "do" <comando> "while" "(" <expressao> ")" [ ";" ]
```

**Exemplo:**

```minipar
do {
    tentativas = tentativas + 1;
} while (tentativas < 5);
```

### 7.4 For

O `for` suporta tanto o estilo clássico (inicializador; condição; incremento) quanto o estilo iterador (`for var x in colecao`):

```bnf
<comando_for> ::= "for" "(" <for_cabecalho> ")" <comando>

<for_cabecalho> ::= <for_classico>
                 | <for_iterador>

<for_classico> ::= [ <inicializador_for> ] ";" [ <expressao> ] ";" [ <incremento_for> ]

<inicializador_for> ::= "var" <IDENTIFIER> [ "=" <expressao> ]
                      | <tipo> <IDENTIFIER> [ "=" <expressao> ]
                      | <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<incremento_for>    ::= <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<for_iterador>      ::= "var" <IDENTIFIER> "in" <expressao>
```

**Exemplos:**

```minipar
# For clássico
for (var i = 0; i < 10; i = i + 1) {
    print(i);
}

# For iterador
for (var item in lista) {
    print(item);
}

# For com range()
for (var i in range(5)) {
    print(i);
}
```

---

## 8. Orientação a Objetos

### 8.1 Instanciação com new

```bnf
<expressao_new> ::= "new" <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
```

**Exemplo:**

```minipar
var obj = new MinhaClasse();
var rede = new RedeNeural(0.5);
```

### 8.2 Acesso a Propriedades

```bnf
<acesso_propriedade> ::= <expressao_posfixo> "." <IDENTIFIER>
```

**Exemplo:**

```minipar
print(neuronio.peso);
```

### 8.3 Chamada de Método

```bnf
<chamada_metodo> ::= <expressao_posfixo> "." <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
```

**Exemplo:**

```minipar
neuronio.treinar();
algoritmo.ordenar();
rede.feedforward(x1, x2);
```

### 8.4 Atribuição de Propriedade

```bnf
<atrib_propriedade> ::= <expressao_posfixo> "." <IDENTIFIER> "=" <expressao> ";"
```

**Exemplo:**

```minipar
this.peso = this.peso + 0.01;
obj.nome = "novo";
```

### 8.5 Referência a this

Dentro de métodos de uma classe, `this` refere-se à instância corrente.

```bnf
<expressao_this> ::= "this"
```

### 8.6 Herança

```bnf
<declaracao_classe> ::= "class" <IDENTIFIER> "extends" <IDENTIFIER> "{"
                            { <membro_classe> }
                        "}"
```

**Exemplo:**

```minipar
class Cachorro extends Animal {
    func latir() {
        print("Au!");
    }
}
```

---

## 9. Funções

### 9.1 Chamada de Função

```bnf
<chamada_funcao> ::= <IDENTIFIER> "(" [ <lista_argumentos> ] ")"

<lista_argumentos> ::= <expressao> { "," <expressao> }
```

### 9.2 Recursão

Funções podem se chamar recursivamente sem nenhuma sintaxe especial:

```minipar
func fatorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * fatorial(n - 1);
}
```

---

## 10. Expressões

As expressões seguem a hierarquia de precedência implementada no parser (da menor para a maior precedência):

```bnf
<expressao> ::= <expressao_ou>

<expressao_ou>  ::= <expressao_e> { "||" <expressao_e> }

<expressao_e>   ::= <expressao_comp> { "&&" <expressao_comp> }

<expressao_comp> ::= <expressao_termo>
                     { ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) <expressao_termo> }

<expressao_termo> ::= <expressao_fator> { ( "+" | "-" ) <expressao_fator> }

<expressao_fator> ::= <expressao_unaria> { ( "*" | "/" | "%" ) <expressao_unaria> }

<expressao_unaria> ::= ( "-" | "+" | "!" ) <expressao_unaria>
                     | <expressao_posfixo>

<expressao_posfixo> ::= <expressao_primaria>
                        { "." <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                        | "[" <expressao> "]"
                        }

<expressao_primaria> ::= <NUMBER>
                       | <STRING_LITERAL>
                       | <BOOL_LITERAL>
                       | <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                       | "this"
                       | <expressao_new>
                       | <expressao_fork>
                       | <expressao_join>
                       | <expressao_c_channel>
                       | <expressao_receive>
                       | <expressao_input>
                       | <expressao_lista>
                       | <expressao_matrix>
                       | "(" <expressao> ")"
```

### Tabela de Precedência (maior nível = avaliado primeiro)

| Nível | Operadores | Associatividade |
|-------|-----------|-----------------|
| 7 (mais alta) | `()` `[]` `.` (posfixo) | esquerda |
| 6 | `!` `-` (unário) `+` (unário) | direita |
| 5 | `*` `/` `%` | esquerda |
| 4 | `+` `-` | esquerda |
| 3 | `==` `!=` `<` `>` `<=` `>=` | esquerda |
| 2 | `&&` | esquerda |
| 1 (mais baixa) | `\|\|` | esquerda |

---

## 11. Comunicação por Canais

A comunicação entre processos/computadores é feita via canais TCP implementados pela classe `MiniParChannel` no C++ gerado.

### 11.1 Criação de Canal

```bnf
<expressao_c_channel> ::= "c_channel" "(" <expressao> "," <expressao> ")"
```

O primeiro argumento é o endereço IP (string) e o segundo é a porta (número).

**Exemplo:**

```minipar
var canal = c_channel("127.0.0.1", 5000);
var canal_remoto = c_channel("192.168.1.10", 8080);
```

### 11.2 Envio de Mensagem (Send)

```bnf
<comando_send> ::= "send" "(" <expressao> "," <expressao> ")" ";"
```

O primeiro argumento é o canal e o segundo é a mensagem a enviar.

**Exemplo:**

```minipar
send(canal, "Hello Server");
send(canal, resultado);
```

### 11.3 Recebimento de Mensagem (Receive)

```bnf
<expressao_receive> ::= "receive" "(" <expressao> ")"
```

**Exemplo:**

```minipar
var mensagem = receive(canal);
var dado = receive(c_channel("127.0.0.1", 5000));
```

---

## 12. Coleções

### 12.1 Lista (Array)

```bnf
<expressao_lista> ::= "[" [ <expressao> { "," <expressao> } ] "]"
```

**Exemplos:**

```minipar
var vazio = [];
var numeros = [1, 2, 3, 4, 5];
var misto = [0, "texto", true];
```

### 12.2 Indexação

```bnf
<expressao_indice> ::= <expressao_posfixo> "[" <expressao> "]"
```

**Exemplo:**

```minipar
var primeiro = lista[0];
var ultimo = lista[len(lista) - 1];
```

A indexação também vale para texto (2026.2). Em texto, `s[i]` devolve o caractere da posição `i` como um texto de 1 letra (começa em 0). Texto só pode ser **lido** por índice: `s[i] = "x"` é erro semântico (use `substr` e `+` para montar outro texto).

```minipar
var palavra = "minipar";
var letra = palavra[0];          # "m"
if (palavra[1] == "i") { print("ok"); }
```

### 12.3 Atribuição por Índice

```bnf
<atrib_indice> ::= <expressao_posfixo> "[" <expressao> "]" "=" <expressao> ";"
```

**Exemplo:**

```minipar
lista[0] = 99;
matriz[i][j] = "#";
```

### 12.4 Matriz (Matrix)

Cria uma matriz bidimensional de `linhas × colunas` inicializada com um valor padrão.

```bnf
<expressao_matrix> ::= "matrix" "(" <expressao> "," <expressao> "," <expressao> ")"
```

**Exemplo:**

```minipar
var tela = matrix(9, 9, " ");       # matriz 9×9 de espaços
var zeros = matrix(3, 3, 0);        # matriz 3×3 de zeros
```

---

## 13. Entrada e Saída

### 13.1 Saída (Print)

```bnf
<comando_print> ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
```

Múltiplos argumentos são impressos separados por espaço seguidos de `\n`.

### 13.2 Entrada (Input)

```bnf
<expressao_input> ::= "input" "(" [ <expressao> ] ")"
```

Lê uma linha da entrada padrão (stdin). O argumento opcional é exibido como prompt antes da leitura.

**Exemplos:**

```minipar
var nome = input("Seu nome: ");
var valor = input();
var numero = to_number(input("Digite um número: "));
```

---

## 14. Tipos e Literais

### 14.1 Número

```bnf
<literal_numero> ::= <digito> { <digito> } [ "." { <digito> } ]
```

Representa inteiros e ponto flutuante. Internamente ambos são tratados como `double` no C++ gerado.

**Exemplos:** `0`, `42`, `3.14`, `0.5`

### 14.2 String

```bnf
<literal_string> ::= '"' { <caractere_string> } '"'

<caractere_string> ::= <qualquer_caractere_exceto_aspas_e_barra>
                     | "\\" "n"    # newline
                     | "\\" "t"    # tab
                     | "\\" '"'    # aspas duplas
                     | "\\" "\\"   # barra invertida
                     | "\\" <outro_caractere>   # escape desconhecido: vale só o caractere (ex.: "\q" vira "q")
```

### 14.3 Booleano

```bnf
<literal_bool> ::= "true" | "false"
```

### 14.4 Identificador

```bnf
<IDENTIFIER> ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }

<letra>  ::= "A" | ... | "Z" | "a" | ... | "z"
<digito> ::= "0" | ... | "9"
```

---

## 15. Biblioteca Nativa

As seguintes funções são reconhecidas pelo analisador semântico e traduzidas diretamente pelo gerador de código C++:

| Função MiniPar | Assinatura | Descrição |
|---------------|------------|-----------|
| `print(...)` | `print(expr, ...)` | Imprime na saída padrão |
| `input([prompt])` | `input()` / `input(expr)` | Lê linha do stdin |
| `exp(x)` | `exp(number)` → `number` | Exponencial natural (eˣ) |
| `random()` | `random()` → `number` | Número aleatório entre 0 e 1 |
| `range(n)` / `range(a,b)` | `range(int)` → `list` | Gera sequência inteira |
| `len(col)` | `len(list\|string)` → `number` | Comprimento de coleção |
| `to_number(s)` | `to_number(string)` → `number` | Converte string para número |
| `parse_ints(s)` | `parse_ints(string)` → `list` | Parseia inteiros de string separados por espaço |
| `to_string(x)` | `to_string(number\|string)` → `string` | Converte para texto, no mesmo formato do `print` (`42`, `3.5`) |
| `substr(s, i, n)` | `substr(string, number, number)` → `string` | Pedaço de `s` que começa em `i` e tem até `n` caracteres |

### Funções de Texto (2026.2)

```minipar
var s = "ab";
s = s + "*";                        # concatenação: "ab*"
var t = "n=" + to_string(42);       # "n=42"
var pedaco = substr("compilador", 0, 4);  # "comp"
var c = s[1];                       # "b"
```

- `substr(s, i, n)`: se `i + n` passar do fim, devolve até o fim. Se `i` estiver fora do texto, o programa para com `[ERRO EXECUCAO]`.
- `s[i]` com `i` fora do texto também para com `[ERRO EXECUCAO]`.
- Para juntar texto com número, use `to_string`: `"n=" + to_string(5)`.

### Métodos de Lista (acesso via ponto)

| Método | Descrição |
|--------|-----------|
| `.append(v)` / `.push_back(v)` | Adiciona elemento ao final |
| `.pop()` | Remove e retorna o último elemento |
| `.size()` / `.size` | Retorna o tamanho da lista (os parênteses são opcionais) |

---

## 16. Comentários

```bnf
<comentario> ::= "#" { <qualquer_caractere> } <fim_de_linha>
```

Comentários iniciam com `#` e vão até o final da linha. São descartados pelo lexer.

**Exemplos:**

```minipar
# Isso é um comentário de linha inteira
var x = 10; # Comentário ao final da linha
```

---

## 17. Gramática Consolidada (BNF Completa)

A seguir a gramática completa em formato BNF, em ordem de definição:

```bnf
(* ============================================================ *)
(*       GRAMÁTICA BNF — LINGUAGEM MINIPAR 2026.2               *)
(*       Compilador: minipar-improvement                        *)
(*       Repositório: github.com/maineros/minipar-improvement-2026.2 *)
(* ============================================================ *)


(* ─── ESTRUTURA GLOBAL ─── *)

<programa> ::= { <comando> }


(* ─── DECLARAÇÕES ─── *)

<declaracao_variavel> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <tipo> <IDENTIFIER> [ "=" <expressao> ] ";"

<declaracao_funcao>   ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_seq>

<lista_parametros>    ::= <parametro> { "," <parametro> }
<parametro>           ::= [ <tipo> ] <IDENTIFIER>

<declaracao_classe>   ::= "class" <IDENTIFIER> [ "extends" <IDENTIFIER> ]
                          "{" { <membro_classe> } "}"

<membro_classe>       ::= <atributo_classe> | <metodo_classe>
<atributo_classe>     ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
<metodo_classe>       ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_seq>


(* ─── COMANDOS ─── *)

<comando> ::= <declaracao_variavel>
            | <declaracao_classe>
            | <declaracao_funcao>
            | <atribuicao>
            | <bloco_seq>
            | <bloco_par>
            | <comando_if>
            | <comando_while>
            | <comando_do_while>
            | <comando_for>
            | <comando_print>
            | <comando_send>
            | <comando_fork>
            | <comando_join>
            | <comando_return>
            | <comando_break>
            | <comando_continue>
            | <chamada_funcao> ";"
            | <chamada_metodo> ";"

<atribuicao>        ::= <alvo_atribuicao> "=" <expressao> ";"
<alvo_atribuicao>   ::= <IDENTIFIER>
                      | <expressao_posfixo> "." <IDENTIFIER>
                      | <expressao_posfixo> "[" <expressao> "]"

<comando_print>     ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
<comando_send>      ::= "send"  "(" <expressao> "," <expressao> ")" ";"
<comando_return>    ::= "return" ( <expressao> [ ";" ] | ";" )
<comando_break>     ::= "break" [ ";" ]
<comando_continue>  ::= "continue" [ ";" ]
<comando_join>      ::= "join" "(" <expressao> ")" ";"


(* ─── BLOCOS E PARALELISMO ─── *)

<bloco_seq> ::= "seq" "{" { <comando> } "}"
              | "{" { <comando> } "}"

<bloco_par> ::= "par" "{" { <comando> } "}"

<expressao_fork> ::= "fork" <expressao>
(* o analisador semântico exige que a expressão seja chamada de função ou método *)
<comando_fork>   ::= <expressao_fork> ";"
<expressao_join> ::= "join" "(" <expressao> ")"


(* ─── ESTRUTURAS DE CONTROLE ─── *)

<comando_if>       ::= "if" "(" <expressao> ")" <comando> [ "else" <comando> ]

<comando_while>    ::= "while" "(" <expressao> ")" <comando>

<comando_do_while> ::= "do" <comando> "while" "(" <expressao> ")" [ ";" ]

<comando_for>      ::= "for" "(" <for_cabecalho> ")" <comando>

<for_cabecalho>    ::= <for_classico>
                     | <for_iterador>

<for_classico>     ::= [ <inicializador_for> ] ";" [ <expressao> ] ";" [ <incremento_for> ]

<inicializador_for> ::= "var"  <IDENTIFIER> [ "=" <expressao> ]
                      | <tipo> <IDENTIFIER> [ "=" <expressao> ]
                      | <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<incremento_for>   ::= <alvo_atribuicao> "=" <expressao>
                     | <expressao>

<for_iterador>     ::= "var" <IDENTIFIER> "in" <expressao>


(* ─── ORIENTAÇÃO A OBJETOS ─── *)

<expressao_new>         ::= "new" <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
<acesso_propriedade>    ::= <expressao_posfixo> "." <IDENTIFIER>
<chamada_metodo>        ::= <expressao_posfixo> "." <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
<atrib_propriedade>     ::= <expressao_posfixo> "." <IDENTIFIER> "=" <expressao> ";"
<expressao_this>        ::= "this"


(* ─── COMUNICAÇÃO POR CANAIS ─── *)

<expressao_c_channel>   ::= "c_channel" "(" <expressao> "," <expressao> ")"
<expressao_receive>     ::= "receive" "(" <expressao> ")"
(* send já listado em <comando_send> *)


(* ─── COLEÇÕES ─── *)

<expressao_lista>   ::= "[" [ <expressao> { "," <expressao> } ] "]"
<expressao_indice>  ::= <expressao_posfixo> "[" <expressao> "]"
<atrib_indice>      ::= <expressao_posfixo> "[" <expressao> "]" "=" <expressao> ";"
<expressao_matrix>  ::= "matrix" "(" <expressao> "," <expressao> "," <expressao> ")"


(* ─── ENTRADA E SAÍDA ─── *)

<expressao_input>   ::= "input" "(" [ <expressao> ] ")"
(* print já listado em <comando_print> *)


(* ─── EXPRESSÕES (hierarquia de precedência) ─── *)

<expressao>          ::= <expressao_ou>

<expressao_ou>       ::= <expressao_e> { "||" <expressao_e> }

<expressao_e>        ::= <expressao_comp> { "&&" <expressao_comp> }

<expressao_comp>     ::= <expressao_termo>
                         { ( "==" | "!=" | "<" | ">" | "<=" | ">=" )
                           <expressao_termo> }

<expressao_termo>    ::= <expressao_fator> { ( "+" | "-" ) <expressao_fator> }

<expressao_fator>    ::= <expressao_unaria> { ( "*" | "/" | "%" ) <expressao_unaria> }

<expressao_unaria>   ::= ( "-" | "+" | "!" ) <expressao_unaria>
                       | <expressao_posfixo>

<expressao_posfixo>  ::= <expressao_primaria>
                         { "." <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                         | "[" <expressao> "]"
                         }

<expressao_primaria> ::= <NUMBER>
                       | <STRING_LITERAL>
                       | <BOOL_LITERAL>
                       | <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                       | "this"
                       | <expressao_new>
                       | <expressao_fork>
                       | <expressao_join>
                       | <expressao_c_channel>
                       | <expressao_receive>
                       | <expressao_input>
                       | <expressao_lista>
                       | <expressao_matrix>
                       | "(" <expressao> ")"

<lista_argumentos>   ::= <expressao> { "," <expressao> }
<chamada_funcao>     ::= <IDENTIFIER> "(" [ <lista_argumentos> ] ")"


(* ─── TIPOS E LITERAIS ─── *)

<tipo>           ::= "number" | "int" | "string" | "bool" | "void" | "list" | "dict"

<NUMBER>         ::= <digito> { <digito> } [ "." { <digito> } ]
<STRING_LITERAL> ::= '"' { <caractere_string> } '"'
<BOOL_LITERAL>   ::= "true" | "false"
<IDENTIFIER>     ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }

<caractere_string> ::= <qualquer_char_exceto_aspas_e_barra>
                     | "\n" | "\t" | '\"' | "\\"

(* Escape desconhecido: "\" seguido de outro caractere produz apenas esse caractere *)

<letra>  ::= "A" | ... | "Z" | "a" | ... | "z"
<digito> ::= "0" | ... | "9"


(* ─── COMENTÁRIOS ─── *)

<comentario> ::= "#" { <qualquer_char> } <nova_linha>
(* Descartados pelo lexer — não aparecem na AST *)
```
---

## Notas de Implementação (2026.2)

### Inferência de Tipos

O analisador semântico (`src/semantic.py`) usa inferência simples de tipos com as seguintes regras:

| Expressão | Tipo inferido |
|-----------|--------------|
| Literal numérico | `number` |
| Literal string | `string` |
| Literal booleano | `bool` |
| Lista literal `[...]` | `list` |
| `matrix(...)` | `matrix` |
| `c_channel(...)` | `c_channel` |
| `receive(...)` | `string` |
| `input(...)` | `string` |
| `new Classe(...)` | `Classe` |
| `this` | nome da classe atual |
| `op` relacional / lógico, `!x` | `bool` |
| `"a" + "b"` (concatenação) | `string` |
| `to_string(x)`, `substr(s, i, n)` | `string` |
| `s[i]` com `s` do tipo `string` | `string` |
| `len(x)`, `to_number(s)`, `exp(x)`, `random()` | `number` |
| `range(...)`, `parse_ints(s)` | `list` |
| `lista + x` (concatenação) | `list` |
| `fork f(...)` | `task` |
| `join(t)` | `unknown` |
| `obj.metodo(...)` | `unknown` |
| `obj.campo` | tipo declarado do atributo (classe conhecida) ou `unknown` |
| Operação aritmética | `number` |
| Identificador | tipo declarado na tabela de símbolos |
| Desconhecido | `unknown` (compatível com qualquer tipo) |

### Regras Semânticas Verificadas

Os erros saem em `stderr` no formato `[ERRO SEMANTICO] Linha N (Funcao: f): mensagem` (o trecho da função só aparece dentro de função). As mensagens do código não têm acentos.

| Regra | Erro reportado |
|-------|---------------|
| Redeclaração no mesmo escopo | `Variavel 'x' ja declarada.` |
| Uso antes de declaração | `Variavel 'x' nao declarada.` |
| Tipo incompatível em declaração | `Tipo incompativel em 'x': esperado T, recebido U.` |
| Tipo incompatível em atribuição | `Tipo incompativel em atribuicao de 'x'.` |
| `- * / %` com operando não numérico | `Operador 'op' exige operandos numericos.` |
| Função não declarada | `Funcao 'f' nao declarada.` |
| Aridade errada (função) | `Funcao 'f' espera N argumento(s), recebeu M.` |
| Aridade errada (`to_string` 1, `substr` 3) | `Funcao 'substr' espera 3 argumento(s), recebeu M.` |
| Classe não declarada | `Classe 'C' nao declarada.` |
| Superclasse não declarada | `Superclasse 'S' nao declarada.` |
| Método inexistente | `Metodo 'm' nao declarado em 'C'.` |
| Aridade errada (método) | `Metodo 'm' espera N argumento(s), recebeu M.` |
| Atributo inexistente | `Atributo 'a' nao declarado em 'C'.` |
| `break`/`continue` fora de laço | `'break' usado fora de laco.` |
| Alterar caractere de texto (`s[i] = ...`) | `Nao da para alterar um caractere de texto com s[i] = ...; use substr e +.` |
| `fork` sem chamada | `A expressao 'fork' exige uma chamada de funcao ou metodo.` |
| `join` com argumento que não é tarefa | `A expressao 'join' exige um identificador de tarefa, recebido: 'T'.` |

### Geração de Código C++20

| Construto MiniPar | Código C++ gerado |
|-------------------|------------------|
| `class C extends S { ... }` | `class C : public S { public: ... };` (atributo com valor: `decltype(e) x = e;`; sem valor: `double x = 0;`) |
| `new C(args)` | `std::make_shared<C>(args)` |
| `obj.metodo(args)` | `obj->metodo(args)` |
| `obj.campo` | `obj->campo` |
| `par { a; b; }` | `std::vector<std::thread>` + `emplace_back` + `join` |
| `c_channel(ip, porta)` | `std::make_shared<MiniParChannel>(ip, porta)` |
| `send(canal, msg)` | `canal->sendData(__to_string(msg))` |
| `receive(canal)` | `canal->receiveData()` |
| `[1, 2, 3]` | `std::vector<double>{1, 2, 3}` |
| `matrix(l, c, v)` | `__make_matrix(l, c, v)` |
| `exp(x)` | `std::exp(x)` |
| `random()` | `random_val()` |
| `"texto"` | `std::string("texto")` |
| `to_number(s)` | `std::stod(s)` |
| `len(x)` | `static_cast<double>(x.size())` |
| `to_string(x)` | `__minipar_to_string(x)` |
| `substr(s, i, n)` | `__substr(s, i, n)` |
| `x[i]` (lista, matriz ou texto) | `__index(x, i)` |
| `range(n)` | `__minipar_range(n)` |
| `input(p)` | `input(p)` (helper C++) |
| `var x = e;` / `tipo x = e;` | `auto x = e;` (sem valor: `auto x = 0;`) |
| `fork f(args)` | `__fork([=]() mutable { return f(args); })`: roda em `std::async` e devolve o número da tarefa (`double`) |
| `join(t)` | `__join(t)`: espera a tarefa e devolve o resultado (`double`) |
| `parse_ints(s)` | `__parse_ints(s)` |
| `lista.append(v)` / `.push_back(v)` | `lista.push_back(v)` |
| `lista.pop()` | `__array_pop(lista)` |
| `lista.size()` / `lista.size` | `lista.size()` |
| `for (var x in c)` | `for (auto x : c)` |
| `func f(a, b) { ... }` | `<ret> f(auto a, auto b) { ... }`; o tipo de retorno é inferido: `void` (sem `return valor`), `double` (se o retorno tem `/`, literal com ponto ou `join`) ou `auto` |

### Geração de Código Intermediário (TAC)

O gerador (`src/tac.py`) escreve `<nome>.tac` com código de três endereços. Temporários são `t0`, `t1`, ... e rótulos são `<PREFIXO>_<n>`.

| Construto MiniPar | TAC gerado |
|-------------------|-----------|
| `a + b` (qualquer binário) | `t0 = a + b` |
| `-a`, `!a` | `t0 = -a`, `t0 = !a` |
| `var x = e;` / `x = e;` | `x = <e>` |
| `[1, 2]` | `t0 = [1, 2]` |
| `matrix(l, c, v)` | `t0 = matrix(l, c, v)` |
| `x[i]` / `x[i] = v` | `t0 = x[i]` / `x[i] = v` |
| `o.campo` / `o.campo = v` | `t0 = o.campo` / `o.campo = v` |
| `f(a, b)` | `param a`, `param b`, `t0 = call f, 2` |
| `o.m(a)` | `param a`, `t0 = call o.m, 1` |
| `new C(...)` | `t0 = new C` (os argumentos não são emitidos) |
| `fork f(a)` | `param a`, `t0 = spawn f, 1` |
| `join(t)` | `t1 = join t` |
| `c_channel(ip, p)` | `t0 = c_channel(ip, p)` |
| `send(c, m)` / `receive(c)` | `send c, m` / `t0 = receive c` |
| `input(p)` | `t0 = input(p)` |
| `print a, b` | `print a`, `print b` |
| `if` / `else` | `ifFalse c goto ELSE_n`, `goto ENDIF_n`, `ELSE_n:`, `ENDIF_n:` |
| `while` | `WHILE_n:`, `ifFalse c goto ENDWHILE_n`, `goto WHILE_n`, `ENDWHILE_n:` |
| `do ... while` | `DO_n:`, corpo, `if c goto DO_n`, `ENDDO_n:` |
| `for` clássico | `FOR_n:`, `ifFalse c goto ENDFOR_n`, corpo, `FOR_STEP_n:`, incremento, `goto FOR_n`, `ENDFOR_n:` |
| `break` / `continue` | `goto` para o rótulo de saída / de continuação do laço mais interno |
| `func f(...) { ... }` | `func f:`, corpo, `endfunc f` |
| `return e` | `return e` (ou `return`) |
| `class C { ... }` | `# class C`, seguido dos métodos |
| `seq { ... }` / `par { ... }` | comandos emitidos em ordem (o `par` não é paralelizado no TAC) |

**Limitação:** o `for (var x in colecao)` emite apenas o comentário `# for x in colecao` e o corpo uma vez, sem expandir o laço.

---
