# Modelo de segurança da SDK

A SDK é desenhada em torno de manifests de pacote declarativos, capabilities explícitas, referências de arquivo seguras, runtimes de navegador escopados e estado de jogo autoritativo no servidor.

## Objetivos de segurança

- Tornar a intenção da extensão visível antes do install/ativação.
- Manter as capabilities do pacote explícitas e revisáveis.
- Prevenir path traversal de pacote.
- Evitar execução de plugin de backend no SDK v1.
- Evitar acesso cru a banco, filesystem, rede e override de permissões.
- Manter as APIs de pacote do navegador escopadas ao pacote dono.
- Tratar o servidor como autoritativo para persistência, permissões e estado de jogo.

## Capabilities são explícitas

Todo pacote declara as capabilities solicitadas em `manifest.json`.

```json
"capabilities": ["assets.scripts", "settings"]
```

O engine rejeita capabilities desconhecidas e proibidas. O runtime do navegador aplica gates aos métodos da SDK conforme as capabilities declaradas.

## Forbidden capabilities

Estas são sempre rejeitadas:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

O SDK v1 não suporta código de pacote executado no backend.

## JavaScript confiável no navegador

Pacotes que declaram `assets.scripts` rodam código de navegador confiável para os usuários da mesa.

Revise pacotes com `assets.scripts` cuidadosamente:

- confirme a origem do pacote;
- revise as capabilities solicitadas;
- inspecione os scripts do pacote;
- prefira manifests declarativos quando possível;
- instale apenas pacotes apropriados para a mesa.

A CLI avisa ao instalar pacotes que rodam JavaScript confiável.

## Propriedade do script

O runtime verifica que um script de pacote só pode registrar o id do próprio manifesto. O registro é recusado quando:

- o script não está associado a um pacote;
- o id reivindicado difere do id de pacote do script;
- o pacote está inativo;
- o pacote já registrou.

Isto impede que o script de um pacote se registre como outro pacote ativo.

## Paths seguros

Paths referenciados no manifesto devem ser relativos ao pacote e seguros.

Inválidos:

```text
../secret.txt
/etc/passwd
https://example.com/script.js
C:\Users\file.txt
```

Válidos:

```text
assets/main.js
assets/theme.css
schemas/character.schema.json
content/items.gwpack.json
locales/en.json
```

O loader verifica os paths referenciados e rejeita paths inseguros.

## Superfícies de navegador públicas vs privadas

Público:

- `window.GravewrightSDK.register(...)`
- objeto `sdk.*` escopado passado às funções de ciclo de vida do pacote
- eventos de pacote documentados
- plugins de runtime de ficha/combate documentados via `sdk.sheets` e `sdk.combat`

Privado, salvo se explicitamente documentado:

- globals do renderer;
- stores privadas;
- estrutura do DOM;
- ordenação interna de eventos WebSocket;
- nomes internos de classes CSS;
- labels de fallback;
- substituição completa do renderer de ficha;
- substituição completa do renderer de combate;
- `window.GravewrightSDKDebug` em produção.

## Autoridade do servidor

Pacotes de navegador podem melhorar a UI, submeter intenções e reagir ao estado. Eles não devem tratar o estado local do navegador como autoritativo.

Autores de pacote devem assumir:

- permissões são aplicadas no servidor;
- mudanças de estado de jogo devem passar por rotas/comandos/intents documentados;
- o estado de UI local pode estar desatualizado;
- mensagens WebSocket podem ser atrasadas, reenviadas ou rejeitadas;
- outros pacotes podem estar ausentes ou inativos.

## Checklist do operador

Antes de instalar um pacote:

- Rode `grave package validate <package>`.
- Revise `capabilities`.
- Verifique se `assets.scripts` está presente.
- Verifique `dependencies` e `conflicts`.
- Revise a origem e a licença do pacote.
- Faça backup das campanhas importantes.

Antes de atualizar pacotes:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
grave lock -o grave.lock.json
```

## Checklist do autor de pacote

- Use o menor conjunto de capabilities.
- Mantenha os arquivos dentro do diretório do pacote.
- Evite globals privados e internals do DOM.
- Faça namespace dos eventos pelo id do pacote.
- Versione os payloads de eventos entre pacotes.
- Trate pacotes par opcionais ausentes como normal.
- Não armazene secrets em settings de pacote.
- Documente cada solicitação de capability.
