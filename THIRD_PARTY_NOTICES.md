# Third-party notices

[Português (Brasil)](THIRD_PARTY_NOTICES.pt-BR.md) · [Project license](LICENSE)

This inventory describes the dependencies and bundled material present in the source tree reviewed on **2026-09-11**. Gravewright's project license does not replace third-party licenses. Copyright, attribution, source-distribution and other conditions attached to those components remain applicable. License texts are preserved in their original language; the Portuguese document translates the explanatory inventory only.

## Evidence and coverage

- Python: all **42 third-party packages** in [uv.lock](uv.lock), including direct, transitive, development and platform-conditional dependencies. Forty installed distributions matched the locked versions exactly. The `tzdata` and `u-msgpack-python` wheels were downloaded from the URLs in the lock and verified against its SHA-256 hashes; neither package had to be installed.
- Maps: all **39 npm dependencies** in [package-lock.json](gravewright/maps/frontend/package-lock.json), including 26 optional platform builds of esbuild. The [bundled package inventory](gravewright/maps/static/gravewright_maps/vendor/packages.json) identifies eight packages used by the map build.
- Journals: all **38 packages** in the [editor bundle inventory](gravewright/journals/static/gravewright_journals/vendor/packages.json), plus PDF.js and the core-js code embedded in its files.
- Other material: locally served Datastar, 247 Phosphor SVG icons, retained original-frontend notices and the built-in PDF template.

The verbatim supplementary texts are under [LICENSES/third-party](LICENSES/third-party/). [SOURCES.json](LICENSES/third-party/SOURCES.json) records each copied file's package, version, source and SHA-256 hash. Existing notices beside vendor files remain in place. Package links below identify upstream releases; license identifiers come from the matching package metadata and accompanying texts, rather than from current/latest releases.

## Python dependencies

“Direct” means a runtime dependency in [pyproject.toml](pyproject.toml). “Development” covers Playwright and its exclusive Python dependencies. Other packages are transitive; marker conditions still determine what is installed on a particular platform. A lock entry does not mean that the dependency's source code is vendored in Gravewright.

