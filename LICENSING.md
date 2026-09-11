# Licensing

[English](LICENSING.md) · [Português (Brasil)](LICENSING.pt-BR.md)

## Project grant

Unless a file or a preserved third-party notice states otherwise, Gravewright's first-party source code, accompanying documentation and original assets are licensed under the **GNU General Public License, version 3 only**, with the additional permission in [LICENSE-EXCEPTION](LICENSE-EXCEPTION).

You may redistribute and modify that material under GPL version 3 as published by the Free Software Foundation. No option to use a later version is granted. The project is distributed without any warranty, including the implied warranties of merchantability or fitness for a particular purpose, to the extent permitted by law. See [LICENSE](LICENSE) for the complete terms.

The GPL text is kept unmodified. The example “or any later version” notice in its appendix is not the project's license grant; the grant above specifies version 3 only.

## Independent modules

The project explicitly permits independently written modules under any license, including proprietary licenses, **using or not using its APIs**. This is an additional permission under GPLv3 section 7; [LICENSE-EXCEPTION](LICENSE-EXCEPTION) is the operative text. The Portuguese version is informative.

| Situation | Project policy |
| --- | --- |
| Original module using the browser SDK, Python interfaces, HTTP or WebSockets | Any module license, subject to the additional permission and its own dependencies |
| Original module using internal interfaces or another integration mechanism | Same permission; no promise of API stability or technical support |
| Modifications to Gravewright core distributed to others | GPL-3.0-only continues to apply to the core, including applicable source obligations |
| Core implementation copied into a module | The copied/adapted material remains covered by its license; the module label is not an exception |
| Maps, books, music, PDFs, campaign data or other uploaded content | No ownership transfer or automatic GPL licensing; the content owner's terms apply |
| Bundled third-party code or assets | Preserve and comply with their own licenses and notices |

A paid module can be open source or proprietary. The permission covers both. It does not grant a module author rights to other people's assets or cancel a dependency's copyleft obligations. Only material for which the relevant copyright holders have granted the permission benefits from it.

## Contributions and notices

By intentionally submitting original contributions for inclusion in the core, you offer them under GPL-3.0-only with the same additional module permission. Contributors retain their copyright. Clearly identify reused material and its license when submitting it; do not replace existing upstream notices with a project notice. See [CONTRIBUTING.md](CONTRIBUTING.md).

For a new first-party source file, an optional short header is:

```text
Licensed under GNU GPL version 3 only, with the Gravewright Independent Module
Permission. See LICENSE, LICENSE-EXCEPTION and LICENSING.md in the source root.
```

Do not add this header to vendored files. The custom SPDX license reference in `pyproject.toml` names the complete GPL-3.0-only plus module-permission terms; its text is in [LICENSES/LicenseRef-Gravewright-GPL-3.0-only-with-module-permission.txt](LICENSES/LicenseRef-Gravewright-GPL-3.0-only-with-module-permission.txt). It is a project-defined reference, not an SPDX-listed exception or an assertion that this custom permission has separate OSI approval. The underlying GPL license identifier is `GPL-3.0-only`.

## Distribution

Distributions should carry `LICENSE`, `LICENSE-EXCEPTION`, this policy and applicable [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and upstream license files. Check the actual contents of a release, including bundled wheels, JavaScript, fonts and native libraries; the source notice inventory does not automatically describe every possible deployment image.

The permission follows the mechanism described in [GPLv3 section 7](https://www.gnu.org/licenses/gpl-3.0.html#section7). The GNU project's [plugin discussion](https://www.gnu.org/licenses/gpl-faq.en.html#GPLPlugins) explains why a module policy needs to address how programs interact rather than rely on the word “plugin.” The project-defined permission above implements the intended broader integration policy.
