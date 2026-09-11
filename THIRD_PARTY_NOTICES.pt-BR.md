# Avisos de terceiros

[English (principal)](THIRD_PARTY_NOTICES.md) · [Licença do projeto](LICENSE)

Este inventário descreve as dependências e o material incluído na árvore de código analisada em **2026-09-11**. A licença do Gravewright não substitui as licenças de terceiros. As condições de direitos autorais, atribuição, distribuição do código-fonte e outras condições desses componentes continuam aplicáveis. Os textos das licenças permanecem em seu idioma original; este documento traduz somente o inventário explicativo.

## Evidências e cobertura

- Python: todos os **42 pacotes de terceiros** em [uv.lock](uv.lock), incluindo dependências diretas, transitivas, de desenvolvimento e condicionadas à plataforma. Quarenta distribuições instaladas correspondem exatamente às versões fixadas. Os wheels de `tzdata` e `u-msgpack-python` foram baixados das URLs do lock e conferidos pelos hashes SHA-256; não foi necessário instalá-los.
- Mapas: todas as **39 dependências npm** em [package-lock.json](gravewright/maps/frontend/package-lock.json), incluindo 26 builds opcionais do esbuild por plataforma. O [inventário do bundle](gravewright/maps/static/gravewright_maps/vendor/packages.json) identifica oito pacotes usados na compilação dos mapas.
- Diários: todos os **38 pacotes** do [inventário do editor](gravewright/journals/static/gravewright_journals/vendor/packages.json), além do PDF.js e do core-js embutido em seus arquivos.
- Outros materiais: Datastar servido localmente, 247 ícones SVG do Phosphor, avisos preservados da interface original e o modelo de PDF incluído.

Os textos complementares, copiados sem alterações, estão em [LICENSES/third-party](LICENSES/third-party/). [SOURCES.json](LICENSES/third-party/SOURCES.json) registra pacote, versão, origem e hash SHA-256 de cada cópia. Os avisos já existentes ao lado dos arquivos de terceiros foram mantidos. Os links abaixo identificam versões upstream; os identificadores de licença vêm dos metadados e textos das versões correspondentes, não das versões atuais/mais recentes.

## Dependências Python

“Direta” significa dependência de execução em [pyproject.toml](pyproject.toml). “Desenvolvimento” cobre o Playwright e suas dependências Python exclusivas. Os demais pacotes são transitivos; as condições de plataforma ainda determinam o que será instalado. Uma entrada no lock não significa que o código-fonte dessa dependência esteja incorporado ao Gravewright.

