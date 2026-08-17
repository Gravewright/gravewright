# Registro curado do Marketplace v1

O Marketplace é um índice curado para descoberta, instalação e atualização. A
fonte canônica é `marketplace.toml`: cada entrada aponta para um
`manifest.json`, nunca diretamente para um artifact.

## Formato do registro

```toml
version = 1

[[packages]]
id = "example-addon"
kind = "addon"
manifest = "https://packages.example/example-addon/manifest.json"
enabled = true
channel = "stable"
update_policy = "publisher"
```

Os kinds canônicos são `ruleset`, `addon`, `library`, `content`, `theme` e
`assets`. `category`, `tags`, `featured` e `reviewed_at` são apenas editoriais.
O manifest é a autoridade para versão, SDK, compatibilidade, capabilities,
dependências e distribuição. O Marketplace rejeita divergências de `id` ou
`kind`.

Packages oficiais ou publishers confiáveis usam `update_policy = "publisher"`
e um manifest estável na raiz. Uma nova versão válida declarada nesse manifest
pode ser oferecida automaticamente.

Packages comunitários usam, no Marketplace v1, um manifest pinado à tag/release
aprovada, `update_policy = "curated"` e `approved_version`. O campo opcional
`approved_sha256` vincula a aprovação aos bytes exatos.

```toml
[[packages]]
id = "community-addon"
kind = "addon"
manifest = "https://raw.githubusercontent.com/example/addon/v1.4.2/manifest.json"
enabled = true
channel = "stable"
update_policy = "curated"
approved_version = "1.4.2"
```

## Manifest e artifact

`$schema` identifica exclusivamente o JSON Schema usado para validar o
manifest. Ele não participa de discovery, versionamento nem download.

Os campos v1 preferenciais `download` e `sha256` apontam para o ZIP imutável e
versionado da release e contêm o SHA-256 esperado. A representação existente
`distribution.url`/`distribution.sha256` continua compatível. O Marketplace
exige ambos, valida o hash antes de extrair e confirma que `id`, `kind`,
`version` e `sdkVersion` do manifest dentro do artifact correspondem ao
manifest remoto aprovado.

## Refresh, cache e instalação

O refresh valida cada manifest separadamente e grava o cache de forma atômica.
Um manifest novo inválido não substitui a última entrada válida em cache. Uma
falha total de rede preserva o catálogo anterior e packages instalados continuam
funcionando offline.

Install e Update baixam com limite de tamanho, validam URL e redirects, SHA-256,
limites e caminhos do ZIP, extraem em staging, executam o Package Doctor e só
então publicam. Se a publicação ou persistência falhar, a versão anterior é
restaurada. A instalação manual existente continua independente do Marketplace.
