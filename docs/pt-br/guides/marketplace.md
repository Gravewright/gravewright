# Publicação e instalação no marketplace

O marketplace é um módulo `system`, não um subsistema especial do kernel. A
implementação incluída serve `/marketplace` pelo server ativo e lê o catálogo
oficial do repositório Gravewright marketplace.

## Modelo de descoberta

Um catálogo contém metadados e valores estáveis de `manifest_url`. O Gravewright
não depende da marca do host Git: GitHub, GitLab, GitBucket, uma CDN ou um server
HTTPS simples funcionam se expuserem os mesmos documentos.

```text
catálogo ──► URL estável do manifest ──► ZIP imutável do release
                                            └── SHA-256 no manifest
```

O manifest estável pode ser atualizado para apontar ao release mais novo. A
instalação usa a versão e o ZIP referenciados por ele; nunca clona ou instala a
branch `main` do repositório.

## Publique um módulo

1. Gere um ZIP com `manifest.json` na raiz ou dentro de um único diretório superior.
2. Publique o ZIP como asset imutável de um release.
3. Calcule seu digest SHA-256.
4. Publique um manifest JSON numa URL HTTPS estável com `download_url` e `download_sha256`.
5. Abra uma issue no repositório do marketplace pedindo a inclusão no catálogo.

Para uma nova versão, publique outro ZIP imutável e depois atualize o manifest
estável e os metadados do catálogo. Nunca substitua os bytes de uma versão e hash
já publicados.

## O que a instalação verifica

O installer incluído aceita URLs HTTPS públicas na porta 443 e sem credenciais.
Ele rejeita endereços privados e reservados, revalida redirects, limita tempo e
prende cada conexão ao endereço que passou na validação, limita tamanho de
respostas, quantidade de arquivos e tamanho extraído. Path traversal, links e
arquivos especiais são rejeitados antes do início da extração.

Antes do commit, ele verifica o SHA-256, nome e versão do manifest arquivado e se
o entry existe dentro do pacote. Dependências npm de produção são instaladas no
próprio módulo com `npm ci --omit=dev --ignore-scripts` e exigem um
`package-lock.json` publicado. Pacotes sem lockfile são rejeitados para evitar
que cada máquina resolva uma árvore diferente.

Dependências Node seguem uma política exclusiva de registry. A validação do
package e lockfile rejeita specs de filesystem, workspace, URL, Git, shorthand
de repositório e tarballs arbitrários. Toda entrada externa do lock precisa vir
do registry npm aprovado e possuir integrity. A instalação usa configuração e
cache npm temporários, sem herdar tokens, configuração privada do usuário ou
`.npmrc` do módulo. TLS continua obrigatório. `--ignore-scripts` reduz risco,
mas não é sandbox.

Esses controles reduzem riscos de transporte, SSRF e arquivos malformados. Eles
não auditam o JavaScript do módulo nem o isolam do processo host.

## Dependências e ativação

A UI primeiro solicita um plano dry-run. Quando há dependências ausentes, mostra
nomes, versões e ordem de instalação antes da confirmação. O installer resolve o
grafo inteiro e confirma dependências antes do módulo solicitado. Uma falha
desfaz instalações preparadas.

Módulos instalados permanecem desativados até que o projeto mude seus estados.
Recipes podem incluir estados desejados e escolhas de providers de capabilities
num único plano revisável.

## Catálogos adicionais

Adicione a configuração local em `gravewright.marketplace.local.json` ou informe
URLs separadas por vírgula em `GRAVEWRIGHT_CATALOGS`. O catálogo oficial continua
habilitado. Falhas remotas usam o último cache local válido e exibem um aviso, em
vez de fingir silenciosamente que o catálogo está atualizado.
