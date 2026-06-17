# Storage

## Diretorios

`storage/` guarda arquivos de runtime, incluindo banco SQLite local, uploads, imagens processadas, tiles e assets escopados por campanha.

`data/` guarda pacotes SDK. `GRAVEWRIGHT_DATA_DIR` permite mover pacotes instalaveis para fora do repositorio.

## Uploads

Uploads de mapas, imagens de atores, imagens de diarios e assets relacionados sao validados por tipo, tamanho, dimensao e path. O servidor deve tratar todo upload como entrada nao confiavel.

## Campanhas

Dados de campanha incluem:

- linhas relacionais no banco;
- cenas, layers, tiles e chunks;
- tokens e condicoes;
- atores, itens, diarios, pastas e permissoes;
- chat, combate, convites e presenca;
- assets enviados para mapas, atores e diarios;
- storage escopado por pacote/ruleset.

Deletar uma campanha remove dados relacionados em cascata no banco e no storage escopado.

## Backups

Backups precisam capturar banco e arquivos no mesmo ponto logico. Backup apenas do banco ou apenas do storage pode deixar referencias quebradas.
