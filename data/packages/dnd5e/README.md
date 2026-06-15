# D&D 5e Framework para Gravewright

Sistema declarativo 5e para Gravewright.

## O que este pacote entrega

- Actor types: `character` e `monster`
- Item types: `weapon`, `armor`, `equipment`, `consumable`, `spell`, `feat`, `feature`, `race`, `background`, `class`
- Fichas declarativas para personagens, monstros e itens
- Regras derivadas para modificadores, proficiência, salvaguardas, perícias, passivas, iniciativa e CD/ataque de magia
- Token mappings para HP, iniciativa e defesa
- Content packs de modelo para testar drag/drop sem compêndio oficial completo

## Observação sobre conteúdo

Este pacote é um framework/sistema. Ele inclui entradas de modelo para validar fluxo de uso, mas não pretende ser um compêndio oficial completo. Use os packs como base para criar ou importar o conteúdo permitido da sua mesa.

## Decisões técnicas

- `sheet.weapons` guarda armas equipáveis/ataques de personagem.
- `sheet.inventory` guarda armaduras, equipamentos e consumíveis.
- `sheet.spells` guarda magias.
- `sheet.features` guarda talentos, características, raça, classe e antecedente.
- Drops criam snapshots editáveis dentro do Actor, preservando `source` para rastreabilidade.