| Pacote | Versão | Licença | Papel | Licença e avisos de direitos autorais |
| --- | --- | --- | --- | --- |
| [asgiref](https://pypi.org/project/asgiref/3.12.1/) | 3.12.1 | `BSD-3-Clause` | Transitiva | [asgiref](LICENSES/third-party/python/asgiref/) |
| [attrs](https://pypi.org/project/attrs/26.1.0/) | 26.1.0 | `MIT` | Transitiva | [attrs](LICENSES/third-party/python/attrs/) |
| [autobahn](https://pypi.org/project/autobahn/26.7.1/) | 26.7.1 | `MIT` | Transitiva | [autobahn](LICENSES/third-party/python/autobahn/) |
| [automat](https://pypi.org/project/automat/25.4.16/) | 25.4.16 | `MIT` | Transitiva | [automat](LICENSES/third-party/python/automat/) |
| [cbor2](https://pypi.org/project/cbor2/5.9.0/) | 5.9.0 | `MIT` | Transitiva | [cbor2](LICENSES/third-party/python/cbor2/) |
| [cffi](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | `MIT-0` | Transitiva | [cffi](LICENSES/third-party/python/cffi/) |
| [channels](https://pypi.org/project/channels/4.3.2/) | 4.3.2 | `BSD-3-Clause` | Direta | [channels](LICENSES/third-party/python/channels/) |
| [channels-redis](https://pypi.org/project/channels-redis/4.3.0/) | 4.3.0 | `BSD-3-Clause` | Direta | [channels-redis](LICENSES/third-party/python/channels-redis/) |
| [constantly](https://pypi.org/project/constantly/23.10.4/) | 23.10.4 | `MIT` | Transitiva | [constantly](LICENSES/third-party/python/constantly/) |
| [cryptography](https://pypi.org/project/cryptography/50.0.1/) | 50.0.1 | `Apache-2.0 OR BSD-3-Clause` | Direta | [cryptography](LICENSES/third-party/python/cryptography/) |
| [daphne](https://pypi.org/project/daphne/4.2.3/) | 4.2.3 | `BSD-3-Clause` | Direta | [daphne](LICENSES/third-party/python/daphne/) |
| [datastar-py](https://pypi.org/project/datastar-py/1.0.2/) | 1.0.2 | `MIT` | Direta | [datastar-py](LICENSES/third-party/python/datastar-py/) |
| [django](https://pypi.org/project/django/6.1.1/) | 6.1.1 | `BSD-3-Clause` | Direta | [django](LICENSES/third-party/python/django/) |
| [greenlet](https://pypi.org/project/greenlet/3.5.5/) | 3.5.5 | `MIT AND PSF-2.0` | Desenvolvimento | [greenlet](LICENSES/third-party/python/greenlet/) |
| [hyperlink](https://pypi.org/project/hyperlink/21.0.0/) | 21.0.0 | `MIT` | Transitiva | [hyperlink](LICENSES/third-party/python/hyperlink/) |
| [idna](https://pypi.org/project/idna/3.19/) | 3.19 | `BSD-3-Clause` | Transitiva | [idna](LICENSES/third-party/python/idna/) |
| [incremental](https://pypi.org/project/incremental/24.11.0/) | 24.11.0 | `MIT` | Transitiva | [incremental](LICENSES/third-party/python/incremental/) |
| [jinja2](https://pypi.org/project/jinja2/3.1.6/) | 3.1.6 | `BSD-3-Clause` | Direta | [jinja2](LICENSES/third-party/python/jinja2/) |
| [jsonschema](https://pypi.org/project/jsonschema/4.26.0/) | 4.26.0 | `MIT` | Direta | [jsonschema](LICENSES/third-party/python/jsonschema/) |
| [jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | 2025.9.1 | `MIT` | Transitiva | [jsonschema-specifications](LICENSES/third-party/python/jsonschema-specifications/) |
| [markupsafe](https://pypi.org/project/markupsafe/3.0.3/) | 3.0.3 | `BSD-3-Clause` | Transitiva | [markupsafe](LICENSES/third-party/python/markupsafe/) |
| [msgpack](https://pypi.org/project/msgpack/1.2.2/) | 1.2.2 | `Apache-2.0` | Transitiva | [msgpack](LICENSES/third-party/python/msgpack/) |
| [mutagen](https://pypi.org/project/mutagen/1.48.1/) | 1.48.1 | `GPL-2.0-or-later` | Direta | [mutagen](LICENSES/third-party/python/mutagen/) |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | `Apache-2.0 OR BSD-2-Clause` | Transitiva | [packaging](LICENSES/third-party/python/packaging/) |
| [pillow](https://pypi.org/project/pillow/12.3.0/) | 12.3.0 | `MIT-CMU` | Direta | [pillow](LICENSES/third-party/python/pillow/) |
| [playwright](https://pypi.org/project/playwright/1.62.0/) | 1.62.0 | `Apache-2.0` | Desenvolvimento | [playwright](LICENSES/third-party/python/playwright/) |
| [pycparser](https://pypi.org/project/pycparser/3.0/) | 3.0 | `BSD-3-Clause` | Transitiva | [pycparser](LICENSES/third-party/python/pycparser/) |
| [pyee](https://pypi.org/project/pyee/13.0.1/) | 13.0.1 | `MIT` | Desenvolvimento | [pyee](LICENSES/third-party/python/pyee/) |
| [pyopenssl](https://pypi.org/project/pyopenssl/26.4.0/) | 26.4.0 | `Apache-2.0` | Transitiva | [pyopenssl](LICENSES/third-party/python/pyopenssl/) |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.3/) | 1.2.3 | `BSD-3-Clause` | Direta | [python-dotenv](LICENSES/third-party/python/python-dotenv/) |
| [redis](https://pypi.org/project/redis/8.1.0/) | 8.1.0 | `MIT` | Transitiva | [redis](LICENSES/third-party/python/redis/) |
| [referencing](https://pypi.org/project/referencing/0.37.0/) | 0.37.0 | `MIT` | Transitiva | [referencing](LICENSES/third-party/python/referencing/) |
| [rpds-py](https://pypi.org/project/rpds-py/2026.6.3/) | 2026.6.3 | `MIT` | Transitiva | [rpds-py](LICENSES/third-party/python/rpds-py/) |
| [service-identity](https://pypi.org/project/service-identity/26.1.0/) | 26.1.0 | `MIT` | Transitiva | [service-identity](LICENSES/third-party/python/service-identity/) |
| [sqlparse](https://pypi.org/project/sqlparse/0.6.0/) | 0.6.0 | `BSD-3-Clause` | Transitiva | [sqlparse](LICENSES/third-party/python/sqlparse/) |
| [twisted](https://pypi.org/project/twisted/26.4.0/) | 26.4.0 | `MIT` | Transitiva | [twisted](LICENSES/third-party/python/twisted/) |
| [txaio](https://pypi.org/project/txaio/26.6.1/) | 26.6.1 | `MIT` | Transitiva | [txaio](LICENSES/third-party/python/txaio/) |
| [typing-extensions](https://pypi.org/project/typing-extensions/4.16.0/) | 4.16.0 | `PSF-2.0` | Transitiva | [typing-extensions](LICENSES/third-party/python/typing-extensions/) |
| [tzdata](https://pypi.org/project/tzdata/2026.3/) | 2026.3 | `Apache-2.0` | Transitiva; Windows | [tzdata](LICENSES/third-party/python/tzdata/) |
| [u-msgpack-python](https://pypi.org/project/u-msgpack-python/2.8.0/) | 2.8.0 | `MIT` | Transitiva; não CPython | [u-msgpack-python](LICENSES/third-party/python/u-msgpack-python/) |
| [ujson](https://pypi.org/project/ujson/6.0.0/) | 6.0.0 | `BSD-3-Clause AND TCL` | Transitiva | [ujson](LICENSES/third-party/python/ujson/) |
| [zope-interface](https://pypi.org/project/zope-interface/8.6/) | 8.6 | `ZPL-2.1` | Transitiva | [zope-interface](LICENSES/third-party/python/zope-interface/) |

Django, Channels, Daphne e channels-redis fornecem a infraestrutura HTTP, ASGI e de tempo real; o SDK Python do Datastar produz respostas conduzidas pelo servidor; Jinja2 renderiza templates. Cryptography verifica metadados assinados de módulos, JSON Schema valida contratos de módulos, Mutagen lê metadados de áudio e Pillow processa imagens. python-dotenv carrega a configuração. Playwright é uma ferramenta de desenvolvimento para verificações no navegador.

Termos upstream específicos que devem acompanhar os pacotes redistribuídos:

- **Mutagen** concede `GPL-2.0-or-later`; seu aviso no código permite expressamente versões posteriores da GPL. Preserve o [aviso](LICENSES/third-party/python/mutagen/SOURCE-NOTICE.txt) e o [texto da GPL](LICENSES/third-party/python/mutagen/COPYING). Uma permissão concedida a módulos do Gravewright não concede exceções aos termos do Mutagen nem de outra dependência.
- **Cryptography** e **packaging** oferecem licenças alternativas (`OR`); **greenlet** e **ujson** identificam múltiplas licenças aplicáveis (`AND`). Os diretórios indicados preservam esses textos sem escolher ou descartar licenças.
- **Pillow** usa `MIT-CMU` para o código da Python Imaging Library. O [LICENSE completo do wheel instalado](LICENSES/third-party/python/pillow/LICENSE) também contém avisos de bibliotecas de imagem/compressão incluídas. A licença principal da tabela não é um inventário de cada codec nativo.
- **Django** inclui avisos do código derivado de Python, da implementação de sinais, de wrappers GIS e dos arquivos do admin (jQuery, Select2 e XRegExp). As cópias no [diretório de avisos](LICENSES/third-party/python/django/) preservam esses textos adicionais.
- **Playwright** inclui um driver Node.js e componentes adicionais com avisos próprios. Seus [arquivos de licença e avisos instalados](LICENSES/third-party/python/playwright/) estão incluídos. Os binários de navegadores baixados são distribuições separadas e estão fora deste inventário de código.
- **tzdata** é a distribuição Python de dados de fuso horário; seu texto Apache acompanha o wheel. Sua presença neste lock depende do uso de Windows.

## Bibliotecas de navegador incluídas no repositório

### Datastar

[Datastar 1.0.3](https://github.com/starfederation/datastar/tree/v1.0.3) é servido por [datastar-1.0.3.js](gravewright/web/static/gravewright_web/vendor/datastar-1.0.3.js), sob a **licença MIT**. A [licença local](gravewright/web/static/gravewright_web/vendor/DATASTAR-LICENSE.md) e o [README do fornecedor](gravewright/web/static/gravewright_web/vendor/README.md) preservam a URL de origem e os detalhes da cópia. É um componente separado do pacote Python `datastar-py`.

### Renderização de mapas

A compilação atual dos mapas registra estas bibliotecas. Suas funções incluem renderização PixiJS, eventos, conversão de cores, triangulação, detecção de dispositivos móveis, leitura de SVG, cache e leitura de XML.

| Pacote | Versão | Licença | Aviso |
| --- | --- | --- | --- |
| [pixi.js](https://www.npmjs.com/package/pixi.js/v/8.20.1) | 8.20.1 | `MIT` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/pixi.js-LICENSE) |
| [eventemitter3](https://www.npmjs.com/package/eventemitter3/v/5.0.4) | 5.0.4 | `MIT` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/eventemitter3-LICENSE) |
| [@pixi/colord](https://www.npmjs.com/package/@pixi/colord/v/2.9.6) | 2.9.6 | `MIT` | [Texto](LICENSES/third-party/javascript/@pixi_colord/LICENSE.md) |
| [earcut](https://www.npmjs.com/package/earcut/v/3.2.3) | 3.2.3 | `ISC` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/earcut-LICENSE) |
| [ismobilejs](https://www.npmjs.com/package/ismobilejs/v/1.1.1) | 1.1.1 | `MIT` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/ismobilejs-LICENSE) |
| [parse-svg-path](https://www.npmjs.com/package/parse-svg-path/v/0.2.0) | 0.2.0 | `MIT` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/parse-svg-path-LICENSE) |
| [tiny-lru](https://www.npmjs.com/package/tiny-lru/v/11.4.7) | 11.4.7 | `BSD-3-Clause` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/tiny-lru-LICENSE) |
| [@xmldom/xmldom](https://www.npmjs.com/package/@xmldom/xmldom/v/0.8.15) | 0.8.15 | `MIT` | [Texto](gravewright/maps/static/gravewright_maps/vendor/licenses/@xmldom_xmldom-LICENSE) |

O pacote publicado de `@pixi/colord` não incluía um arquivo de licença na raiz para o script de compilação copiar. O texto ausente foi preservado a partir da [licença upstream v2.9.6](https://github.com/PixiJS/colord/blob/v2.9.6/LICENSE.md).

O lock npm também contém os pacotes abaixo, que o inventário atual **não** lista como código de execução incluído no bundle. Preserve seus avisos ao redistribuir a árvore de dependências de desenvolvimento:

| Pacote | Versão | Licença | Aviso |
| --- | --- | --- | --- |
| [@types/earcut](https://www.npmjs.com/package/@types/earcut/v/3.0.0) | 3.0.0 | `MIT` | [Texto](LICENSES/third-party/javascript/@types_earcut/) |
| [@webgpu/types](https://www.npmjs.com/package/@webgpu/types/v/0.1.72) | 0.1.72 | `BSD-3-Clause` | [Texto](LICENSES/third-party/javascript/@webgpu_types/) |
| [esbuild](https://www.npmjs.com/package/esbuild/v/0.28.2) | 0.28.2 | `MIT` | [Texto](LICENSES/third-party/javascript/esbuild/) |
| [gifuct-js](https://www.npmjs.com/package/gifuct-js/v/2.1.2) | 2.1.2 | `MIT` | [Texto](LICENSES/third-party/javascript/gifuct-js/) |
| [js-binary-schema-parser](https://www.npmjs.com/package/js-binary-schema-parser/v/2.0.3) | 2.0.3 | `MIT` | [Texto](LICENSES/third-party/javascript/js-binary-schema-parser/) |

Os **26** pacotes `@esbuild/*` abaixo estão fixados em **0.28.2**, marcados como dependências opcionais/de desenvolvimento e declaram **MIT** no lock npm. O [texto da licença](LICENSES/third-party/javascript/esbuild/LICENSE.md) foi preservado; normalmente o npm instala somente o pacote correspondente à máquina de compilação.

`@esbuild/aix-ppc64`, `@esbuild/android-arm`, `@esbuild/android-arm64`, `@esbuild/android-x64`, `@esbuild/darwin-arm64`, `@esbuild/darwin-x64`, `@esbuild/freebsd-arm64`, `@esbuild/freebsd-x64`, `@esbuild/linux-arm`, `@esbuild/linux-arm64`, `@esbuild/linux-ia32`, `@esbuild/linux-loong64`, `@esbuild/linux-mips64el`, `@esbuild/linux-ppc64`, `@esbuild/linux-riscv64`, `@esbuild/linux-s390x`, `@esbuild/linux-x64`, `@esbuild/netbsd-arm64`, `@esbuild/netbsd-x64`, `@esbuild/openbsd-arm64`, `@esbuild/openbsd-x64`, `@esbuild/openharmony-arm64`, `@esbuild/sunos-x64`, `@esbuild/win32-arm64`, `@esbuild/win32-ia32`, `@esbuild/win32-x64`.

### Editor de texto rico dos diários

O editor de diários usa Tiptap e ProseMirror. O inventário do bundle declara todos os pacotes abaixo como MIT. A [licença compartilhada do Tiptap v2.11.5](https://github.com/ueberdosis/tiptap/blob/v2.11.5/LICENSE.md), copyright 2025 Tiptap GmbH, está preservada localmente para os pacotes `@tiptap/*`.

| Pacote | Versão | Licença | Aviso |
| --- | --- | --- | --- |
| [orderedmap](https://www.npmjs.com/package/orderedmap/v/2.1.1) | 2.1.1 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/orderedmap-LICENSE) |
| [prosemirror-model](https://www.npmjs.com/package/prosemirror-model/v/1.25.11) | 1.25.11 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-model-LICENSE) |
| [prosemirror-transform](https://www.npmjs.com/package/prosemirror-transform/v/1.12.1) | 1.12.1 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-transform-LICENSE) |
| [prosemirror-state](https://www.npmjs.com/package/prosemirror-state/v/1.4.4) | 1.4.4 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-state-LICENSE) |
| [@tiptap/pm](https://www.npmjs.com/package/@tiptap/pm/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-view](https://www.npmjs.com/package/prosemirror-view/v/1.42.3) | 1.42.3 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-view-LICENSE) |
| [w3c-keyname](https://www.npmjs.com/package/w3c-keyname/v/2.2.8) | 2.2.8 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/w3c-keyname-LICENSE) |
| [prosemirror-keymap](https://www.npmjs.com/package/prosemirror-keymap/v/1.2.3) | 1.2.3 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-keymap-LICENSE) |
| [prosemirror-commands](https://www.npmjs.com/package/prosemirror-commands/v/1.7.2) | 1.7.2 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-commands-LICENSE) |
| [prosemirror-schema-list](https://www.npmjs.com/package/prosemirror-schema-list/v/1.5.1) | 1.5.1 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-schema-list-LICENSE) |
| [@tiptap/core](https://www.npmjs.com/package/@tiptap/core/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-blockquote](https://www.npmjs.com/package/@tiptap/extension-blockquote/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-bold](https://www.npmjs.com/package/@tiptap/extension-bold/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-bullet-list](https://www.npmjs.com/package/@tiptap/extension-bullet-list/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-code](https://www.npmjs.com/package/@tiptap/extension-code/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-code-block](https://www.npmjs.com/package/@tiptap/extension-code-block/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-document](https://www.npmjs.com/package/@tiptap/extension-document/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-dropcursor](https://www.npmjs.com/package/prosemirror-dropcursor/v/1.8.3) | 1.8.3 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-dropcursor-LICENSE) |
| [@tiptap/extension-dropcursor](https://www.npmjs.com/package/@tiptap/extension-dropcursor/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-gapcursor](https://www.npmjs.com/package/prosemirror-gapcursor/v/1.4.1) | 1.4.1 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-gapcursor-LICENSE) |
| [@tiptap/extension-gapcursor](https://www.npmjs.com/package/@tiptap/extension-gapcursor/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-hard-break](https://www.npmjs.com/package/@tiptap/extension-hard-break/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-heading](https://www.npmjs.com/package/@tiptap/extension-heading/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [rope-sequence](https://www.npmjs.com/package/rope-sequence/v/1.3.4) | 1.3.4 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/rope-sequence-LICENSE) |
| [prosemirror-history](https://www.npmjs.com/package/prosemirror-history/v/1.5.0) | 1.5.0 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-history-LICENSE) |
| [@tiptap/extension-history](https://www.npmjs.com/package/@tiptap/extension-history/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-horizontal-rule](https://www.npmjs.com/package/@tiptap/extension-horizontal-rule/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-italic](https://www.npmjs.com/package/@tiptap/extension-italic/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-list-item](https://www.npmjs.com/package/@tiptap/extension-list-item/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-ordered-list](https://www.npmjs.com/package/@tiptap/extension-ordered-list/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-paragraph](https://www.npmjs.com/package/@tiptap/extension-paragraph/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-strike](https://www.npmjs.com/package/@tiptap/extension-strike/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-text](https://www.npmjs.com/package/@tiptap/extension-text/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/starter-kit](https://www.npmjs.com/package/@tiptap/starter-kit/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [linkifyjs](https://www.npmjs.com/package/linkifyjs/v/4.3.3) | 4.3.3 | `MIT` | [Texto](gravewright/journals/static/gravewright_journals/vendor/licenses/linkifyjs-LICENSE) |
| [@tiptap/extension-link](https://www.npmjs.com/package/@tiptap/extension-link/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-placeholder](https://www.npmjs.com/package/@tiptap/extension-placeholder/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/suggestion](https://www.npmjs.com/package/@tiptap/suggestion/v/2.11.5) | 2.11.5 | `MIT` | [Texto](LICENSES/third-party/javascript/tiptap/LICENSE.md) |

### PDF.js e core-js embutido

Os cabeçalhos de [pdf.mjs](gravewright/journals/static/gravewright_journals/vendor/pdf.mjs) e [pdf.worker.mjs](gravewright/journals/static/gravewright_journals/vendor/pdf.worker.mjs) identificam **PDF.js 6.2.108**, build **0365cbde0**, copyright 2024 Mozilla Foundation, sob **Apache-2.0**. O texto completo está em [PDFJS-LICENSE](gravewright/journals/static/gravewright_journals/vendor/PDFJS-LICENSE); o projeto upstream é [mozilla/pdf.js](https://github.com/mozilla/pdf.js).

Ambos os arquivos também contêm **core-js 3.49.0**, que identifica sua versão, direitos autorais e URL da licença MIT no bundle. A [licença upstream](https://github.com/zloirock/core-js/blob/v3.49.0/LICENSE) foi copiada para [LICENSES/third-party/javascript/core-js/LICENSE](LICENSES/third-party/javascript/core-js/LICENSE). Esse aviso MIT complementar deve acompanhar o código embutido junto ao aviso Apache do PDF.js.

## Ícones, fontes, modelos e interface reutilizada

| Material | Evidências e termos |
| --- | --- |
| Ícones Phosphor | **247 SVGs** em [gravewright/web/icons](gravewright/web/icons/), com a [licença MIT original](gravewright/web/icons/LICENSE), copyright 2020 Phosphor Icons. O aviso identifica o [projeto upstream](https://github.com/phosphor-icons/core); a versão/commit importado não está registrado localmente. |
| Interface original Gravewright | [ORIGINAL-NOTICE](gravewright/web/static/gravewright_web/ORIGINAL-NOTICE) atribui “Gravewright Vue frontend and UI components”, copyright 2026 Gravewright contributors, e registra a adaptação de um checkout local anterior. O [texto Apache-2.0](gravewright/web/static/gravewright_web/ORIGINAL-LICENSE) foi mantido. O aviso não registra URL pública nem revisão exata da origem. |
| Ícone do executor Windows | [gravewright.ico](scripts/windows/gravewright.ico) converte o símbolo CSS existente em tamanhos de ícone Windows. A [nota de origem e licença](scripts/windows/ICON-NOTICE.md) preserva a atribuição da interface original e os termos Apache-2.0. |
| Fontes | O CSS usa nomes de fontes do sistema e alternativas; não foram encontrados binários de fontes nem folhas de estilo remotas de webfonts na árvore da aplicação. Mencionar uma fonte do sistema não significa distribuir seu arquivo. |
| PDF incluído | [blank-a4.pdf](gravewright/pdf_system/static/gravewright_pdf_system/assets/blank-a4.pdf) contém instruções do Gravewright e referencia a fonte padrão PDF Helvetica; não incorpora um binário de fonte. O arquivo não traz atribuição separada a terceiros. |
| Conteúdo do usuário | Mapas, imagens, sons, músicas, PDFs e conteúdo de campanhas/módulos enviados são fornecidos durante a execução. Seus direitos e permissões não são inferidos da licença do Gravewright nem deste inventário. Não foram encontrados arquivos independentes de imagem raster, áudio ou fonte nos fontes da aplicação fora dos dados ignorados de execução. |

## Downloads do executor Windows

O [Gravewright Runner](docs/pt-BR/windows-runner.md) reaproveita uv, Python e Node.js/npm compatíveis instalados. Quando falta uma ferramenta compatível, baixa uma alternativa para a pasta local de dados da aplicação do usuário; esses executáveis não estão incluídos neste arquivo de código-fonte. O download alternativo do **uv 0.12.13** e o executável em cache são verificados. Essa versão do uv está disponível sob **Apache-2.0 OR MIT**; consulte seus textos [Apache](https://github.com/astral-sh/uv/blob/0.12.13/LICENSE-APACHE) e [MIT](https://github.com/astral-sh/uv/blob/0.12.13/LICENSE-MIT). Instalações reaproveitadas mantêm os avisos de suas versões efetivas.

O launcher em lote usa CMD, `curl.exe`, `tar.exe` e `certutil.exe` fornecidos pelo Windows em seu fluxo de instalação. Essas ferramentas do sistema não são redistribuídas neste arquivo de código-fonte. O helper do atalho usa a biblioteca padrão do Python e as interfaces COM do Windows; não acrescenta dependência de pacote Python.

O executor usa um interpretador **CPython 3.14** compatível instalado quando disponível. Caso contrário, o uv baixa uma compilação gerenciada do [python-build-standalone](https://docs.astral.sh/uv/concepts/python-versions/#cpython-distributions). O Python e suas bibliotecas nativas incluídas possuem avisos próprios, além do [histórico de licenças e termos do Python](https://docs.python.org/3.14/license.html). O patch/build do interpretador segue a instalação selecionada ou a disponibilidade de ambientes gerenciados pelo uv; não é uma entrada de pacote Python no `uv.lock`. As dependências Python da aplicação continuam fixadas nesse lock, com as dependências Python de desenvolvimento excluídas da instalação normal do executor.

A alternativa Node é a [distribuição oficial Node.js 24.19.0 para Windows x64](https://nodejs.org/en/download/archive/v24.19.0), que inclui **npm 11.17.0**. O [arquivo de licenças do Node](https://github.com/nodejs/node/blob/v24.19.0/LICENSE) cobre o Node e seus componentes incluídos; o [arquivo de licenças do npm](https://github.com/nodejs/node/blob/v24.19.0/deps/npm/LICENSE) identifica **Artistic-2.0** para o próprio npm e termos separados para suas dependências. Essas dependências das ferramentas são distintas do `package-lock.json` dos mapas do Gravewright. A preparação do frontend pelo executor instala as dependências do lock dos mapas, incluindo esbuild, e executa o build existente que coleta seus avisos de terceiros.

Ao redistribuir uma pasta do executor já instalada ou um pacote de ambiente offline, preserve os arquivos efetivos de licença/avisos do uv, Python, Node.js, npm e pacotes instalados e as informações aplicáveis de distribuição de código-fonte. Este inventário da árvore de código, isoladamente, não inventaria todos os avisos dessas distribuições binárias baixadas ou reaproveitadas.

## Limites do inventário e manutenção de versões

Este documento inventaria a árvore de código e os avisos dos pacotes; não afirma que toda instalação possível ou módulo futuro tenha sido auditado. Em particular:

1. O editor existente é um snapshot pré-compilado com uma lista de pacotes; este checkout não contém seu lock npm dedicado nem um processo completo de recompilação do editor. O snapshot Phosphor e a adaptação da interface original também não registram revisões exatas.
2. O diretório vendor dos mapas contém chunks com hashes de várias compilações. Seu inventário descreve a compilação atual registrada, não uma origem individual para cada chunk remanescente. Revise os arquivos efetivamente distribuídos ao preparar uma versão.
3. O **servidor** Redis é configurado externamente e não é a mesma distribuição que o cliente Python `redis`, licenciado sob MIT. Este repositório não seleciona versão, imagem de contêiner nem licença do servidor Redis. Python, Node.js, bibliotecas do sistema operacional, navegadores baixados separadamente e binários nativos por plataforma também precisam dos avisos das versões efetivamente distribuídas.
4. Os textos Python vieram das distribuições instaladas correspondentes ao lock, além dos dois wheels verificados descritos acima. Um wheel de outra plataforma pode conter bibliotecas nativas e avisos diferentes. Preserve as informações completas da distribuição upstream ao empacotá-lo.
5. Módulos de terceiros continuam sujeitos às próprias licenças. Preserve e revise seus avisos ao empacotá-los; este documento não altera suas licenças nem substitui os termos de código copiado para eles.

Ao alterar dependências ou arquivos de terceiros, atualize os dois idiomas, preserve os arquivos upstream de licença/direitos autorais/NOTICE, atualize o lock ou `packages.json` do bundle e registre a origem de novas cópias em `SOURCES.json`. Ao distribuir builds compilados ou empacotados, inclua os textos aplicáveis e cumpra as obrigações de código-fonte dos componentes efetivamente distribuídos. Inclua este arquivo, sua versão inglesa, os avisos existentes de fornecedores e o diretório complementar `LICENSES/third-party` nos arquivos de lançamento.
