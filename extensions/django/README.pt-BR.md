# Módulos Django do servidor

Pasta padrão para apps Django confiáveis instalados pelo operador do host.
Configurada por `GRAVEWRIGHT_DJANGO_MODULES_ROOT` no `.env`; o
`config/settings.py` a acrescenta ao `sys.path`, então um pacote colocado
diretamente nesta pasta só precisa ter seu caminho de importação listado em
`GRAVEWRIGHT_SERVER_APPS`:

```
extensions/django/meu_app/__init__.py
extensions/django/meu_app/apps.py
```

```
GRAVEWRIGHT_SERVER_APPS=meu_app
```

Entradas explícitas em `GRAVEWRIGHT_SERVER_APP_PATHS` continuam suportadas para
checkouts mantidos em outro lugar, e têm precedência sobre esta pasta. Um
`AppConfig` pode expor `gravewright_urlconf` para acrescentar rotas.

Esses apps rodam como código de servidor confiável: precisam aplicar
autenticação, CSRF e as permissões nativas de domínio. Eles nunca são populados
por manifestos de pacotes de navegador, e suas dependências Python ainda exigem
instalação separada. Uma importação inválida impede a inicialização em vez de
desativar o app silenciosamente.

O conteúdo da pasta é ignorado pelo git, para que apps de terceiros fiquem fora
do histórico deste repositório.

Veja `docs/pt-BR/modules.md` ("Apps Django instalados explicitamente").
