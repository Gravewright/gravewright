# Implantação e backups

[Documentação](../README.pt-BR.md) · [English](../en/deployment.md)

Este guia cobre a implantação em servidores. Para uma instalação Windows usada apenas no próprio computador, use o [Gravewright Runner](windows-runner.md), que administra o armazenamento pessoal e um perfil local com um único processo.

## HTTPS e WebSockets

Gravewright oferece páginas HTTPS e WebSockets seguros (WSS). Configure `GRAVEWRIGHT_PUBLIC_ORIGIN` com a origem acessada pelo navegador, como `https://vtt.example.com`. O [SameOriginWebSocketMiddleware](../../gravewright/realtime/security.py) usa essa origem para validar o `Origin` do navegador e o `Host` da requisição, incluindo a porta efetiva. Isso também funciona com Daphne **4.2.3**, cujo escopo WebSocket omite `scheme`.

Atrás de um proxy reverso que termina TLS, o [TrustedProxySchemeMiddleware](../../config/proxy.py) restaura o esquema HTTP/HTTPS ou WS/WSS antes de encaminhar a requisição pelo roteador ASGI. Aceita exatamente um cabeçalho `X-Forwarded-Proto: http` ou `https` apenas quando o endereço do par conectado pertence a `TRUSTED_PROXIES`. Valores de origem não confiável, duplicados, separados por vírgula ou malformados mantêm o esquema original. Assim, Django reconhece HTTPS corretamente nas verificações CSRF e nas respostas HSTS.

A origem pública define uma origem permitida; não cria um listener TLS nem concede permissões. WebSockets da mesa continuam exigindo host permitido, uma única origem válida e correspondente, sessão válida e autorização na campanha. Sem origem pública configurada, a verificação WebSocket usa o esquema ASGI `ws`/`wss`; esquema ausente assume HTTP local. Portanto, TLS direto no Daphne exige a origem pública HTTPS. Apenas `DJANGO_SECURE_COOKIES=true` não a fornece.

## Configuração de execução

Use um checkout versionado e uma conta com escrita no banco e no armazenamento privado. Configure `DJANGO_SECRET_KEY` persistente e privada, `DJANGO_DEBUG=false`, hosts explícitos, origem pública e URL do Redis. A origem deve ser HTTP(S), sem caminho ou barra final. HTTPS ativa cookies de sessão/CSRF seguros e HSTS nas configurações.

Gere a chave localmente e guarde em configuração protegida, mantendo-a entre reinicializações:

```bash
uv run --locked python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Não publique o valor gerado em issue, commit ou log compartilhado. Veja [configuração](configuration.md) para limites, caminhos e prioridade das variáveis.

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python manage.py migrate --noinput
uv run --locked --no-dev python manage.py collectstatic --noinput
uv run --locked --no-dev python manage.py check --deploy
uv run --locked --no-dev daphne -b 127.0.0.1 -p 3000 config.asgi:application
```

Esses comandos pressupõem os valores de produção configurados e pastas existentes. `check --deploy` pode indicar decisões pendentes de configuração; verifique também o endereço público conforme descrito abaixo. O último comando usa HTTP em loopback atrás do proxy TLS. `main.py` usa o `runserver` de desenvolvimento; `config.wsgi` não atende WebSockets.

## Proxy reverso Nginx

Para Nginx e Daphne no mesmo servidor, defina estes valores na configuração protegida da aplicação, junto com sua `DJANGO_SECRET_KEY` privada:

```dotenv
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=vtt.example.com
GRAVEWRIGHT_PUBLIC_ORIGIN=https://vtt.example.com
TRUSTED_PROXIES=127.0.0.1/32
GRAVEWRIGHT_REDIS_URL=redis://127.0.0.1:6379/0
```

Use o comando Daphne em loopback acima **sem `--proxy-headers`**. Essa opção substitui o endereço do par conectado antes da verificação do Gravewright e conflita com a confiança em proxies controlada pela aplicação. `TRUSTED_PROXIES` controla a resolução do IP encaminhado e o adaptador de esquema ASGI. Confie apenas nos endereços dos proxies que podem conectar ao Daphne e mantenha a porta interna privada. Em contêineres, substitua loopback pelo endereço real do proxy imediato ou por uma rede confiável de escopo restrito.

