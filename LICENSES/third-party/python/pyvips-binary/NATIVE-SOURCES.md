# Optional libvips binary provenance

Gravewright's optional `vips` extra locks pyvips 3.2.0 and pyvips-binary
8.18.7. The `LICENSE` in this directory is the MIT license for the
pyvips-binary wrapper. The native bundle is declared `LGPL-3.0-or-later`
by its Python package metadata and includes separately licensed libraries.

`THIRD-PARTY-NOTICES.md` and `versions.json` are unchanged files from the
[upstream Windows x64 libvips 8.18.7 archive](https://github.com/kleisauke/libvips-packaging/releases/download/v8.18.7/libvips-8.18.7-win-x64.tar.gz),
SHA-256 `5aeaaa952c2919723f1689e36c009ec4f1b5233ac293ad89be5ac50e76fa818a`.
The [pyvips-binary download script](https://github.com/kleisauke/pyvips-binary/blob/v8.18.7/scripts/download-vips.py)
identifies this packaging release as its source. Its
[Windows recipe](https://github.com/kleisauke/libvips-packaging/blob/v8.18.7/build/win.sh)
and [POSIX recipe](https://github.com/kleisauke/libvips-packaging/blob/v8.18.7/build/posix.sh)
identify the upstream native builds and dependency sources.

`native/` preserves component license and attribution texts from the
versioned upstream sources identified by those component versions. Exact
source URLs and SHA-256 hashes for every copied text are recorded in
[`SOURCES.json`](../../SOURCES.json). The libnsgif notice comes from its
embedded copy in the libvips 8.18.7 sources. The original GLib `COPYING`
is a pointer to its `LGPL-2.1-or-later.txt`; the target text is retained
under `native/glib/`. The LGPLv3 text accompanies the native bundle's
chosen later-version terms; the complete GPLv3 text is also present in
the Gravewright root [`LICENSE`](../../../../LICENSE).

The optional native bundle uses FreeType 2.14.3 code from
[the FreeType Project](https://freetype.org); its FreeType license is
retained in `native/freetype/FTL.TXT`. Its JPEG support is based in part
on the work of the Independent JPEG Group; the mozjpeg and IJG notices
are retained in `native/mozjpeg/`.

These files preserve notices for the declared native components. They
are not the complete corresponding source or relinking materials and
do not inventory every platform's compiler runtimes or recursively
embedded dependencies. Native binaries are not included in Gravewright's
source archive. When redistributing an installed or offline environment,
also retain its actual platform-specific notices and provide the
corresponding sources and relinking materials required by the
components' licenses, including their patches and build scripts.
