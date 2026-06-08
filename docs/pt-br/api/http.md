# API HTTP

O Gravewright usa handlers HTTP para auth, paginas renderizadas, formularios, uploads, assets e endpoints de jogo.

## Grupos De Rotas

- Auth: login, registro, recuperacao e reset de senha.
- Inside: dashboard, campanhas, convites, sistemas, modulos, configuracoes e diagnosticos.
- Game: pagina de mesa, atores, itens, diarios, cenas, tokens, permissoes, combate, chat e preferencias.
- Static: arquivos estaticos, assets de sistemas e assets de modulos.

## Autorizacao

Rotas autenticadas exigem sessao valida. Rotas de campanha validam membership, role e permissoes por recurso quando aplicavel. Operacoes destrutivas exigem permissao apropriada e protecao CSRF.

## Contrato

O servidor valida entrada e retorna HTML, redirects, JSON ou arquivos conforme a rota. Clientes e modulos nao devem depender de endpoints nao documentados como contrato estavel.
