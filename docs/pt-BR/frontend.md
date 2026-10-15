# Arquitetura do frontend

[Índice da documentação](../README.pt-BR.md) · [English](../en/frontend.md) · [Referência da API](api.md)

A aplicação renderiza HTML Jinja2 no servidor, usa Datastar para sinais reativos e atualizações de fragmentos e executa controladores JavaScript nos espaços interativos. O tabuleiro usa PixiJS e possui pipeline próprio de fontes/build. Não existe um build único de SPA para toda a aplicação.

## Acompanhe a página pelo template

[`base.html`](../../gravewright/web/jinja2/gravewright_web/base.html) carrega CSS compartilhado, Datastar distribuído localmente e `gravewright_modules/frontend-api.js`, que cria `window.gravewright`. O ambiente `/inside` e a mesa de jogo estendem essa estrutura. [`table/page.html`](../../gravewright/table/jinja2/gravewright_table/page.html) compõe templates e carrega controladores de mesa, mapa, documentos, atores, dados e módulos.

Áreas úteis para começar:

| Local | Finalidade |
| --- | --- |
| `gravewright/web/jinja2/` | Estrutura compartilhada, páginas Inside e HTML reutilizável |
| `gravewright/accounts/jinja2/` | Templates de autenticação e configuração inicial da conta |
| `gravewright/web/static/gravewright_web/css/` | Variáveis visuais, estilos base e componentes |
| `gravewright/web/static/gravewright_web/inside/` | Controladores/estilos de contas, campanhas e administração |
| `gravewright/web/static/gravewright_web/windows.js` | Janelas móveis e redimensionáveis |
| `gravewright/table/static/gravewright_table/realtime.js` | Socket, assinaturas, fragmentos autenticados e eventos |
| `gravewright/modules/static/gravewright_modules/` | API pública de navegador, runtime de módulos, transporte e ciclo de vida |
| `gravewright/maps/frontend/` | Fontes editáveis de tabuleiro, paredes, tokens, iluminação, seleção e ferramentas |
| `gravewright/maps/static/gravewright_maps/workspace.js` | Integração do espaço de mapas |
| `gravewright/pdf_system/frontend/` | Fontes editáveis de mapeamento/controlador PDF |
| `jinja2/`, `static/` e `messages.json` de cada app | Interface, estilos e textos do domínio |

IDs e atributos `data-*` dos templates conectam controladores nativos e superfícies de extensão. Alterá-los pode afetar o controlador, sinais Datastar e montagem de módulos. Confira os três ao renomear seletores ou substituir painéis inteiros.

## Dimensões compartilhadas e tokens visuais

[`tokens.css`](../../gravewright/web/static/gravewright_web/css/tokens.css) define os valores visuais compartilhados. Tokens dimensionais fixos usam valores simples em `px`. Reutilize os tokens existentes quando forem adequados ao componente e introduza um novo valor compartilhado somente quando ele for necessário entre componentes. A escala Fibonacci e seu script de auditoria foram retirados; o CSS do núcleo usa as regras de espaçamento, raio e tipografia abaixo em vez de `--fib-*` ou `--step-*`.

Use `--space-*` para padding, margens e gaps, incluindo suas formas abreviadas, lógicas e de linha/coluna. Ao migrar uma dimensão fixa, escolha o valor mais próximo desta escala; em caso de empate, escolha o menor. Preserve o sinal de margens negativas. O sufixo do token conta passos de quatro pixels, com nomes separados para zero, um e dois pixels:

