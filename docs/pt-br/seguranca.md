# Seguranca

## Modelo

O servidor e autoritativo. Clientes nao devem ser tratados como fonte confiavel de permissao, estado da mesa, ownership ou visibilidade.

## Controles

- Sessoes assinadas no servidor.
- Protecao CSRF em formularios e comandos HTTP sensiveis.
- Validacao de origem para WebSocket.
- Rate limits para auth e comandos.
- Limites de tamanho para payloads, uploads e viewport.
- Permissoes por campanha e por recurso.
- Sanitizacao de paths para assets de sistemas, modulos e uploads.

## Checklist De Producao

- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `SESSION_SECRET` forte e privado.
- HTTPS no `PUBLIC_BASE_URL`.
- Cookies seguros.
- `ALLOWED_HOSTS` restrito.
- `WS_ALLOWED_ORIGINS` restrito.
- Backups testados.
- PostgreSQL com credenciais dedicadas.

## Reportar Vulnerabilidades

Use `../../SECURITY.md` para instrucoes de reporte. Nao publique detalhes exploraveis em issues publicas antes de coordenar a correcao.
