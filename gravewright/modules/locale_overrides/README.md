# Reviewed host interface copy

`pt-BR.json` contains reviewed corrections for native Gravewright interface strings
in the official Translator catalog. The host applies these exact source-to-text
mappings only while `gravewright.translator` is active, compatible and provides
Brazilian Portuguese. It never rewrites the signed archive, extracted module
files, stored package catalog or user-authored content.

The Runner uses `DEFAULT_LOCALE` from the project `.env`, loading the active
Translator catalog after database preparation. Before the database and language
module are ready, this file also supplies Portuguese installer and startup copy.
Selecting a language in the installer changes the remaining prompts immediately.

Use infinitives for action labels: **Criar mesa**, **Editar cena**, **Enviar PDF**.
Use **mesa** for the RPG session and **tabela de rolagem** for random-result tables.
The shared vocabulary is **personagem**, **ficha**, **token**, **mestre**, **diário**,
**carta**, **baralho**, **sistema de regras**, **ponto de restauração** and
**material compartilhado**. Keep product names, commands, keyboard shortcuts,
code, identifiers and placeholders unchanged. Instructions may use the imperative.

Apply new corrections here and in Translator's authoring catalogs. The source
repository is https://github.com/Gravewright/translator. Its reviewed overrides
must also be updated so rebuilding the catalogs retains the changes.