| Package | Version | License | Role | License and copyright notices |
| --- | --- | --- | --- | --- |
| [asgiref](https://pypi.org/project/asgiref/3.12.1/) | 3.12.1 | `BSD-3-Clause` | Transitive | [asgiref](LICENSES/third-party/python/asgiref/) |
| [attrs](https://pypi.org/project/attrs/26.1.0/) | 26.1.0 | `MIT` | Transitive | [attrs](LICENSES/third-party/python/attrs/) |
| [autobahn](https://pypi.org/project/autobahn/26.7.1/) | 26.7.1 | `MIT` | Transitive | [autobahn](LICENSES/third-party/python/autobahn/) |
| [automat](https://pypi.org/project/automat/25.4.16/) | 25.4.16 | `MIT` | Transitive | [automat](LICENSES/third-party/python/automat/) |
| [cbor2](https://pypi.org/project/cbor2/5.9.0/) | 5.9.0 | `MIT` | Transitive | [cbor2](LICENSES/third-party/python/cbor2/) |
| [cffi](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | `MIT-0` | Transitive | [cffi](LICENSES/third-party/python/cffi/) |
| [channels](https://pypi.org/project/channels/4.3.2/) | 4.3.2 | `BSD-3-Clause` | Direct | [channels](LICENSES/third-party/python/channels/) |
| [channels-redis](https://pypi.org/project/channels-redis/4.3.0/) | 4.3.0 | `BSD-3-Clause` | Direct | [channels-redis](LICENSES/third-party/python/channels-redis/) |
| [constantly](https://pypi.org/project/constantly/23.10.4/) | 23.10.4 | `MIT` | Transitive | [constantly](LICENSES/third-party/python/constantly/) |
| [cryptography](https://pypi.org/project/cryptography/50.0.1/) | 50.0.1 | `Apache-2.0 OR BSD-3-Clause` | Direct | [cryptography](LICENSES/third-party/python/cryptography/) |
| [daphne](https://pypi.org/project/daphne/4.2.3/) | 4.2.3 | `BSD-3-Clause` | Direct | [daphne](LICENSES/third-party/python/daphne/) |
| [datastar-py](https://pypi.org/project/datastar-py/1.0.2/) | 1.0.2 | `MIT` | Direct | [datastar-py](LICENSES/third-party/python/datastar-py/) |
| [django](https://pypi.org/project/django/6.1.1/) | 6.1.1 | `BSD-3-Clause` | Direct | [django](LICENSES/third-party/python/django/) |
| [greenlet](https://pypi.org/project/greenlet/3.5.5/) | 3.5.5 | `MIT AND PSF-2.0` | Development | [greenlet](LICENSES/third-party/python/greenlet/) |
| [hyperlink](https://pypi.org/project/hyperlink/21.0.0/) | 21.0.0 | `MIT` | Transitive | [hyperlink](LICENSES/third-party/python/hyperlink/) |
| [idna](https://pypi.org/project/idna/3.19/) | 3.19 | `BSD-3-Clause` | Transitive | [idna](LICENSES/third-party/python/idna/) |
| [incremental](https://pypi.org/project/incremental/24.11.0/) | 24.11.0 | `MIT` | Transitive | [incremental](LICENSES/third-party/python/incremental/) |
| [jinja2](https://pypi.org/project/jinja2/3.1.6/) | 3.1.6 | `BSD-3-Clause` | Direct | [jinja2](LICENSES/third-party/python/jinja2/) |
| [jsonschema](https://pypi.org/project/jsonschema/4.26.0/) | 4.26.0 | `MIT` | Direct | [jsonschema](LICENSES/third-party/python/jsonschema/) |
| [jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | 2025.9.1 | `MIT` | Transitive | [jsonschema-specifications](LICENSES/third-party/python/jsonschema-specifications/) |
| [markupsafe](https://pypi.org/project/markupsafe/3.0.3/) | 3.0.3 | `BSD-3-Clause` | Transitive | [markupsafe](LICENSES/third-party/python/markupsafe/) |
| [msgpack](https://pypi.org/project/msgpack/1.2.2/) | 1.2.2 | `Apache-2.0` | Transitive | [msgpack](LICENSES/third-party/python/msgpack/) |
| [mutagen](https://pypi.org/project/mutagen/1.48.1/) | 1.48.1 | `GPL-2.0-or-later` | Direct | [mutagen](LICENSES/third-party/python/mutagen/) |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | `Apache-2.0 OR BSD-2-Clause` | Transitive | [packaging](LICENSES/third-party/python/packaging/) |
| [pillow](https://pypi.org/project/pillow/12.3.0/) | 12.3.0 | `MIT-CMU` | Direct | [pillow](LICENSES/third-party/python/pillow/) |
| [playwright](https://pypi.org/project/playwright/1.62.0/) | 1.62.0 | `Apache-2.0` | Development | [playwright](LICENSES/third-party/python/playwright/) |
| [pycparser](https://pypi.org/project/pycparser/3.0/) | 3.0 | `BSD-3-Clause` | Transitive | [pycparser](LICENSES/third-party/python/pycparser/) |
| [pyee](https://pypi.org/project/pyee/13.0.1/) | 13.0.1 | `MIT` | Development | [pyee](LICENSES/third-party/python/pyee/) |
| [pyopenssl](https://pypi.org/project/pyopenssl/26.4.0/) | 26.4.0 | `Apache-2.0` | Transitive | [pyopenssl](LICENSES/third-party/python/pyopenssl/) |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.3/) | 1.2.3 | `BSD-3-Clause` | Direct | [python-dotenv](LICENSES/third-party/python/python-dotenv/) |
| [redis](https://pypi.org/project/redis/8.1.0/) | 8.1.0 | `MIT` | Transitive | [redis](LICENSES/third-party/python/redis/) |
| [referencing](https://pypi.org/project/referencing/0.37.0/) | 0.37.0 | `MIT` | Transitive | [referencing](LICENSES/third-party/python/referencing/) |
| [rpds-py](https://pypi.org/project/rpds-py/2026.6.3/) | 2026.6.3 | `MIT` | Transitive | [rpds-py](LICENSES/third-party/python/rpds-py/) |
| [service-identity](https://pypi.org/project/service-identity/26.1.0/) | 26.1.0 | `MIT` | Transitive | [service-identity](LICENSES/third-party/python/service-identity/) |
| [sqlparse](https://pypi.org/project/sqlparse/0.6.0/) | 0.6.0 | `BSD-3-Clause` | Transitive | [sqlparse](LICENSES/third-party/python/sqlparse/) |
| [twisted](https://pypi.org/project/twisted/26.4.0/) | 26.4.0 | `MIT` | Transitive | [twisted](LICENSES/third-party/python/twisted/) |
| [txaio](https://pypi.org/project/txaio/26.6.1/) | 26.6.1 | `MIT` | Transitive | [txaio](LICENSES/third-party/python/txaio/) |
| [typing-extensions](https://pypi.org/project/typing-extensions/4.16.0/) | 4.16.0 | `PSF-2.0` | Transitive | [typing-extensions](LICENSES/third-party/python/typing-extensions/) |
| [tzdata](https://pypi.org/project/tzdata/2026.3/) | 2026.3 | `Apache-2.0` | Transitive; Windows | [tzdata](LICENSES/third-party/python/tzdata/) |
| [u-msgpack-python](https://pypi.org/project/u-msgpack-python/2.8.0/) | 2.8.0 | `MIT` | Transitive; non-CPython | [u-msgpack-python](LICENSES/third-party/python/u-msgpack-python/) |
| [ujson](https://pypi.org/project/ujson/6.0.0/) | 6.0.0 | `BSD-3-Clause AND TCL` | Transitive | [ujson](LICENSES/third-party/python/ujson/) |
| [zope-interface](https://pypi.org/project/zope-interface/8.6/) | 8.6 | `ZPL-2.1` | Transitive | [zope-interface](LICENSES/third-party/python/zope-interface/) |

Django, Channels, Daphne and channels-redis provide HTTP, ASGI and realtime infrastructure; Datastar's Python SDK creates server-driven responses; Jinja2 renders templates. Cryptography verifies signed module metadata, JSON Schema validates module contracts, Mutagen reads audio metadata, and Pillow processes images. python-dotenv loads configuration. Playwright is a development tool for browser checks.

Specific upstream terms worth retaining with redistributed packages:

- **Mutagen** grants `GPL-2.0-or-later`; its accompanying source notice explicitly permits later GPL versions. Preserve its own [notice](LICENSES/third-party/python/mutagen/SOURCE-NOTICE.txt) and [GPL text](LICENSES/third-party/python/mutagen/COPYING). A permission granted for Gravewright modules does not grant exceptions to Mutagen's or any other dependency's terms.
- **Cryptography** and **packaging** offer alternative licenses (`OR`); **greenlet** and **ujson** identify multiple applicable licenses (`AND`). The linked directories retain the accompanying license texts rather than selecting or discarding them.
- **Pillow** uses `MIT-CMU` for its Python Imaging Library code. Its complete [installed-wheel LICENSE](LICENSES/third-party/python/pillow/LICENSE) also contains notices for bundled image/compression libraries. The table's top-level license is not an inventory of every native codec.
- **Django** includes notices for its Python-derived code, dispatch implementation, GIS wrappers and admin assets (jQuery, Select2 and XRegExp). The copies in its [notice directory](LICENSES/third-party/python/django/) retain these additional texts.
- **Playwright** includes a Node.js driver and additional components with their own notices. Their installed [license and notice files](LICENSES/third-party/python/playwright/) are included. Downloaded browser binaries are separate distributions and are outside this source-tree inventory.
- **tzdata** is the Python timezone-data distribution; its Apache license text accompanies the wheel. Its presence in this lock is conditional on Windows.

## Browser libraries included in the repository

### Datastar

[Datastar 1.0.3](https://github.com/starfederation/datastar/tree/v1.0.3) is served from [datastar-1.0.3.js](gravewright/web/static/gravewright_web/vendor/datastar-1.0.3.js) under the **MIT License**. Its [local license](gravewright/web/static/gravewright_web/vendor/DATASTAR-LICENSE.md) and [vendor README](gravewright/web/static/gravewright_web/vendor/README.md) retain the source URL and copying details. It is separate from the `datastar-py` Python package.

### Map rendering

The current map build records these libraries. Their roles include PixiJS rendering, events, color conversion, triangulation, mobile detection, SVG parsing, caching and XML parsing.

| Package | Version | License | Notice |
| --- | --- | --- | --- |
| [pixi.js](https://www.npmjs.com/package/pixi.js/v/8.20.1) | 8.20.1 | `MIT` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/pixi.js-LICENSE) |
| [eventemitter3](https://www.npmjs.com/package/eventemitter3/v/5.0.4) | 5.0.4 | `MIT` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/eventemitter3-LICENSE) |
| [@pixi/colord](https://www.npmjs.com/package/@pixi/colord/v/2.9.6) | 2.9.6 | `MIT` | [Text](LICENSES/third-party/javascript/@pixi_colord/LICENSE.md) |
| [earcut](https://www.npmjs.com/package/earcut/v/3.2.3) | 3.2.3 | `ISC` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/earcut-LICENSE) |
| [ismobilejs](https://www.npmjs.com/package/ismobilejs/v/1.1.1) | 1.1.1 | `MIT` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/ismobilejs-LICENSE) |
| [parse-svg-path](https://www.npmjs.com/package/parse-svg-path/v/0.2.0) | 0.2.0 | `MIT` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/parse-svg-path-LICENSE) |
| [tiny-lru](https://www.npmjs.com/package/tiny-lru/v/11.4.7) | 11.4.7 | `BSD-3-Clause` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/tiny-lru-LICENSE) |
| [@xmldom/xmldom](https://www.npmjs.com/package/@xmldom/xmldom/v/0.8.15) | 0.8.15 | `MIT` | [Text](gravewright/maps/static/gravewright_maps/vendor/licenses/@xmldom_xmldom-LICENSE) |

The published `@pixi/colord` package did not include a root license file for the build script to copy. Its missing text is now preserved from the upstream [v2.9.6 license](https://github.com/PixiJS/colord/blob/v2.9.6/LICENSE.md).

The npm lock also contains these packages, which the current bundled-package inventory does **not** list as emitted runtime code. Keep their notices when redistributing the development dependency tree:

| Package | Version | License | Notice |
| --- | --- | --- | --- |
| [@types/earcut](https://www.npmjs.com/package/@types/earcut/v/3.0.0) | 3.0.0 | `MIT` | [Text](LICENSES/third-party/javascript/@types_earcut/) |
| [@webgpu/types](https://www.npmjs.com/package/@webgpu/types/v/0.1.72) | 0.1.72 | `BSD-3-Clause` | [Text](LICENSES/third-party/javascript/@webgpu_types/) |
| [esbuild](https://www.npmjs.com/package/esbuild/v/0.28.2) | 0.28.2 | `MIT` | [Text](LICENSES/third-party/javascript/esbuild/) |
| [gifuct-js](https://www.npmjs.com/package/gifuct-js/v/2.1.2) | 2.1.2 | `MIT` | [Text](LICENSES/third-party/javascript/gifuct-js/) |
| [js-binary-schema-parser](https://www.npmjs.com/package/js-binary-schema-parser/v/2.0.3) | 2.0.3 | `MIT` | [Text](LICENSES/third-party/javascript/js-binary-schema-parser/) |

All **26** `@esbuild/*` platform packages below are locked to **0.28.2**, marked development/optional dependencies, and declare **MIT** in the npm lock. The esbuild [license text](LICENSES/third-party/javascript/esbuild/LICENSE.md) is retained; normally npm installs only the package matching the build host.

`@esbuild/aix-ppc64`, `@esbuild/android-arm`, `@esbuild/android-arm64`, `@esbuild/android-x64`, `@esbuild/darwin-arm64`, `@esbuild/darwin-x64`, `@esbuild/freebsd-arm64`, `@esbuild/freebsd-x64`, `@esbuild/linux-arm`, `@esbuild/linux-arm64`, `@esbuild/linux-ia32`, `@esbuild/linux-loong64`, `@esbuild/linux-mips64el`, `@esbuild/linux-ppc64`, `@esbuild/linux-riscv64`, `@esbuild/linux-s390x`, `@esbuild/linux-x64`, `@esbuild/netbsd-arm64`, `@esbuild/netbsd-x64`, `@esbuild/openbsd-arm64`, `@esbuild/openbsd-x64`, `@esbuild/openharmony-arm64`, `@esbuild/sunos-x64`, `@esbuild/win32-arm64`, `@esbuild/win32-ia32`, `@esbuild/win32-x64`.

### Journal rich-text editor

The journal editor uses Tiptap and ProseMirror. The bundled inventory reports every package below as MIT. Tiptap's shared [v2.11.5 license](https://github.com/ueberdosis/tiptap/blob/v2.11.5/LICENSE.md), copyright 2025 Tiptap GmbH, is preserved locally for the `@tiptap/*` packages.

| Package | Version | License | Notice |
| --- | --- | --- | --- |
| [orderedmap](https://www.npmjs.com/package/orderedmap/v/2.1.1) | 2.1.1 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/orderedmap-LICENSE) |
| [prosemirror-model](https://www.npmjs.com/package/prosemirror-model/v/1.25.11) | 1.25.11 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-model-LICENSE) |
| [prosemirror-transform](https://www.npmjs.com/package/prosemirror-transform/v/1.12.1) | 1.12.1 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-transform-LICENSE) |
| [prosemirror-state](https://www.npmjs.com/package/prosemirror-state/v/1.4.4) | 1.4.4 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-state-LICENSE) |
| [@tiptap/pm](https://www.npmjs.com/package/@tiptap/pm/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-view](https://www.npmjs.com/package/prosemirror-view/v/1.42.3) | 1.42.3 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-view-LICENSE) |
| [w3c-keyname](https://www.npmjs.com/package/w3c-keyname/v/2.2.8) | 2.2.8 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/w3c-keyname-LICENSE) |
| [prosemirror-keymap](https://www.npmjs.com/package/prosemirror-keymap/v/1.2.3) | 1.2.3 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-keymap-LICENSE) |
| [prosemirror-commands](https://www.npmjs.com/package/prosemirror-commands/v/1.7.2) | 1.7.2 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-commands-LICENSE) |
| [prosemirror-schema-list](https://www.npmjs.com/package/prosemirror-schema-list/v/1.5.1) | 1.5.1 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-schema-list-LICENSE) |
| [@tiptap/core](https://www.npmjs.com/package/@tiptap/core/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-blockquote](https://www.npmjs.com/package/@tiptap/extension-blockquote/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-bold](https://www.npmjs.com/package/@tiptap/extension-bold/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-bullet-list](https://www.npmjs.com/package/@tiptap/extension-bullet-list/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-code](https://www.npmjs.com/package/@tiptap/extension-code/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-code-block](https://www.npmjs.com/package/@tiptap/extension-code-block/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-document](https://www.npmjs.com/package/@tiptap/extension-document/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-dropcursor](https://www.npmjs.com/package/prosemirror-dropcursor/v/1.8.3) | 1.8.3 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-dropcursor-LICENSE) |
| [@tiptap/extension-dropcursor](https://www.npmjs.com/package/@tiptap/extension-dropcursor/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [prosemirror-gapcursor](https://www.npmjs.com/package/prosemirror-gapcursor/v/1.4.1) | 1.4.1 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-gapcursor-LICENSE) |
| [@tiptap/extension-gapcursor](https://www.npmjs.com/package/@tiptap/extension-gapcursor/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-hard-break](https://www.npmjs.com/package/@tiptap/extension-hard-break/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-heading](https://www.npmjs.com/package/@tiptap/extension-heading/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [rope-sequence](https://www.npmjs.com/package/rope-sequence/v/1.3.4) | 1.3.4 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/rope-sequence-LICENSE) |
| [prosemirror-history](https://www.npmjs.com/package/prosemirror-history/v/1.5.0) | 1.5.0 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/prosemirror-history-LICENSE) |
| [@tiptap/extension-history](https://www.npmjs.com/package/@tiptap/extension-history/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-horizontal-rule](https://www.npmjs.com/package/@tiptap/extension-horizontal-rule/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-italic](https://www.npmjs.com/package/@tiptap/extension-italic/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-list-item](https://www.npmjs.com/package/@tiptap/extension-list-item/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-ordered-list](https://www.npmjs.com/package/@tiptap/extension-ordered-list/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-paragraph](https://www.npmjs.com/package/@tiptap/extension-paragraph/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-strike](https://www.npmjs.com/package/@tiptap/extension-strike/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-text](https://www.npmjs.com/package/@tiptap/extension-text/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/starter-kit](https://www.npmjs.com/package/@tiptap/starter-kit/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [linkifyjs](https://www.npmjs.com/package/linkifyjs/v/4.3.3) | 4.3.3 | `MIT` | [Text](gravewright/journals/static/gravewright_journals/vendor/licenses/linkifyjs-LICENSE) |
| [@tiptap/extension-link](https://www.npmjs.com/package/@tiptap/extension-link/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/extension-placeholder](https://www.npmjs.com/package/@tiptap/extension-placeholder/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |
| [@tiptap/suggestion](https://www.npmjs.com/package/@tiptap/suggestion/v/2.11.5) | 2.11.5 | `MIT` | [Text](LICENSES/third-party/javascript/tiptap/LICENSE.md) |

### PDF.js and embedded core-js

The headers in both [pdf.mjs](gravewright/journals/static/gravewright_journals/vendor/pdf.mjs) and [pdf.worker.mjs](gravewright/journals/static/gravewright_journals/vendor/pdf.worker.mjs) identify **PDF.js 6.2.108**, build **0365cbde0**, copyright 2024 Mozilla Foundation, under **Apache-2.0**. Its full local text is [PDFJS-LICENSE](gravewright/journals/static/gravewright_journals/vendor/PDFJS-LICENSE); the upstream project is [mozilla/pdf.js](https://github.com/mozilla/pdf.js).

Both files also embed **core-js 3.49.0**, which identifies its version, copyright and MIT license URL in the bundle. Its [upstream license](https://github.com/zloirock/core-js/blob/v3.49.0/LICENSE) is copied to [LICENSES/third-party/javascript/core-js/LICENSE](LICENSES/third-party/javascript/core-js/LICENSE). This supplementary MIT notice must accompany the embedded code as well as PDF.js's Apache notice.

## Icons, fonts, templates and reused UI

| Material | Evidence and terms |
| --- | --- |
| Phosphor icons | **247 SVGs** under [gravewright/web/icons](gravewright/web/icons/), with the original [MIT license](gravewright/web/icons/LICENSE), copyright 2020 Phosphor Icons. The [upstream project](https://github.com/phosphor-icons/core) is identified by that notice; the exact imported release/commit is not recorded locally. |
| Original Gravewright UI | [ORIGINAL-NOTICE](gravewright/web/static/gravewright_web/ORIGINAL-NOTICE) credits “Gravewright Vue frontend and UI components”, copyright 2026 Gravewright contributors, and records adaptation from an earlier local checkout. Its [Apache-2.0 text](gravewright/web/static/gravewright_web/ORIGINAL-LICENSE) is retained. No public source URL or exact original revision is recorded in that notice. |
| Windows runner icon | [gravewright.ico](scripts/windows/gravewright.ico) converts the existing CSS house mark into Windows icon sizes. Its [source and license note](scripts/windows/ICON-NOTICE.md) preserves the original UI attribution and Apache-2.0 terms. |
| Fonts | The CSS uses system/fallback font names; no font binaries or remotely imported webfont stylesheet were found in the application source tree. Naming a system font is not distribution of its font file. |
| Built-in PDF | [blank-a4.pdf](gravewright/pdf_system/static/gravewright_pdf_system/assets/blank-a4.pdf) contains Gravewright instructions and references the standard PDF Helvetica font; it does not embed a font binary. No separate third-party attribution is present in this file. |
| User content | Uploaded maps, images, sound, music, PDFs and campaign/module content are supplied at runtime. Their ownership and permissions are not inferred from Gravewright's license or this inventory. No standalone raster-image, audio or font files were found in application sources outside ignored runtime data. |

## Windows runner downloads

The [Gravewright Runner](docs/en/windows-runner.md) reuses compatible installed uv, Python and Node.js/npm tools. Where a compatible tool is missing, it downloads a fallback into the user's local application-data directory; these executables are not included in this source archive. The fallback **uv 0.12.13** download and cached executable are verified. That uv release is available under **Apache-2.0 OR MIT**; see its [Apache text](https://github.com/astral-sh/uv/blob/0.12.13/LICENSE-APACHE) and [MIT text](https://github.com/astral-sh/uv/blob/0.12.13/LICENSE-MIT). Reused installations retain the notices for their actual versions.

The batch launcher uses Windows-supplied CMD, `curl.exe`, `tar.exe` and `certutil.exe` for its installation flow. Those system tools are not redistributed in this source archive. The shortcut helper uses Python's standard library and the Windows COM interfaces; it adds no Python package dependency.

The runner uses an installed compatible **CPython 3.14** interpreter when available. Otherwise, uv downloads a managed build from [python-build-standalone](https://docs.astral.sh/uv/concepts/python-versions/#cpython-distributions). Python and its bundled native libraries carry their own notices, in addition to Python's [license history and terms](https://docs.python.org/3.14/license.html). The interpreter patch/build follows the selected installation or uv's managed runtime availability; it is not a Python package entry in `uv.lock`. The application's Python dependencies remain pinned by that lock, with Python development dependencies excluded from normal runner installation.

The Node fallback is the official [Node.js 24.19.0 Windows x64 distribution](https://nodejs.org/en/download/archive/v24.19.0), which includes **npm 11.17.0**. Its [Node license file](https://github.com/nodejs/node/blob/v24.19.0/LICENSE) covers Node and bundled components; the included [npm license file](https://github.com/nodejs/node/blob/v24.19.0/deps/npm/LICENSE) identifies **Artistic-2.0** for npm itself and separate terms for its dependencies. Those tool dependencies are distinct from Gravewright's map `package-lock.json`. The runner's frontend preparation installs the map lock's dependencies, including esbuild, and runs the existing build that collects its vendor notices.

When redistributing a preinstalled runner directory or an offline runtime package, preserve the actual uv, Python, Node.js, npm and installed-package license/notice files and applicable source-distribution information. This source-tree inventory alone is not a complete notice inventory for those downloaded or reused binary distributions.

## Scope limits and maintaining a release

This is a source-tree and package-notice inventory, not a claim that every possible installation or future module has been audited. In particular:

1. The existing journal editor is a prebuilt snapshot with a package list; this checkout does not contain its dedicated npm lock or a complete editor rebuild pipeline. The Phosphor snapshot and original UI adaptation also lack exact revision records.
2. The maps vendor directory contains hashed chunks from multiple builds. Its package inventory describes the recorded current build, not a separate provenance record for every leftover chunk. Review the actual distributed files when preparing a release.
3. Redis **server** software is configured externally and is not the same distribution as the MIT-licensed Python `redis` client. No Redis server version, container image or license is selected by this repository. Python, Node.js, operating-system libraries, separately downloaded browsers and platform-specific native binaries also need the notices that accompany the versions actually distributed.
4. The Python texts were copied from the installed distributions matching the lock, plus the two verified wheels described above. A wheel built for another platform can contain different native libraries/notices. Preserve its complete upstream distribution information when packaging it.
5. Third-party modules remain governed by their own licenses. Preserve and review module notices when packaging them; this document does not relicense them or override licenses of code copied into them.

When changing dependencies or vendor assets, update both language versions, preserve upstream license/copyright/NOTICE files, refresh the lock or bundled `packages.json`, and record sources for additional copies in `SOURCES.json`. When distributing compiled or packaged builds, include the applicable license/notice texts and satisfy source-code obligations for the components actually distributed. Ship this file, its Portuguese counterpart, the existing vendor notices and the supplementary `LICENSES/third-party` directory with release archives.
