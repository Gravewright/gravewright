# Assets de áudio e Sounds nativos

A SDK mantém quatro conceitos separados: Asset armazena bytes canônicos, Sound é
conteúdo semântico reutilizável, Spatial Sound posiciona esse conteúdo de forma
persistente em uma Cena e Audio Playback representa estado de execução.

`sdk.assets.ingest(file)` aceita arquivos de áudio selecionados pelo usuário e
validados por assinatura, retornando um Asset de `kind: "audio"`.
`sdk.assets.list({ kind: "audio" })` lê Assets autorizados da campanha sem expor
caminhos de armazenamento.

Pacotes usam `sounds.read` e `sounds.write` para `sdk.sounds.list`, `get`, `create`,
`update` e `delete`. A criação aceita referência `library-asset` ou `package-asset`
declarada. O áudio do pacote passa pela ingestão segura canônica antes da criação
do Sound nativo. Atualização e exclusão usam `expectedVersion`, preservando a
política nativa de dependências.


Uma exclusão de Sound ainda usado por Playlist, Soundscape ou Som espacial falha
com `RESOURCE_IN_USE` e informa `details.dependencyCount`, exatamente como a
biblioteca nativa de Sons; nada é removido parcialmente. Um `expectedVersion`
desatualizado falha com `STALE_VERSION`. `audio.playback` nunca concede autoridade
sobre a biblioteca de Sons: reproduzir áudio e editar conteúdo reutilizável são
capabilities separadas.
