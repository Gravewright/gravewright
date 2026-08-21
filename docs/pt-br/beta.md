# Estado Beta

Versão atual: **Gravewright v1.0.0-beta.3**.

O contrato público de extensões da SDK 1 está congelado. As versões Beta são
voltadas a correções compatíveis, segurança e permissões, confiabilidade das
migrações, documentação, testes e desempenho.

## Incluído na Beta 3

- campanhas, cenas, atores, itens, journals, cartas e combate autoritativos no servidor;
- pacotes SDK 1 com capabilities e autoridade do usuário verificadas;
- visualização, navegação, busca, metadados e anotações de PDF pela SDK 1;
- backup, restore, snapshots, clonagem, exportação e importação de campanhas;
- mapas virtual-raster, granularidade adaptativa e prefetch guiado pelo GM;
- iluminação dinâmica, paredes, portas, partículas, shaders e composição para streamer;
- renderer de tokens com assets compartilhados e benchmarks reproduzíveis;
- rulesets de compatibilidade para PDF e Savage Worlds.

## Compatibilidade

Autores de pacotes devem usar `sdkVersion: "1"` e declarar todas as capabilities
consumidas. A Beta 3 é certificada contra a SDK 1 RC 1; packages continuam
declarando `sdkVersion: "1"`, pois RC não é uma segunda versão de manifesto. Mudanças no banco são entregues
por migrations Alembic, e as APIs públicas documentadas da SDK 1 formam o limite
de compatibilidade.

## Atualização

1. Crie um backup verificado com `grave backup -o pre-upgrade.zip --include-assets --include-packages --verify`.
2. Execute `grave doctor` e resolva problemas de schema ou pacotes.
3. Atualize a aplicação e execute o fluxo normal de migrations.
4. Verifique a instância e uma campanha representativa antes do uso normal.

## Feedback

Relatos são mais úteis quando incluem passos exatos, versão do Gravewright, logs
do navegador e servidor sem segredos, escala da campanha/mapa, número de
jogadores e o comportamento esperado comparado ao observado.
