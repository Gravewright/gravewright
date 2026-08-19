# SDK 1 RC 1 — política de compatibilidade

A SDK **1** do Gravewright está no **Release Candidate 1**. O contrato público está
congelado: o que estiver publicado em `gravewright-sdk-1.json`,
`gravewright-sdk-1.d.ts` e na documentação da SDK é o que um pacote pode usar como
base, e não se espera que mude novamente antes de a SDK 1 se tornar estável.

O status RC fala sobre estabilidade, não sobre versão. `sdkVersion` é `1`, pacotes
declaram `"sdkVersion": "1"`, e a promoção de RC 1 para SDK 1 Estável não muda esse
campo nem obriga a republicar nenhum pacote.

## O que é público

Apenas o que o contrato declara:

- os métodos, parâmetros e tipos de retorno em `gravewright-sdk-1.json`;
- os tipos em `gravewright-sdk-1.d.ts`;
- as capabilities, eventos e códigos de erro nos mesmos registros;
- a semântica de runtime que esses documentos descrevem — autoridade, visibilidade,
  concorrência e durabilidade.

## O que não é público

Todo o resto, incluindo:

- campos de resposta que o DTO não declara;
- formatos internos de serviços e repositórios;
- o DOM, o renderer e qualquer coisa em `window` além do ponto de entrada documentado;
- rotas HTTP privadas e frames de WebSocket crus;
- o esquema do banco e o layout do sistema de arquivos;
- eventos internos e campos de DTO exclusivos da implementação.

Um pacote que dependa de qualquer um deles **não tem garantia de compatibilidade**, e
uma release pode alterá-los sem aviso. Isso não restringe o que você pode fazer com o
código — o Gravewright é aberto, e bifurcar ou modificar é totalmente legítimo. É uma
declaração sobre o que a SDK promete manter funcionando.

Antes do RC 1, a leitura de Token repassava campos internos não declarados, entre eles
`token_id` e um `controlled_by_user_ids` sem filtro. Eles nunca fizeram parte do
contrato; a leitura agora retorna o `TokenDTO` declarado, cujo campo de identidade é
`id` e cuja lista `controllers` é filtrada pela autoridade de quem chama para
inspecionar controle. Nenhum alias é fornecido para os campos internos removidos.

## Quebra versus compatível

**Quebra** — não permitido durante o RC sem revisão explícita:

- remover ou renomear método, capability, evento ou código de erro;
- remover campo público de DTO ou estreitar um tipo público;
- tornar um parâmetro opcional obrigatório, ou remover um parâmetro;
- mudar o que um método retorna;
- mudar a semântica de autoridade para quem já era um chamador válido;
- mover um método para outro namespace.

**Compatível** — permitido durante o RC:

- correções de bug, segurança e desempenho;
- trocar a implementação por trás de um contrato inalterado;
- correções de documentação e novos testes;
- remover campos internos vazados ou não declarados, que nunca foram prometidos;
- adicionar campo ou parâmetro opcional, após revisão explícita de RC.

Métodos e capabilities novos são estruturalmente compatíveis, mas o RC 1 é um
congelamento de funcionalidades: exigem revisão explícita, e o classificador de diff
os reporta como `POTENTIALLY_BREAKING` para que não entrem em silêncio.

## Como o congelamento é garantido

`docs/sdk/_data/gravewright-sdk-1.rc1-snapshot.json` é uma impressão digital semântica
do contrato certificado — identidade dos métodos, obrigatoriedade e tipos dos
parâmetros, tipos de retorno, ids de capabilities, eventos e erros, e campos de DTO.
Formatação, ordenação e texto ficam de fora de propósito, então a documentação pode ser
reescrita livremente.

```
python scripts/sdk1_contract_snapshot.py --diff    # classifica cada diferença
python scripts/sdk1_contract_snapshot.py --check   # falha em mudança que quebra
python scripts/sdk1_contract_snapshot.py --write   # recongela após mudança aprovada
```

A suíte de testes roda `--check`, então uma quebra acidental falha no CI em vez de
chegar a um pacote publicado.

## Reportar uma lacuna

Se o seu addon precisa de algo que a SDK pública não expressa:

1. confirme que nenhuma composição pública existente resolve;
2. reporte como lacuna pública da SDK, indicando a operação bloqueada;
3. não publique contra internals privados esperando que se mantenham.

A SDK **2** é reservada exclusivamente para uma mudança incompatível intencional deste
contrato público. Não é número de release do produto, e a versão do produto anda de
forma independente.
