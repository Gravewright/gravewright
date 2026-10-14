#!/bin/bash
# Sourced by install.sh; Bash 3.2 compatible. No Homebrew or rustup bootstrap.
# Official pinned sources reviewed 2026-10-13:
# https://static.rust-lang.org/dist/channel-rust-stable.toml (2026-10-01)
# https://openssl-library.org/source/ (OpenSSL 3.5 LTS)

gw_mac_pins() {
    GW_RUST_VERSION=1.99.0
    GW_RUST_TARGET=x86_64-apple-darwin
    GW_RUST_DATE=2026-10-01
    GW_RUSTC_SHA=4b909ba0153d4a67eb83a31ef11157b7c54e5c04a323d80e46436b778c18df52
    GW_CARGO_SHA=ec5bd1c782e5b9d58cfcafbc4131d19fd7ca2ec6b1a197f2fd1a1f953802a26a
    GW_RUST_STD_SHA=7321ff86554726b8ab7b0a5c0d9ba0a3e763824f5d09b0c997e36bd72b80fa06
    GW_OPENSSL_VERSION=3.5.9
    GW_OPENSSL_SHA=603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a
}

gw_mac_clt_available() {
    command -v xcrun >/dev/null 2>&1 && command -v make >/dev/null 2>&1 && command -v perl >/dev/null 2>&1 || return 1
    GW_MAC_CLANG=$(xcrun --sdk macosx --find clang 2>/dev/null) || return 1
    GW_MAC_SDK=$(xcrun --sdk macosx --show-sdk-path 2>/dev/null) || return 1
    [ -x "$GW_MAC_CLANG" ] && [ -d "$GW_MAC_SDK" ] || return 1
    "$GW_MAC_CLANG" --version >/dev/null 2>&1 && make --version >/dev/null 2>&1 && perl -e 'use File::Spec; use FindBin; use IPC::Cmd;' || return 1
}

gw_mac_require_clt() {
    gw_mac_clt_available && return 0
    if [ "$GW_CHECK" -eq 0 ] && [ -t 0 ] && command -v xcode-select >/dev/null 2>&1; then
        gw_info 'Opening the official Apple Command Line Tools installer...'
        xcode-select --install || true
    fi
    gw_fail 'Mac Intel builds a locked cryptography dependency from source. Install Apple Command Line Tools with xcode-select --install, finish the Apple installer, then run Gravewright installation again. A working macOS SDK, clang, make and Perl are required; Homebrew is not required.'
}

gw_mac_cached_download() {
    local url=$1 archive=$2 expected=$3
    if [ -f "$archive" ] && [ "$(gw_sha256 "$archive")" = "$expected" ]; then return 0; fi
    case "${UV_OFFLINE:-0}" in 1|true) gw_fail 'A verified macOS build-tool archive is missing. Run installation once with internet access.'; return 1 ;; esac
    mkdir -p "${archive%/*}"
    gw_download "$url" "$GW_WORK/mac-download.part" "$expected" || return 1
    mv "$GW_WORK/mac-download.part" "$archive"
}

gw_mac_manifest() {
    "$GW_BASE_PYTHON" -I "$GW_ROOT/scripts/posix/mac_build.py" "$@"
}

gw_mac_try_rust() {
    local candidate=$1 details version host cargo_version bin sysroot library_dir library cargo_label cargo_number cargo_rest
    [ -x "$candidate" ] || return 1
    details=$("$candidate" --version --verbose 2>/dev/null) || return 1
    version=$(printf '%s\n' "$details" | awk '$1 == "release:" {print $2}')
    host=$(printf '%s\n' "$details" | awk '$1 == "host:" {print $2}')
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && gw_version_at_least "$version" 1 83 && [ "$host" = "$GW_RUST_TARGET" ] || return 1
    sysroot=$("$candidate" --print sysroot 2>/dev/null) || return 1
    bin="$sysroot/bin"
    [ -x "$bin/rustc" ] || return 1
    [ -x "$bin/cargo" ] || return 1
    cargo_version=$("$bin/cargo" --version 2>/dev/null) || return 1
    read -r cargo_label cargo_number cargo_rest <<EOF
$cargo_version
EOF
    [ "$cargo_label" = cargo ] && [[ "$cargo_number" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && gw_version_at_least "$cargo_number" 1 83 || return 1
    library_dir=$("$candidate" --print target-libdir 2>/dev/null) || return 1
    [ -d "$library_dir" ] || return 1
    for library in "$library_dir"/libstd-*.rlib; do [ ! -f "$library" ] || { GW_RUST_BIN=$bin; return 0; }; done
    return 1
}

gw_mac_resolve_rust() {
    local destination stage component expected archive
    local archives=() hashes=()
    GW_RUST_BIN=''
    destination="$GW_RUNTIME/rust/$GW_RUST_VERSION-$GW_RUST_TARGET"
    if gw_mac_manifest verify --root "$destination" --kind rust --version "$GW_RUST_VERSION" --quiet && gw_mac_try_rust "$destination/bin/rustc"; then return 0; fi
    stage="$GW_WORK/rust-install"
    for component in rustc cargo rust-std; do
        case "$component" in rustc) expected=$GW_RUSTC_SHA ;; cargo) expected=$GW_CARGO_SHA ;; rust-std) expected=$GW_RUST_STD_SHA ;; esac
        archive="$GW_RUNTIME/downloads/mac/$component-$GW_RUST_VERSION-$GW_RUST_TARGET.tar.gz"
        gw_info "Preparing private Rust component: $component $GW_RUST_VERSION..."
        gw_mac_cached_download "https://static.rust-lang.org/dist/$GW_RUST_DATE/$component-$GW_RUST_VERSION-$GW_RUST_TARGET.tar.gz" "$archive" "$expected"
        archives+=("$archive"); hashes+=("$expected")
    done
    # Pass a relative prefix to Rust's installer so project spaces are harmless.
    gw_mac_manifest install-rust --root "$stage" --version "$GW_RUST_VERSION" --archives "${archives[@]}" --hashes "${hashes[@]}"
    gw_mac_manifest record --root "$stage" --kind rust --version "$GW_RUST_VERSION"
    mkdir -p "$GW_RUNTIME/rust"
    if [ -e "$destination" ]; then mv "$destination" "$GW_WORK/previous-rust"; fi
    mv "$stage" "$destination"
    gw_mac_try_rust "$destination/bin/rustc" || { gw_fail 'The verified private Rust toolchain cannot execute on this Mac.'; return 1; }
}

