# Kinds de pacote

`kind` define a função do pacote no ecossistema Gravewright.

## `ruleset`

Use `ruleset` para o sistema-base de uma campanha. Um ruleset normalmente declara:

- actor types;
- item types;
- sheets;
- rules;
- mappings;
- rolls;
- combat config;
- conteúdo inicial.

`activation.mode` deve ser `exclusive`: a campanha usa um ruleset ativo por vez.

## `addon`

Use `addon` para funcionalidades opcionais. Addons podem declarar settings, scripts, styles, comandos, chat cards, scene tools, overlays, plugins de runtime e integrações.

`activation.mode` deve ser `multiple`.

## `library`

Use `library` para dependências passivas compartilhadas. Bibliotecas não devem assumir ativação direta como feature de usuário.

`activation.mode` deve ser `passive`.

## `theme`

Use `theme` para alterações visuais, CSS e assets de interface. Themes devem preferir `entrypoints.game.styles` e `assets.styles`.

## `content`

Use `content` para conteúdo importável: encontros, compêndios, itens, actors, cenas ou pacotes de dados. Content packages devem funcionar sem runtime JS sempre que possível.

## `assets`

Use `assets` para mídia reutilizável: imagens, mapas, ícones, áudio, retratos e similares. Asset packages devem declarar `provides.assets` e capabilities por tipo.

## Escolha rápida

| Se o pacote... | Use |
|---|---|
| define o jogo que a campanha vai jogar | `ruleset` |
| adiciona uma feature opcional | `addon` |
| existe para outros pacotes dependerem dele | `library` |
| muda aparência | `theme` |
| distribui dados importáveis | `content` |
| distribui mídia reutilizável | `assets` |