| Token | Valor |
| --- | --- |
| `--space-0` | `0` |
| `--space-px` | `1px` |
| `--space-half` | `2px` |
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-5` | `20px` |
| `--space-6` | `24px` |
| `--space-7` | `28px` |
| `--space-8` | `32px` |
| `--space-10` | `40px` |
| `--space-12` | `48px` |
| `--space-14` | `56px` |
| `--space-16` | `64px` |

O antigo valor de 34px de `--space-9` é substituído por `--space-8` com 32px. Os raios de borda usam estes nomes compartilhados:

| Token | Valor |
| --- | --- |
| `--radius-sm` | `4px` |
| `--radius-md` | `8px` |
| `--radius-lg` | `12px` |
| `--radius-xl` | `16px` |
| `--radius-pill` | `999px` |
| `--radius-circle` | `50%` |

O CSS da interface do host deve renderizar textos com **12px ou mais**. Confira os tamanhos efetivos vindos de estilos herdados, unidades relativas e formas abreviadas de fonte, além de `font-size` explícito. Os nomes existentes `--text-3xs`, `--text-2xs` e `--text-xs` continuam disponíveis com 12px. Textos de PDFs e desenhos, assim como rótulos de cena escalados pela câmera, preservam os tamanhos definidos pelo autor.

Larguras, alturas e demais geometrias dos componentes mantêm as dimensões necessárias. Um valor específico de um único componente pode usar um literal local em `px`; reserve tokens `--size-*` compartilhados para valores reutilizados entre componentes. A geometria responsiva ainda pode usar unidades relativas e expressões de layout como `calc()` e `clamp()` quando necessário.

## Estado nativo e tempo real

O frontend nativo usa a API de domínio compartilhada onde implementada e mantém adaptadores HTTP/socket especializados para uploads, assinaturas do tabuleiro e fragmentos renderizados. A API pública não substitui todos os transportes nativos.

O controlador de tempo real conecta o WebSocket autenticado da mesa atual, gerencia assinaturas/reconexão e dispara eventos `gravewright:*`. O servidor envia projeções autorizadas por usuário e HTML renderizado; dados privados, audiência do chat e visibilidade da cena são filtrados antes do envio. Insira texto de usuário com `textContent`. A inserção de fragmentos HTML existente destina-se ao HTML dos templates confiáveis do servidor, não a texto arbitrário de chat ou módulo.

`gravewright:api-event` é o evento interno consumido pela API de domínio; notificações `api.changed` provocam novas leituras autorizadas. Integrações públicas devem usar `api.events.on(...)`, conforme [eventos da API](api.md#eventos-de-domínio), em vez de copiar comandos internos de socket. Assinaturas não são um fluxo durável: reconecte e releia o estado. Criar `gravewright.forTable(...)` não abre um socket.

Os diretórios nativos de itens e compêndios ordenam cópias das entradas visíveis
pelo nome exibido, usando o idioma ativo; a ordem armazenada e os IDs dos
documentos permanecem intactos. Pacotes, filtros e prévias de compêndios usam
linhas compactas e janelas com tamanho inicial ajustado ao conteúdo, com rolagem
interna para conteúdos longos. O usuário mantém os controles compartilhados de
mover, redimensionar, minimizar e redefinir janelas. Mestres podem criar o
primeiro compêndio no diretório vazio; acesso de leitura não exibe controles de
importação ou permissões. Os editores de itens de cada sistema permanecem em
seus pacotes e usam os contratos existentes do host. Projeções de itens repetidas
preservam menus de ações abertos e foco; alterações de documento ou permissão
invalidam esses menus.

## Fontes e arquivos gerados

A maioria dos JavaScripts de cada app em `static/` é fonte servida diretamente. Alguns arquivos são resultados de build versionados. [`maps/scripts/build.cjs`](../../gravewright/maps/scripts/build.cjs) gera:

| Entrada/fonte editável | Destino gerado |
| --- | --- |
| `maps/frontend/widgets/game-board/ui/board.js` | Bundle/chunks em `maps/static/gravewright_maps/vendor/` |
| `maps/frontend/shared/rendering/render-profile.js` | `maps/static/gravewright_maps/render-profile.js` |
| `maps/frontend/native/tools.js` | `maps/static/gravewright_maps/tools.js` |
| `maps/frontend/native/table-modules.js` | `table/static/gravewright_table/media-workspace.js` |
| `maps/frontend/features/walls/{ui,model}/walls.js` | `maps/static/gravewright_maps/walls/` |
| Fontes de camadas e perfis de iluminação | `maps/static/gravewright_maps/sources/` |
| `maps/frontend/calibration.js`, `directory.js` | Modelos/controladores estáticos correspondentes |
| `maps/frontend/shared/lib/dom/tree-drag.js` | `actors/static/gravewright_actors/tree-drag.js` |
| `maps/frontend/features/tokens/ui/controller.js` | `tokens/static/gravewright_tokens/controller.js` |
| `pdf_system/frontend/controller.js` | `pdf_system/static/gravewright_pdf_system/controller.js` |

Os caminhos da tabela são relativos a `gravewright/`. Edite fontes e reconstrua os destinos. Evite correções isoladas em chunks minificados ou bibliotecas de terceiros.

Na raiz do repositório:

```sh
npm ci --include=dev --prefix gravewright/maps/frontend
npm run build --prefix gravewright/maps/frontend
npm test --prefix gravewright/maps/frontend
```

O build usa PixiJS/esbuild fixados em [`maps/frontend/package-lock.json`](../../gravewright/maps/frontend/package-lock.json), gera ES2022 e mantém imports `/static/*` externos. O módulo compartilhado de perfil de renderização permanece externo para todos os recursos usarem a mesma instância. O build também copia licenças/avisos das dependências e escreve `vendor/packages.json`; preserve esses arquivos na redistribuição. Ele rejeita a inclusão de pacotes Vue.

### Preparação pelo executor Windows

O [Gravewright Runner](windows-runner.md) reutiliza Node.js/npm verificados dentro de `data/runner/` ou baixa sua cópia gerenciada nessa instalação quando necessário. Seu arquivo em lote CMD chama [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) no modo `--plan` para conferir versões dos pacotes, impressões dos arquivos e uma operação real do esbuild. Uma instalação correspondente e funcional das dependências pode ser reaproveitada já na primeira execução. O próprio arquivo em lote executa `npm ci --include=dev --include=optional` quando é necessário instalar dependências e o `npm run build` existente na primeira preparação ou em um build invalidado. Depois chama o helper no modo `--record` para verificar e salvar o estado das saídas concluídas. O esbuild é necessário durante a preparação, embora as dependências Python de desenvolvimento sejam omitidas da instalação normal do executor.

O plano retorna código de saída `0` para recursos atuais, `10` para instalação npm e build, ou `11` para somente build. O launcher em lote trata essas decisões explicitamente. Ambos os modos do helper aceitam `--node`, `--npm-cli` e `--state-dir`; o modo padrão do helper continua disponível para realizar a preparação completa em scripts de desenvolvimento e testes de regressão.

O projeto npm permanece em `gravewright/maps/frontend`; seu `node_modules/` ignorado é instalado ali e os recursos estáticos gerados são gravados nos destinos acima. Essas saídas são recursos versionados da aplicação; portanto, uma alteração nos fontes seguida da preparação pelo executor pode produzir um diff no controle de versão. Revise e inclua as saídas geradas e os avisos apropriados ao contribuir alterações de frontend.

O estado da preparação fica dentro da pasta descompactada em `data/runner/frontend/<hash-local-do-código>/state.json`. Ferramentas gerenciadas e caches do npm/uv também ficam nesta instalação. A verificação das dependências inclui arquivos de pacotes e versões Node/npm selecionadas. A verificação do build inclui fontes editáveis, script de build e hashes das saídas geradas. O arquivo em lote solicita ao `build.cjs` um manifesto das saídas, incluindo avisos de terceiros, pela variável de processo opcional `GRAVEWRIGHT_BUILD_MANIFEST`. Uma próxima execução pula um build válido e inalterado; entradas modificadas ou saídas ausentes/modificadas provocam nova preparação. Um build com falha impede a inicialização, em vez de servir um frontend não verificado. Depois, `collectstatic` copia os recursos públicos preparados para o diretório `data/staticfiles/` dentro do projeto.

O registro de métodos de domínio possui geração própria:

```sh
uv run --locked python scripts/generate_frontend_api.py
```

O script gera somente `modules/static/gravewright_modules/frontend-contract.js` a partir de `contracts/frontend.json`. `generated.js` e schemas do SDK original são artefatos separados, não gerados por esse script. `collectstatic` reúne arquivos para implantação, mas não executa builds JavaScript.

## Camadas do tabuleiro e ciclo dos recursos

`maps/frontend/` separa modelos de entidades, modelos/UI de funcionalidades, utilitários e widget do tabuleiro. O widget coordena renderização, entrada, agendamento/cache/pré-carregamento de tiles, camadas nativas, polígonos de visão, luzes e shaders. As funcionalidades incluem paredes, tokens, desenhos, medidas, efeitos e seleção. Testes de algoritmos ficam ao lado dos modelos e são empacotados por `maps/scripts/test_models.cjs` para o executor de testes do Node.

Mantenha um sistema de coordenadas consistente: pixels lógicos da cena, origem superior esquerda e centro dos tokens como âncora. Pan/zoom convertem posições em coordenadas CSS da área visível; a densidade de pixels altera a resolução de renderização. Misturar unidades desalinha seleção, tokens e luzes. A API de sobreposição oferece conversão explícita em vez de expor o renderer PixiJS.

Operações assíncronas pertencem a uma página, tabuleiro, ativação ou montagem. [`Lifetime`](../../gravewright/modules/static/gravewright_modules/lifetime.js) cancela chamadas e remove assinaturas; os fontes de mapas possuem utilitários próprios. Adicione/remova listeners e observers com seu proprietário. Libere recursos gráficos e tarefas pendentes ao encerrar o tabuleiro ou trocar de cena. Listener ou API que sobrevive ao contexto pode atualizar a próxima cena com dados antigos.

## Estendendo a interface

O [`SurfaceRegistry`](../../gravewright/modules/static/gravewright_modules/surface-registry.js) do host aceita `gravewright.ui.register(domain, declaration)` e retorna função de cancelamento. Suporta superfícies da mesa, `app.shell` e `inside.content`. Uma montagem recebe `{root, context, api, signal, onDispose}`, ciclo de vida e raiz próprios. Falhas geram limpeza e restauram a visibilidade anterior dos elementos nativos substituídos. Esse registro global permite uma substituição por domínio.

Pacotes assinados usam `ModuleRuntime`: registro síncrono durante ativação, chamadas com identidade/lease/revisão e seleção de substituições pelas preferências da mesa. Use o callback `register` do módulo para pacotes instalados; o registro global é destinado a integrações da página do host e tem outras regras de propriedade/seleção. Veja exemplos e nomes em [módulos](modules.md).

## Verificação do frontend

Execute as verificações afetadas pela alteração:

```sh
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
npm test --prefix gravewright/maps/frontend
uv run --locked python tests/e2e/frontend_api.py
```

Para renderização/interação, use cenários relevantes de `tests/e2e/`, incluindo `mixed_selection.py`, `token_routes.py`, `light_rendering.py`, `effect_geometry.py`, `effect_pixels.py`, `map_prefetch.py` e `realtime.py`. O ambiente de navegador está descrito em [testes](testing.md). Verifique sessões de mestre e jogador quando houver permissões distintas e valide limpeza/reconexão de assinaturas novas. Mantenha textos e catálogos alinhados aos idiomas suportados pela aplicação.
