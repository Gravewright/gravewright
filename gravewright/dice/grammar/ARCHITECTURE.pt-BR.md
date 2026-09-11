# Dados do Gravewright — execução em Python

[English](ARCHITECTURE.md) · [Português](ARCHITECTURE.pt-BR.md)

Toda avaliação no servidor ocorre em Python. `engine.py` valida a entrada e a
concorrência e, em seguida, chama este pacote. Não há subprocessos Node, arquivos
de motor JavaScript, fontes TypeScript ou etapas de compilação TypeScript.

- `parser.py`: análise por descida recursiva, preservando a precedência original
  dos operadores, a ligação lexical dos modificadores de dados e os intervalos
  de posição no texto-fonte.
- `compiler.py`: regras de tipos numéricos e booleanos, funções permitidas,
  limites determinísticos para comparação de conjuntos de dados e limites de
  complexidade; não consome aleatoriedade.
- `runtime.py`: avaliação da esquerda para a direita, ordenação estável ao
  manter/descartar dados, filas de explosão/nova rolagem processadas em largura
  e geração limitada de fatos.
- `errors.py`: exceção `RollError` exposta à integração Django.

`compile_expression` valida uma árvore de notação em memória. Não compila arquivos
de código-fonte nem produz um artefato executável. O executor inclui os planos de
dados no resultado JSON existente para manter compatibilidade com o histórico
persistido.

## Resultados e aleatoriedade

O resultado mantém o schema `gravewright-dice-result`, versão 1, valores, planos,
fatos, intervalos no texto-fonte, estados de seleção e registros de comparação.
Os fatos preservam IDs, índices físicos das faces, causas, linhagem e entropia
normalizada. Seleção e geração preservam fatos anteriores; o histórico renderiza
o JSON armazenado sem chamar novamente o gerador de números aleatórios.

As amostras de produção usam `secrets` do Python. Testes podem injetar um gerador
chamável; clientes não podem escolhê-lo pelo conteúdo das mensagens WebSocket.
Cada repetição independente recebe um novo executor e uma nova sequência de IDs
de resultado. As funções numéricas padrão preservam a semântica original, incluindo
o arredondamento de empates em direção ao infinito positivo.

## Limites de recursos

A entrada aceita no máximo 512 caracteres e aninhamento sintático de 32 níveis.
A compilação verifica 1.000 nós, profundidade semântica de 128 níveis e 100
argumentos por chamada de função. A execução permite 99 dados iniciais por termo,
1.000 faces, 256 dados iniciais por expressão, 32 termos de dados, 256 resultados
gerados por termo e 512 fatos por expressão. São aceitas até 12 repetições
independentes. Quatro avaliações podem ocorrer simultaneamente por processo.
Não é possível executar explosões recursivas ilimitadas.

## Evidências de equivalência

`../tests/legacy_results.json` registra 396 casos determinísticos do motor original.
Os testes Python comparam os resultados JSON completos e a rejeição de expressões
inválidas. Testes adicionais verificam repetições independentes, amostras aleatórias
válidas e avaliação sem processos externos.
