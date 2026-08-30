export const releaseGuides = {
  "pt-br": [
    {
      slug: "release-beta-4", section: "Comece aqui", title: "Gravewright Beta 4 e SDK 1 RC 1",
      summary: "Conheça a release atual, seus contratos e os cuidados de atualização.",
      body: `# Gravewright Beta 4 e SDK 1 RC 1

Gravewright **1.0.0-beta.4** certifica a paridade entre a CLI \`grave\` e o contrato público **SDK 1 RC 1**. Packages continuam declarando \`sdkVersion: "1"\`; RC 1 é metadata da release, não outra versão do manifest.

## Destaques

- scaffold e wizard para \`ruleset\`, \`addon\`, \`library\`, \`content\`, \`theme\` e \`assets\`;
- templates mantidos de ruleset, dry-run e saída JSON;
- \`validate\`, Package Doctor e \`grave doctor\` com responsabilidades distintas;
- content packs v2 com documentos inline ou lazy;
- Marketplace v2, provenance \`core/community/partner\` e updates verificados;
- canais \`stable\`, \`testing\` e \`dev\` publicados pelo registro remoto.

> [!WARNING]
> Os artefatos atuais estão no canal de desenvolvimento. Não existe release stable até que ela seja publicada no Marketplace. Faça um backup verificado antes de atualizar uma instalação com dados importantes.

## Próximos passos

Use *CLI, scaffold e diagnóstico* para authoring e *Marketplace, canais e updates* para distribuição. Consulte a referência de capabilities antes de pedir acesso ao runtime.`
    },
    {
      slug: "authoring-beta-4", section: "Criadores", title: "CLI, scaffold e diagnóstico",
      summary: "Crie, valide e diagnostique packages com o fluxo certificado da Beta 4.",
      body: `# CLI, scaffold e diagnóstico

Todos os seis kinds aceitam \`new\`. Os controles comuns são \`--name\`, \`--version\`, \`--output-dir\`, \`--yes\`, \`--force\`, \`--dry-run\`, \`--wizard\`/\`-i\` e \`--json\`.

\`\`\`powershell
.\\grave.bat ruleset new --wizard
.\\grave.bat addon new meu-addon --yes --json
.\\grave.bat content new meu-conteudo --dry-run --json
.\\grave.bat ruleset new --list-templates
.\\grave.bat ruleset new meu-rpg --template blank --yes --json
\`\`\`

Scaffolds de content emitem content packs v2: \`formatVersion: 2\`, \`documentType\`, \`indexFields\` e um arquivo com \`index\`. O formato 1 com \`entries\` permanece legível apenas por compatibilidade.

## Três níveis de verificação

\`grave package validate CAMINHO --json\` examina um diretório de authoring. \`grave package doctor ID --json\` examina um package instalado. \`grave doctor --json\` examina a instalação inteira; \`grave doctor --ai\` produz um resumo limitado para assistência, sem editar arquivos.

Saídas JSON contêm um único documento e \`error_key\` estável. \`--json\` nunca substitui \`--yes\` quando confirmação é necessária.`
    },
    {
      slug: "marketplace-updates", section: "Criadores", title: "Marketplace, canais e updates",
      summary: "Entenda publicação, provenance e atualização local ou remota.",
      body: `# Marketplace, canais e updates

Marketplace v2 distribui o Core e packages. Cada entrada pode publicar \`stable\`, \`testing\` e/ou \`dev\`, artefatos imutáveis, checksum e provenance \`core\`, \`community\` ou \`partner\`.

## Canais vêm do registro

Um canal só existe para o usuário quando aparece no \`marketplace.toml\` remoto. Ausência não cria fallback para um canal mais arriscado: stable recebe apenas stable; testing pode cair para stable; dev pode cair para testing ou stable. A CLI aceita os três valores do protocolo, mas uma consulta posterior falha com segurança se o registro não publicar o canal escolhido.

## Atualizar

\`grave package update ID\` atualiza o snapshot instalado a partir dos arquivos locais. \`grave package update ID --remote --json\` usa o instalador do Marketplace, verifica integridade, compatibilidade e dependências e preserva rollback/recovery.

O manifest não pode se autoproclamar \`core\` ou \`partner\`; essa provenance depende da associação confiável do registro e da integridade do artefato.`
    }
  ],
  en: [
    {
      slug: "release-beta-4", section: "Start here", title: "Gravewright Beta 4 and SDK 1 RC 1",
      summary: "Understand the current release, its contracts, and update precautions.",
      body: `# Gravewright Beta 4 and SDK 1 RC 1

Gravewright **1.0.0-beta.4** certifies parity between the \`grave\` CLI and the public **SDK 1 RC 1** contract. Packages still declare \`sdkVersion: "1"\`; RC 1 is release metadata, not another manifest version.

## Highlights

- scaffolds and a wizard for all six package kinds;
- maintained ruleset templates, dry runs, and JSON output;
- distinct roles for \`validate\`, Package Doctor, and \`grave doctor\`;
- content packs v2 with inline or lazy documents;
- Marketplace v2, \`core/community/partner\` provenance, and verified updates;
- registry-published \`stable\`, \`testing\`, and \`dev\` channels.

> [!WARNING]
> Current artifacts are on the development channel. No stable release exists until it is published in the Marketplace. Create a verified backup before updating an installation with important data.

Continue with *CLI, scaffolding, and diagnostics* for authoring or *Marketplace, channels, and updates* for distribution.`
    },
    {
      slug: "authoring-beta-4", section: "Creators", title: "CLI, scaffolding, and diagnostics",
      summary: "Create, validate, and diagnose packages with the certified Beta 4 workflow.",
      body: `# CLI, scaffolding, and diagnostics

All six kinds support \`new\`. Shared controls are \`--name\`, \`--version\`, \`--output-dir\`, \`--yes\`, \`--force\`, \`--dry-run\`, \`--wizard\`/\`-i\`, and \`--json\`.

\`\`\`powershell
.\\grave.bat ruleset new --wizard
.\\grave.bat addon new my-addon --yes --json
.\\grave.bat content new my-content --dry-run --json
.\\grave.bat ruleset new --list-templates
.\\grave.bat ruleset new my-rpg --template blank --yes --json
\`\`\`

Content scaffolds emit content packs v2 with \`formatVersion: 2\`, \`documentType\`, \`indexFields\`, and an \`index\` file. Format 1 \`entries\` remains readable only for compatibility.

## Three verification levels

\`grave package validate PATH --json\` checks an authoring tree. \`grave package doctor ID --json\` checks an installed package. \`grave doctor --json\` checks the whole installation; \`grave doctor --ai\` produces a bounded assistance summary without editing files.

JSON output contains one document and a stable \`error_key\`. \`--json\` never replaces \`--yes\` when confirmation is required.`
    },
    {
      slug: "marketplace-updates", section: "Creators", title: "Marketplace, channels, and updates",
      summary: "Understand publication, provenance, and local or remote updates.",
      body: `# Marketplace, channels, and updates

Marketplace v2 distributes the Core and packages. Each entry may publish \`stable\`, \`testing\`, and/or \`dev\`, immutable artifacts, checksums, and \`core\`, \`community\`, or \`partner\` provenance.

## Channels come from the registry

A channel exists for users only when the remote \`marketplace.toml\` publishes it. Resolution never falls upward to a riskier channel. The CLI accepts all three protocol values, but a later check fails safely if the selected channel is not published.

## Updates

\`grave package update ID\` refreshes the installed snapshot from local files. \`grave package update ID --remote --json\` uses the Marketplace installer and verifies integrity, compatibility, dependencies, rollback, and recovery.

A manifest cannot self-assert \`core\` or \`partner\`; trusted registry association and artifact integrity establish that provenance.`
    }
  ],
  es: [
    {
      slug: "release-beta-4", section: "Empieza aquí", title: "Gravewright Beta 4 y SDK 1 RC 1",
      summary: "Conozca la release actual, sus contratos y las precauciones de actualización.",
      body: `# Gravewright Beta 4 y SDK 1 RC 1

Gravewright **1.0.0-beta.4** certifica la paridad entre la CLI \`grave\` y el contrato público **SDK 1 RC 1**. Los packages siguen declarando \`sdkVersion: "1"\`; RC 1 es metadata de release, no otra versión del manifest.

## Destacados

- scaffold y wizard para los seis package kinds;
- templates de ruleset, dry runs y salida JSON;
- responsabilidades distintas para \`validate\`, Package Doctor y \`grave doctor\`;
- content packs v2 con documentos inline o lazy;
- Marketplace v2, provenance \`core/community/partner\` y updates verificados;
- canales \`stable\`, \`testing\` y \`dev\` publicados por el registro.

> [!WARNING]
> Los artefactos actuales están en el canal de desarrollo. No existe una release stable hasta que sea publicada en Marketplace. Cree un backup verificado antes de actualizar datos importantes.

Continúe con *CLI, scaffold y diagnóstico* para authoring o *Marketplace, canales y updates* para distribución.`
    },
    {
      slug: "authoring-beta-4", section: "Creadores", title: "CLI, scaffold y diagnóstico",
      summary: "Cree, valide y diagnostique packages con el flujo certificado de Beta 4.",
      body: `# CLI, scaffold y diagnóstico

Los seis kinds admiten \`new\`. Los controles comunes son \`--name\`, \`--version\`, \`--output-dir\`, \`--yes\`, \`--force\`, \`--dry-run\`, \`--wizard\`/\`-i\` y \`--json\`.

\`\`\`powershell
.\\grave.bat ruleset new --wizard
.\\grave.bat addon new mi-addon --yes --json
.\\grave.bat content new mi-contenido --dry-run --json
.\\grave.bat ruleset new --list-templates
.\\grave.bat ruleset new mi-rpg --template blank --yes --json
\`\`\`

El scaffold de content emite content packs v2 con \`formatVersion: 2\`, \`documentType\`, \`indexFields\` y un archivo \`index\`. El formato 1 con \`entries\` sigue legible solo por compatibilidad.

## Tres niveles de verificación

\`grave package validate RUTA --json\` comprueba un árbol de authoring. \`grave package doctor ID --json\` comprueba un package instalado. \`grave doctor --json\` comprueba toda la instalación; \`grave doctor --ai\` produce un resumen limitado sin editar archivos.

La salida JSON contiene un documento y un \`error_key\` estable. \`--json\` nunca reemplaza \`--yes\` cuando se requiere confirmación.`
    },
    {
      slug: "marketplace-updates", section: "Creadores", title: "Marketplace, canales y updates",
      summary: "Comprenda publicación, provenance y actualización local o remota.",
      body: `# Marketplace, canales y updates

Marketplace v2 distribuye el Core y packages. Cada entrada puede publicar \`stable\`, \`testing\` y/o \`dev\`, artefactos inmutables, checksum y provenance \`core\`, \`community\` o \`partner\`.

## Los canales vienen del registro

Un canal existe para el usuario solo cuando el \`marketplace.toml\` remoto lo publica. La resolución nunca sube a un canal más riesgoso. La CLI acepta los tres valores del protocolo, pero una consulta posterior falla de forma segura si el canal elegido no está publicado.

## Actualizaciones

\`grave package update ID\` actualiza el snapshot instalado desde archivos locales. \`grave package update ID --remote --json\` usa el instalador de Marketplace y verifica integridad, compatibilidad, dependencias, rollback y recovery.

El manifest no puede autodeclararse \`core\` o \`partner\`; la asociación confiable del registro y la integridad del artefacto establecen esa provenance.`
    }
  ]
};