gw_mac_try_openssl() {
    local prefix=$1
    [ -n "$prefix" ] && [ -x "$prefix/bin/openssl" ] || return 1
    gw_mac_manifest probe-openssl --root "$prefix" --clang "$GW_MAC_CLANG" --sdk "$GW_MAC_SDK" --quiet || return 1
    GW_OPENSSL_ROOT=$prefix
}

gw_mac_resolve_openssl() {
    local destination stage archive
    GW_OPENSSL_ROOT=''
    destination="$GW_RUNTIME/openssl/$GW_OPENSSL_VERSION-darwin-x64"
    if gw_mac_manifest verify --root "$destination" --kind openssl --version "$GW_OPENSSL_VERSION" --quiet && gw_mac_try_openssl "$destination"; then return 0; fi
    archive="$GW_RUNTIME/downloads/mac/openssl-$GW_OPENSSL_VERSION.tar.gz"
    gw_mac_cached_download "https://github.com/openssl/openssl/releases/download/openssl-$GW_OPENSSL_VERSION/openssl-$GW_OPENSSL_VERSION.tar.gz" "$archive" "$GW_OPENSSL_SHA"
    stage="$GW_WORK/openssl-install"
    gw_info "Building private static OpenSSL $GW_OPENSSL_VERSION with Apple's SDK. This can take several minutes..."
    mkdir -p "$GW_RUNTIME/build-logs"
    gw_mac_manifest build-openssl --archive "$archive" --sha256 "$GW_OPENSSL_SHA" --root "$stage" --final-root "$destination" --version "$GW_OPENSSL_VERSION" --clang "$GW_MAC_CLANG" --sdk "$GW_MAC_SDK" --log "$GW_RUNTIME/build-logs/openssl-$GW_OPENSSL_VERSION-darwin-x64.log"
    gw_mac_manifest record --root "$stage" --kind openssl --version "$GW_OPENSSL_VERSION"
    mkdir -p "$GW_RUNTIME/openssl"
    if [ -e "$destination" ]; then mv "$destination" "$GW_WORK/previous-openssl"; fi
    mv "$stage" "$destination"
    gw_mac_try_openssl "$destination" || { gw_fail 'The private static OpenSSL build could not be validated.'; return 1; }
}

gw_mac_prepare_build_tools() {
    [ "$GW_PLATFORM" = darwin ] || return 0
    # Autobahn explicitly supports this pure-Python path. It avoids needing an
    # optional CFFI accelerator on Intel and on macOS versions before 15.
    export AUTOBAHN_USE_NVX=0
    [ "$GW_ARCH" = x64 ] || return 0
    gw_mac_pins
    gw_mac_require_clt
    unset RUSTC CARGO RUSTDOC RUSTFLAGS CARGO_ENCODED_RUSTFLAGS
    export CARGO_HOME="$GW_RUNTIME/cargo"
    gw_mac_resolve_rust
    unset RUSTUP_TOOLCHAIN
    export GRAVEWRIGHT_BUILD_TOOLS_PATH="$GW_RUST_BIN"
    export PATH="$GW_RUST_BIN:$PATH"
    gw_mac_resolve_openssl
    export OPENSSL_DIR="$GW_OPENSSL_ROOT" OPENSSL_STATIC=1
    "$GW_RUST_BIN/rustc" --version
    "$GW_RUST_BIN/cargo" --version
    "$OPENSSL_DIR/bin/openssl" version
}