O exemplo Nginx abaixo pertence ao contexto `http`. Substitua domínio, arquivos existentes de certificado/chave e caminho absoluto do checkout antes de ativá-lo. O limite de 100 MiB no corpo da requisição é um exemplo operacional; ajuste aos uploads e à capacidade do servidor. As diretivas TLS e o upgrade WebSocket seguem o [guia HTTPS do Nginx](https://nginx.org/en/docs/http/configuring_https_servers.html) e o [guia de proxy WebSocket](https://nginx.org/en/docs/http/websocket.html).

```nginx
map $http_upgrade $gravewright_connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name vtt.example.com;
    return 308 https://vtt.example.com$request_uri;
}

server {
    listen 443 ssl;
    server_name vtt.example.com;

    ssl_certificate /etc/letsencrypt/live/vtt.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vtt.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 100m;

    location /static/ {
        alias /srv/gravewright/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $http_host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $gravewright_connection_upgrade;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Forwarded "";
        proxy_set_header X-Forwarded-Host "";
        proxy_set_header X-Forwarded-Port "";
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

`Host $http_host` preserva a porta usada pelo navegador; Nginx encaminha `Origin` sem alterações. O proxy substitui os valores de encaminhamento confiáveis, sem acrescentar dados enviados pelo cliente. Consulte a [configuração de cabeçalhos do proxy Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header). Para uma porta pública diferente de 443, inclua-a em `GRAVEWRIGHT_PUBLIC_ORIGIN`, no listener TLS e no destino do redirecionamento. `DJANGO_ALLOWED_HOSTS` contém nomes de host sem portas.

Nginx redireciona HTTP para HTTPS; este checkout não ativa o redirecionamento SSL global do Django. Instale um certificado válido e configure sua renovação, valide a configuração com `nginx -t` e recarregue Nginx pelo gerenciador de serviços. Após alterações, confira login, cookies de sessão/CSRF com Secure, HSTS em uma resposta da aplicação e conexão autenticada da mesa com status `101` por WSS. Verifique duas sessões e a rejeição de origem WebSocket externa. O teste automatizado de TLS direto e proxy está descrito em [testes](testing.md).

## Arquivos estáticos e armazenamento privado

Sirva `/static/` a partir de `staticfiles/`, gerado por `collectstatic`. Recursos atendidos por views próprias, inclusive módulos de frontend, continuam dependendo das rotas da aplicação. Com debug desativado, o Django não serve automaticamente os arquivos coletados pelo handler estático de desenvolvimento.

Mantenha `MEDIA_ROOT` privado: mapas, PDFs, diários, áudio, cartas e pacotes de módulos são atendidos por rotas protegidas. Um alias público `/media/` ignoraria as verificações. Faça backup do armazenamento junto com o banco. Coleções opcionais em `data/vtt/compendiums/` também precisam de backup.

Configure limites de upload e timeouts do servidor externo. O limite padrão de bytes de mapa é 50 GiB, enquanto pixels decodificados, dimensões e quantidade de tiles têm limites separados; aceitar muitos bytes não significa que haverá memória suficiente para processar o arquivo.

## Vários processos

Todos os workers precisam compartilhar banco, arquivos, chave secreta, configuração de confiança dos módulos e camada Redis. As configurações padrão do servidor exigem `GRAVEWRIGHT_REDIS_URL` com debug desativado, mesmo em um único processo. O executor local possui um perfil separado e não pode ser usado para essa implantação. Channels em memória não entrega eventos entre workers.

SQLite é o banco configurado e usa transações `IMMEDIATE`. Redis entrega eventos; não substitui o banco nem mantém um registro durável da partida. Vários processos ainda compartilham a disputa por escrita do SQLite; o código não fornece configuração PostgreSQL nem afirma suportar armazenamento distribuído horizontalmente. Dimensione com base em cargas observadas.

Use um gerenciador de serviços para supervisionar ASGI e Redis, guardar logs e encerrar processos adequadamente. Após mudanças de hospedagem, teste duas sessões, visibilidade de mestre/jogador, uploads, reconexão WebSocket e reinício de workers.

## Backup e restauração

Exportações são pacotes portáveis de conteúdo; snapshots são pontos de recuperação da campanha. Nenhum deles é um backup completo da instância. Exportações omitem ou ajustam vínculos, proprietários e parte do histórico privado; o estado de instalação de módulos está fora do grafo exportado. Consulte [archives.py](../../gravewright/administration/archives.py).

Para um backup completo consistente:

1. Interrompa escritas, incluindo todos os processos ASGI e processos de manutenção.
2. Copie o banco SQLite configurado e arquivos journal/WAL associados, se existirem, toda a mídia privada, coleções opcionais e configurações/chaves de confiança necessárias. Também é possível usar a operação de backup do SQLite, coordenada com a cópia dos arquivos.
3. Registre a versão correspondente do código, o lock file e as licenças. Proteja segredos separadamente e restrinja acesso ao backup.
4. Restaure primeiro em uma pasta separada, ajustando os caminhos. Verifique login, uma campanha, uploads representativos e módulos antes de direcionar usuários para ela.

Não copie somente `db.sqlite3` da raiz nem restaure código antigo sobre banco já migrado para uma versão nova. Teste rollback com banco e arquivos correspondentes, sem presumir que migrações sejam reversíveis.

## Atualizações e serviços opcionais

A descoberta de versões do núcleo é opcional por `GRAVEWRIGHT_RELEASES_REPOSITORY=owner/repo`. Espera artefatos Django compatíveis com metadados SHA-256. O atualizador atual informa estado e artefato; não substitui a instalação em execução. Confira os bytes baixados, faça backup, revise migrações e atualize o código manualmente.

O marketplace usa catálogo HTTPS e arquivo local de chaves públicas Ed25519 confiáveis. URL vazia deixa a descoberta online sem configuração. Revise autores e código antes de instalar módulos, pois executam na origem da aplicação. Veja [módulos](modules.md).

O e-mail usa o backend de console do Django. Texto e publicação da política de privacidade são administrados pelo operador; ativar uma opção não fornece política preenchida nem serviço de e-mail. Considere também licenças das dependências, servidor Redis, navegador e imagem de contêiner efetivamente distribuídos; consulte [avisos de terceiros](../../THIRD_PARTY_NOTICES.pt-BR.md).

### Atualizações pela interface: Windows, Linux e macOS

O início normal por `main.py` e pelo Gravewright Runner ativa o supervisor
por padrão. No Windows, o `Gravewright Runner.bat` mantém seu funcionamento
habitual. No Linux e macOS, `uv run --locked python main.py` também inicia o
fluxo de atualização; `--dev` é reservado ao desenvolvimento com autoreload.
Não é necessário iniciar um modo especial para usar o botão de atualização.

Em Administração → Atualizações, escolha o canal, verifique a versão e clique
em **Fazer backup e instalar atualização**. O download, validação SHA-256,
preparação de dependências, backup, migrações, reinício e recuperação são
controlados por essa tela nos três sistemas operacionais. Alpha usa o canal
Desenvolvimento. Acesso e conexões de mesa são interrompidos durante a troca;
a tela acompanha o retorno do servidor.

O pacote `Gravewright-VERSAO-django.zip` deve ter digest SHA-256 publicado no
GitHub, versão superior e os arquivos do supervisor. O repositório padrão é
`Gravewright/gravewright`; uma configuração explicitamente vazia desabilita a
consulta. A release inicial `0.1.0-alpha.0`, anterior ao supervisor, não pode
aplicar atualizações: é necessário distribuir este inicializador atualizado
para habilitar o fluxo da interface nessa instalação antiga.

A versão nova fica em um diretório separado. Banco, mídia, compêndios e os
arquivos estáticos compartilhados do Runner são preservados. Falhas de
migração ou inicialização restauram a versão anterior e seus dados. Uma
transação interrompida é recuperada ao iniciar novamente. Checkouts Git com
alterações locais são protegidos contra substituição. Não execute outro
servidor contra o mesmo banco durante a atualização.

O Runner guarda versões, backups e `update.log` na pasta `updates` dentro de
seu diretório de dados. O inicializador por `main.py` usa o diretório de estado
do usuário: `%LOCALAPPDATA%/Gravewright/updates` no Windows,
`~/Library/Application Support/Gravewright/updates` no macOS e
`$XDG_STATE_HOME/gravewright/updates` (ou `~/.local/state/gravewright/updates`)
no Linux. Preserve esses diretórios e reserve espaço para backups, que não são
apagados automaticamente.

O workflow `Automatic updates` testa Windows, Linux e macOS nativamente.
Para reproduzir, execute `uv run python tests/e2e/automatic_updates.py` e
`uv run python tests/e2e/automatic_updates.py --runner`; ambos usam dados
temporários, HTTPS local e falhas deliberadas de migração e inicialização.
