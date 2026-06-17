# Segurança

## Modelo

O servidor é autoritativo. Clientes não devem ser tratados como fonte confiável de permissão, estado da mesa, ownership ou visibilidade.

## Controles

- Sessões assinadas no servidor.
- Proteção CSRF em formulários e comandos HTTP sensíveis.
- Validação de origem para WebSocket.
- Rate limits para auth e comandos.
- Limites de tamanho para payloads, uploads e viewport.
- Permissões por campanha e por recurso.
- Sanitização de paths para assets de pacotes SDK e uploads.
- Validação de manifest de pacote.
- Gating por capabilities no SDK.
- Bloqueio de capabilities perigosas como acesso bruto a banco, filesystem, rede e override de permissões.

## Pacotes com JavaScript

Pacotes que declaram `assets.scripts` executam JavaScript confiável no browser dos usuários da mesa.

Instale pacotes com script apenas de autores confiáveis.

## Checklist de Produção

- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `SESSION_SECRET` forte e privado.
- HTTPS no `PUBLIC_BASE_URL`.
- Cookies seguros.
- `ALLOWED_HOSTS` restrito.
- `WS_ALLOWED_ORIGINS` restrito.
- Backups testados.
- PostgreSQL com credenciais dedicadas.

## Segurança em Alpha

Antes de atualizar uma instância com dados importantes:

```bash
grave doctor
grave backup -o gravewright-backup.zip --include-assets --verify
```

Teste restore em uma cópia antes de atualizar a mesa real.

## Reportar Vulnerabilidades

Use `../../SECURITY.md` para instruções de reporte. Não publique detalhes exploráveis em issues públicas antes de coordenar a correção.
