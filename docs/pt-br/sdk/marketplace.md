# Marketplace v2 e canais de distribuição

O catálogo canônico de packages é o `marketplace.toml` publicado em
`Gravewright/gravewright-marketplace`. O Gravewright baixa, valida o documento
inteiro e preserva atomicamente a última cópia válida. A cópia no repositório do
Core serve apenas para publicação e pode ser removida depois.

O protocolo reconhece `stable`, `testing` e `dev`, mas a interface lista apenas
os canais presentes no catálogo baixado. Selecionar um nome não publica o canal.
Core e Packages ficam vinculados por padrão, mas podem usar canais diferentes.
A resolução nunca sobe para um canal mais arriscado:

- `stable` aceita somente `stable`;
- `testing` prefere `testing` e usa `stable` como fallback;
- `dev` prefere `dev`, depois `testing`, depois `stable`.

Voltar para um canal mais conservador não executa downgrade. Uma versão
instalada mais nova aparece como `ahead-of-channel` até o canal alcançá-la ou o
owner solicitar um downgrade explícito e protegido.

O mesmo documento declara quais canais do Core estão publicados. A autoridade
do Core é fixa no repositório oficial e no feed de GitHub Releases do
Gravewright; hosts alternativos são rejeitados.

```toml
[core]
id = "gravewright"
name = "Gravewright"
enabled = true
repository = "https://github.com/Gravewright/gravewright"
releases = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"

[core.channels.dev]
enabled = true
```

A presença publica um canal; a ausência o torna indisponível. Enquanto tudo
estiver em desenvolvimento, Core e packages podem expor somente `dev`, sem
vazar essas builds para usuários em stable ou testing.

O parser atual da CLI aceita os três valores do protocolo. A disponibilidade é
resolvida depois pelo catálogo; assim, `grave channel set stable` pode salvar o
valor mesmo sem entrada stable publicada, e a consulta/update posterior reporta
canal indisponível sem fallback para cima.

## Formato

```toml
version = 2

[[packages]]
id = "example-addon"
name = "Example Addon"
kind = "addon"
enabled = true
source = "community"
update_policy = "publisher"

[packages.channels.stable]
manifest = "https://packages.example/stable/manifest.json"

[packages.channels.testing]
manifest = "https://packages.example/testing/manifest.json"

[packages.channels.dev]
manifest = "https://packages.example/dev/manifest.json"
```

O ID continua único e cada package pode publicar qualquer subconjunto dos três
canais. O formato v1 continua aceito para migração; `beta` vira `testing` e
`experimental` vira `dev`. Em `update_policy = "curated"`, cada canal declara
seu próprio `approved_version` e, opcionalmente, `approved_sha256`.

## Comunidade, publishers e propriedade intelectual

`source` aceita `core`, `community` e `partner`; a interface apresenta `partner`
como Publisher verificado. Canal, procedência, curadoria e direito de download
são independentes. Packages protegidos podem declarar:

```toml
source = "partner"
access = "entitled"
publisher = "Example Publisher"
license_model = "commercial"
auth_provider = "example-publisher"
```

O catálogo público nunca contém credenciais, chaves de licença, URLs secretas
permanentes ou dados do comprador. Sem um provider de entitlement conectado, o
package aparece como `license-required` e a instalação falha de forma segura.
Escolher `dev` não concede acesso ao canal privado de um publisher.

## Segurança e Core

Manifest, SDK, compatibilidade, SHA-256, ZIP, dependências e Package Doctor
continuam sendo validados antes da promoção atômica. Registro inválido ou falha
total de rede preserva o último catálogo válido.

O catálogo controla os manifests dos packages e quais canais do Core estão
publicados. Os binários do Core continuam vindo exclusivamente dos GitHub
Releases oficiais do Gravewright. O processo web nunca
substitui a própria instalação em execução; essa responsabilidade pertence ao
launcher verificado.
