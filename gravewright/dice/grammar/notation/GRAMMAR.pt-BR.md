# Notação de dados do Gravewright — gramática inicial

[English](GRAMMAR.md) · [Português](GRAMMAR.pt-BR.md)

O parser produz somente a estrutura sintática. Não rola dados, não avalia
resultados, não acessa o SDK e não compila expressões em objetos `RollDefinition`.

## Subconjunto implementado

```ebnf
expression       = comparison ;
comparison       = additive, [ expression-comparison, additive ] ;
expression-comparison = "==" | "!=" | ">" | ">=" | "<" | "<=" ;
additive         = multiplicative, { ("+" | "-"), multiplicative } ;
multiplicative   = unary, { ("*" | "/"), unary } ;
unary            = ( "+" | "-" ), unary | primary ;
primary          = number | dice-expression | function-call |
                   "(", expression, ")" ;
function-call    = identifier, "(", [ expression, { ",", expression } ], ")" ;
identifier       = ( letter | "_" ), { letter | digit | "_" } ;
dice-expression  = [ positive-integer ], "d", ( positive-integer | "F" | "f" ),
                   { dice-modifier } ;
dice-modifier    = explode-modifier | reroll-modifier |
                   keep-modifier | drop-modifier ;
explode-modifier = "!", [ "o" ], [ explode-condition ] ;
reroll-modifier  = ( "r" | "rr" ), ( number | comparison-condition ) ;
keep-modifier    = ( "kh" | "kl" ), [ positive-integer ] ;
drop-modifier    = ( "dh" | "dl" ), [ positive-integer ] ;
comparison-condition = ( "=" | "!=" | ">" | ">=" | "<" | "<=" ), number ;
explode-condition = ( "=" | ">" | ">=" | "<" | "<=" ), number ;
number           = digit+, [ ".", digit+ ] | ".", digit+ ;
positive-integer = digit+ ;
```

Espaços em branco são ignorados entre tokens. O marcador canônico e único aceito
para dados é `d` minúsculo. Quantidade de dados e número de faces devem ser inteiros
positivos representáveis com segurança; `d20` significa `1d20`. Números decimais
comuns são aceitos, mas quantidades de dados ou faces decimais são erros de sintaxe.
Modificadores devem estar ligados lexicalmente ao termo de dados: `4d6kh3` é válido
e `4d6 kh3` é inválido. Espaços dentro de um modificador não são aceitos.

A ordem dos modificadores é preservada exatamente. Quando a quantidade é omitida
em `kh`, `kl`, `dh` ou `dl`, o padrão é um. `!` representa explosão recursiva e, por
padrão, verifica igualdade com a face máxima; `!o` explode uma única vez. Ambos
aceitam condições anexadas. `r` rola novamente uma vez e `rr` repete recursivamente;
ambos exigem um valor de igualdade implícita (`r1`) ou comparação explícita
(`r<=2`).

Após um termo de dados, `!` anexado sempre inicia um modificador de explosão.
Assim, `1d6!=5` significa explosão recursiva quando a face é igual a 5; não é a
expressão de comparação de desigualdade `1d6 != 5`. Essa regra de ligação lexical
evita reinterpretar a expressão conforme o contexto. Não existe notação para uma
condição de explosão por desigualdade nesta versão da gramática; o tipo de condição
do runtime continua capaz de representá-la.

Espaços são especialmente significativos no limite entre explosão e comparação:

- `1d6!=5` é um modificador de explosão anexado, com condição de igualdade a 5;
- `1d6 != 5` é uma comparação de conjunto usando desigualdade de expressão;
- `2d6!>=5` é explosão recursiva condicional, não contagem de sucessos;
- `2d6! >= 5` é explosão recursiva padrão seguida de contagem de sucessos do conjunto.

A igualdade entre expressões usa `==`. Um único `=` permanece reservado às condições
dos modificadores. Comparações não são associativas, portanto `1 < 2 < 3` é inválido.

## Precedência, da maior para a menor

1. Expressões entre parênteses.
2. Termos de dados e seus modificadores pós-fixados (`!`, `kh`, `kl`, `dh`, `dl`, `r`).
3. Operadores unários `+` e `-`.
4. Multiplicação e divisão, associativas à esquerda.
5. Adição e subtração, associativas à esquerda.
6. Comparações, não associativas.

Os seis níveis estão implementados. Chamadas de função comportam-se como expressões
primárias. Uma condição como `>=5` em `1d6!>=5` pertence ao modificador de explosão;
a comparação em `8d10 >= 8` é um nó separado de expressão de comparação.

## Divisão entre validação e execução em Python

Python valida tipos e limites de recursos na árvore de notação antes de rolar dados.
O executor avalia a árvore em profundidade e da esquerda para a direita. Planos
compactos de dados mantêm a estrutura serializada original, incluindo `count` e
`sides` iniciais e as operações ordenadas. O valor escalar padrão de um termo de
dados é a soma das faces cujo estado final de seleção é `active`.

Uma comparação cujo nó esquerdo da AST é diretamente um termo de dados é compilada
como contagem numérica de sucessos sobre os fatos ativos do conjunto. Seu limite de
comparação deve ser uma expressão aritmética numérica determinística sem dados.
Outras comparações são compiladas como comparações escalares booleanas. Parênteses
não são preservados como nós da AST; portanto, `(8d10) >= 8` tem a mesma semântica
de conjunto que `8d10 >= 8`.

## Funções numéricas padrão

O parser aceita a sintaxe de chamada sem conhecer a tabela de funções. O compilador
reconhece apenas `floor`, `ceil`, `round`, `abs`, `min`, `max` e `clamp`, em minúsculas.
Funções unárias exigem um argumento; `min` e `max` exigem dois ou mais; `clamp`
exige exatamente três. Todos os argumentos e retornos são numéricos. Os argumentos
são executados em profundidade e da esquerda para a direita. Nomes desconhecidos
ou em maiúsculas causam erros de compilação; não existe um registro de funções
mutável durante a execução.

## Extensão Fudge do VTT

`dF` (também `df`) usa um dado personalizado e equilibrado de seis faces: −1, −1, 0,
0, +1, +1. Aceita os mesmos modificadores; sua face máxima para explosão padrão é +1.
