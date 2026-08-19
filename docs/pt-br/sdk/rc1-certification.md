# SDK 1 RC 1 — registro de certificação

Status: **RC 1**. `sdkVersion`: **1**.

O status RC é metadado de release. Ele não cria um segundo eixo de compatibilidade:
pacotes declaram `"sdkVersion": "1"` e continuarão declarando quando a SDK 1 se tornar
estável.

## Contrato certificado

Derivado dos geradores canônicos no momento da certificação:

| | |
|---|---|
| Versão da SDK | 1 |
| Métodos | 264 |
| Capabilities | 116 |
| Eventos | 51 |
| Erros | 25 |
| DTOs | 290 |
| Retornos não resolvidos | 0 |
| Parâmetros não resolvidos | 0 |

Regenere com `scripts/generate_sdk1_contract.py` e `scripts/generate_sdk_reference.py`;
ambos verificam limpo com `--check`. A impressão digital semântica congelada está em
`_data/gravewright-sdk-1.rc1-snapshot.json` e é garantida por
`scripts/sdk1_contract_snapshot.py --check`. Veja
[rc1-compatibility-policy.md](rc1-compatibility-policy.md).

## Pacote de conformidade

Black Vault (`data/packages/addons/black-vault`) é o pacote permanente de conformidade
e estresse extremo da SDK 1 RC. Ele **não** é publicado no Marketplace de propósito.

| | |
|---|---|
| Referências a API privada | 0 |
| Capabilities desconhecidas | 0 |
| Uso de SDK não declarado | 0 |
| Exige mudança no core | Não |
| Métodos públicos usados | 51 |
| Capabilities declaradas | 45 |
| Eventos consumidos | 2 |
| Systemless | Sim — sem ruleset, sem dados |

Domínios exercitados: membros da campanha, atores, tokens, zonas, objetos de mundo,
gameplay flow, workflow durável, interações dirigidas, ações registradas, timeline
semântica, reprodução de áudio, sons nativos, sons espaciais, cartas, drag/drop
semântico, transferência de token, navegação de cena, apresentações, referências de
conteúdo, diários, aplicações de UI, comandos de entrada, settings e storage de
pacote. Package interop não é usado, porque a missão não precisa.

## Observações conhecidas não bloqueantes

Registradas, não corrigidas. Nenhuma bloqueia o RC 1.

1. **Gameplay Flow não tem estado terminal de recurso.** `advance` percorre as fases em
   ciclo e não existe `complete`/`cancel`, então a instância fica `ACTIVE`
   indefinidamente. Uma fase chamada `COMPLETE` basta para a missão expressar conclusão.
2. **`behavior.sound` de parede é somente escrita.** `createWall`/`updateWall` aceitam,
   mas `WallDTO`/`GeometryBehaviorDTO` não expõem, então o pacote não relê o que
   definiu. Porta fechada bloqueia som por padrão, então nenhuma missão fica bloqueada.
3. **O endpoint de comando do runtime retorna `201` de forma ampla**, inclusive em
   atualizações e alternâncias de estado. Convenção preexistente.
4. **Imagens distribuídas pelo pacote não viram Asset de campanha.**
   `sdk.assets.ingest` aceita apenas um `File` escolhido pelo usuário. A arte de carta
   é um `campaign-asset-slot` por design, então isso é intencional, não uma lacuna.
5. **O Package Doctor não enxerga todo uso declarativo de capability.** O Doctor agora
   infere capabilities a partir do registro de ações declarado, então uma ação
   registrada não reporta mais as capabilities de suas operações como não usadas.
   Definições registradas em runtime — passos `INTERACTION` de workflow e cues
   `AUDIO_PLAY` de timeline — continuam invisíveis à análise estática, então
   `interactions.request`, `interactions.respond` e `audio.playback` ainda podem
   aparecer como `capability_declared_unused`. São avisos sobre detecção, não sobre a
   declaração: as capabilities são exigidas e aplicadas em runtime. Fechar isso por
   completo exigiria análise estática real de JS.

## Orientação para autores

Construa sobre a SDK pública se quiser as garantias de compatibilidade de RC e
estável. Se o seu addon parecer precisar de uma API interna:

1. verifique se a SDK pública realmente não expressa o caso de uso;
2. reporte como lacuna pública da SDK, nomeando a operação bloqueada;
3. não trate internals privados como estáveis enquanto isso.

O Gravewright é código aberto e você continua livre para bifurcar ou modificar. Essas
mudanças simplesmente ficam fora da garantia de compatibilidade da SDK.
