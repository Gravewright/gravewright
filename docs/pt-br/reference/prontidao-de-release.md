# Prontidão de release

## Decisão de escopo

O Gravewright é responsável por manifests, descoberta/carregamento, validação
de dependências, resolução de capabilities, lifecycle, exports explícitos,
planejamento de composição e acesso por `use`, `capability` e `get`.

Módulos são responsáveis por framework frontend, UI, DOM, rendering, estado,
protocolos de rede, transporte, comunicação client/server, implementação de
persistência, integrações externas e APIs específicas da implementação.

## Achados reavaliados

| Achado | Classificação e decisão |
| --- | --- |
| Não existe transporte padrão server → browser | Non-goal: o módulo coordena suas próprias partes client e server. |
| Response neutra não modela todo o HTTP | Non-goal: a surface portável é pequena; necessidades especiais podem consumir exports de um server concreto. |
| `DynamicContext` não possuía diagnóstico | Inconsistência corrigida e coberta por verificação de tipos. |
| JSON Schema não expressa todas as invariantes | Divisão intencional: schema serve tooling; runtime controla semântica e grafo. |
| Capability usava `/v1` no nome | Corrigido para nome estável com versão SemVer separada. |
| `ActivationPlan` não era exportado pela raiz | Bug de empacotamento corrigido. |

## Footprint de dependencies do kernel

`@gravewright/kernel` possui uma única dependency third-party de runtime:
`semver`. Ela valida versões de módulos, ranges de dependencies e
compatibilidade de capabilities, responsabilidades diretas do kernel. Node não
oferece implementação nativa equivalente para ranges SemVer; reimplementá-la
aumentaria código e risco de correção sem reduzir o footprint de forma útil.

A outra dependency de runtime é a first-party `@gravewright/sdk`, que contém os
contratos compartilhados impostos pelo kernel. O pacote não depende de
framework, transporte, renderer, storage ou aplicação.

## Recomendação atual

**Ready for 0.9 pre-freeze.** Os contratos centrais possuem evidência de
composição e resolução de capabilities; lifecycle, reativação, segurança do marketplace e
consumo dos pacotes estão cobertos. A linha `0.9.x` continua sendo um período de
dogfooding e coleta de evidência, no qual correções breaking raras ainda são
possíveis. O freeze efetivo começa em `1.0.0-rc.1`, após evidência de ecossistema
e upgrades.
