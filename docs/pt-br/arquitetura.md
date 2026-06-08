# Arquitetura

O Gravewright e uma aplicacao web server-authoritative para mesas virtuais de RPG.

## Backend

O backend usa Litestar para rotas HTTP, WebSocket, handlers de formulario, redirects e renderizacao Jinja2. A regra pratica e simples: o servidor decide o estado autoritativo da mesa, valida comandos e persiste mudancas.

Camadas principais:

- `app/actions/`: entrada HTTP, WebSocket, formularios e templates.
- `app/business/`: regras de produto para usuarios, campanhas, auth e permissoes.
- `app/engine/`: servicos de mesa, cenas, fichas, chat, sistemas, modulos e conteudo.
- `app/realtime/`: transporte WebSocket, comandos, eventos, presenca e replay.
- `app/persistence/`: tabelas SQLAlchemy Core e repositorios.

## Frontend

O frontend usa HTML renderizado no servidor, CSS estatico, JavaScript modular e PixiJS para o tabuleiro. O cliente envia intencoes; o servidor valida, persiste e retransmite eventos.

## Persistencia

SQLite e o padrao local e de testes. PostgreSQL e o backend esperado para producao. O runtime cria schema local quando necessario, e migracoes ficam em `migrations/`.

## Realtime

`/game/ws` e o canal de mesa. Ele transporta comandos do cliente e eventos do servidor. O event log permite replay e reconexao dentro dos limites configurados.

## Sistemas E Modulos

Sistemas definem regras, modelos de ficha, layouts, rolagens, combate, assets e conteudo inicial.

Modulos sao extensoes escopadas por campanha. Eles podem expor assets, hooks de navegador, conteudo e configuracoes.

APIs publicas documentadas sao materiais MIT. A implementacao do runtime e Apache-2.0.
