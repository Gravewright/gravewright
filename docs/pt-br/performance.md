# Performance e metodologia de benchmark

O Gravewright publica os resultados brutos junto dos harnesses que os produziram. Toda afirmação de performance deve informar workload, modo do navegador, viewport, hardware, aquecimento, janela de medição e gates de validade.

## Máquina de referência atual

Os testes mais recentes foram executados em 13 de agosto de 2026 com:

- NVIDIA GeForce RTX 4060, driver 32.0.15.9621;
- Chromium headed usando ANGLE sobre Direct3D 11;
- aceleração por hardware ativa;
- viewport 1366×768;
- 10 segundos de aquecimento e 30 segundos de medição.

A GPU e o estado da aceleração estão gravados nos JSONs. Cadência obtida em modo headless não é usada como resultado de aceitação.

## Workloads

### Stress test de tokens animados compartilhados

O teste sintético usa uma única fonte canvas animada de 128×128 compartilhada por todos os dragões. Os tokens usam o caminho denso de fast sprites e são compactados no viewport. Esse teste mede escala de instâncias e compartilhamento de recursos; não representa uma campanha normal nem mede decode de vídeo.

| Dragões visíveis | Frame p95 | Callback p95 | Leitura |
|---:|---:|---:|---|
| 100 | 16,9 ms | 9,2 ms | baseline canônico |
| 6.500 | 16,9 ms | 13,8 ms | apresentação próxima de 60 Hz |
| 7.500 | 17,0 ms | 12,2 ms | último ponto medido na faixa de 60 Hz |
| 10.000 | 33,5 ms | 15,5 ms | apresentação próxima de 30 Hz |
| 11.000 | 33,7 ms | 16,5 ms | callback ainda dentro de 16,67 ms |
| 11.500 | 50,1 ms | 23,2 ms | orçamento do callback ultrapassado |

O joelho de apresentação fica entre 7.500 e 10.000 dragões visíveis. O cruzamento isolado do callback fica entre 11.000 e 11.500. Runs sequenciais próximos do limite apresentaram variância; por isso o projeto não declara um teto exato de uma única entidade.

Dados brutos: [`tests/performance/dragons_renderer/results-gpu-rtx4060/summary.md`](../../tests/performance/dragons_renderer/results-gpu-rtx4060/summary.md).

### Cena realista 5K

Esse workload desativa o atalho de fast sprites e usa mapa JPEG real de 5.000×5.000, nomes e duas barras por token, 150 paredes, 12 luzes dinâmicas, visão e darkness 0,6.

| Tokens visíveis | Runs válidos | Frame p95 mediano | Frame p99 mediano |
|---:|---:|---:|---:|
| 500 | 3/3 | 16,9 ms | 17,0 ms |
| 800 | 3/3 | 33,2 ms | 49,9 ms |

Relatório detalhado: [cena realista na RTX 4060](../benchmarks/gravewright-realistic-rtx4060.md).

## Regra de leitura

Não compare diretamente o teto do teste de dragões com a cena realista. O primeiro é um melhor caso sintético com asset compartilhado; o segundo inclui nomes, barras, iluminação, visão, paredes e composição do mapa. Sempre publique o workload ao lado do número.
