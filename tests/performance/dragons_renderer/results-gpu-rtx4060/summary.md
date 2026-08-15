# Benchmark dos dragões — NVIDIA RTX 4060

Executado em 13 de agosto de 2026 com Chromium headed, viewport 1366×768, uma única fonte animada compartilhada, 10 s de warm-up e 30 s de medição por ponto.

## GPU confirmada

- dispositivo: NVIDIA GeForce RTX 4060;
- driver: 32.0.15.9621;
- backend: ANGLE sobre Direct3D 11;
- aceleração por hardware: ativa;
- renderer WebGL: `ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 (0x00002882) Direct3D11 vs_5_0 ps_5_0, D3D11)`.

Essas informações estão gravadas em todos os JSONs desta rodada. Não houve uso de SwiftShader ou Chromium headless.

## Resultado

| Solicitados | Visíveis | Frame p95 | Frame p99 | Callback p95 | App render p95 | Long tasks |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 16,9 ms | 17,0 ms | 9,2 ms | 5,5 ms | 0 |
| 6.000 | 6.000 | 16,9 ms | 33,3 ms | 14,8 ms | 5,0 ms | 0 |
| 6.250 | 6.250 | 16,9 ms | 17,3 ms | 14,7 ms | 5,0 ms | 0 |
| 6.500 | 6.500 | 16,9 ms | 33,2 ms | 13,8 ms | 4,8 ms | 0 |
| 7.500 | 7.500 | 17,0 ms | 33,3 ms | 12,2 ms | 4,4 ms | 0 |
| 10.000 | 10.000 | 33,5 ms | 50,0 ms | 15,5 ms | 5,0 ms | 7 |
| 11.000 | 11.000 | 33,7 ms | 50,2 ms | 16,5 ms | 5,2 ms | 9 |
| 11.500 | 11.500 | 50,1 ms | 66,3 ms | 23,2 ms | 6,9 ms | 43 |
| 12.500 | 12.500 | 50,0 ms | 50,4 ms | 23,1 ms | 7,5 ms | 15 |

Os pontos de 10.000, 11.000 e 11.500 da tabela são execuções isoladas, cada uma em um Chromium novo. Isso evita que crescimento anterior da matriz seja confundido com o resultado do ponto.

## Novo limite observado

Há dois limites diferentes:

1. **Cadência apresentada:** 7.500 ainda permanece na faixa de aproximadamente 60 Hz no p95; 10.000 cai para 33,5 ms, aproximadamente 30 Hz. Portanto o joelho de apresentação está entre **7.500 e 10.000 dragões simultaneamente visíveis**.
2. **Orçamento interno do callback:** 11.000 registra 16,5 ms, ainda abaixo do orçamento de 16,67 ms; 11.500 registra 23,2 ms. O cruzamento observado fica entre **11.000 e 11.500 dragões visíveis**.

Para comunicação conservadora, a RTX 4060 sustenta **aproximadamente 7.500 dragões visíveis na faixa de 60 Hz** e **aproximadamente 10.000 na faixa de 30 Hz** neste workload sintético.

O joelho antigo de aproximadamente 5.150 não se reproduziu nesta rodada: 6.500/6.500 ficaram visíveis, com frame p95 16,9 ms e callback p95 13,8 ms. O resultado antigo permanece como histórico daquela execução, mas não deve ser apresentado como o limite confirmado na RTX 4060.

## Variância próxima ao limite

A matriz sequencial de refinamento (`results-gpu-rtx4060-refine`) produziu callback p95 entre 22,7 e 23,1 ms em 10.100–10.500, enquanto as execuções isoladas deram 15,5 ms em 10.000 e 16,5 ms em 11.000. Isso mostra variância dependente do estado/ordem perto do limite. Por esse motivo:

- o relatório não afirma um joelho exato de uma única entidade;
- a faixa 11.000–11.500 usa os pontos isolados mais comparáveis;
- 7.500 é a recomendação conservadora para preservar a cadência apresentada.

## Arquivos brutos

- `diagnostic-scale-headed.json`: 100, 6.000, 6.250 e 6.500;
- `../results-gpu-rtx4060-high/diagnostic-scale-headed.json`: 7.500, 10.000 e 12.500;
- `../results-gpu-rtx4060-10000-isolated/diagnostic-scale-headed.json`;
- `../results-gpu-rtx4060-11000-isolated/diagnostic-scale-headed.json`;
- `../results-gpu-rtx4060-11500-isolated/diagnostic-scale-headed.json`;
- `../results-gpu-rtx4060-refine/diagnostic-scale-headed.json`: varredura sequencial complementar.
