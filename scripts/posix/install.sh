#!/bin/bash
# Bash 3.2 compatible: the macOS system shell needs no additional bootstrap.
# uv archives: https://github.com/astral-sh/uv/releases/tag/0.12.13
# Node archives/checksums: https://nodejs.org/download/release/v24.19.0/
# Python downloads use uv's embedded python-build-standalone checksum catalog.

gw_fail() { printf '\nGravewright Installer: %s\n' "$*" >&2; return 1; }
gw_info() { printf '%s\n' "$*"; }

gw_help() {
    cat <<'HELP'
Gravewright Linux/macOS Installer
Usage: installer [--check] [--data-dir PATH] [--port NUMBER] [--no-browser] [--no-pause]

--check       Prepare tools, dependencies, assets and database without questions.
--data-dir    Select the persistent Runner state directory.
--port        Override the local port (1-65535) during the installation check only.
--no-browser  Accepted for compatibility; installation never opens the browser.
--no-pause    Exit without waiting for a key, for terminals and automation.

Installation never starts the server. Open the generated Gravewright Runner to play.
Tools, caches and Runner state stay inside this extracted installation.
GRAVEWRIGHT_RUNNER_ROOT optionally selects a tools directory, relative to the project.
HELP
}

gw_parse_arguments() {
    GW_CHECK=0 GW_NO_BROWSER=0 GW_NO_PAUSE=0 GW_DATA='' GW_PORT='' GW_HELP=0
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --help|-h) GW_HELP=1; return 0 ;;
            --check) GW_CHECK=1; GW_NO_PAUSE=1; shift ;;
            --no-browser) GW_NO_BROWSER=1; shift ;;
            --no-pause) GW_NO_PAUSE=1; shift ;;
            --data-dir)
                [ "$#" -ge 2 ] && [ -n "$2" ] || { gw_fail '--data-dir needs a path.'; return 1; }
                GW_DATA=$2; shift 2 ;;
            --port)
                [ "$#" -ge 2 ] && [[ "$2" =~ ^[0-9]{1,5}$ ]] || { gw_fail '--port needs a number from 1 to 65535.'; return 1; }
                GW_PORT=$((10#$2))
                [ "$GW_PORT" -ge 1 ] && [ "$GW_PORT" -le 65535 ] || { gw_fail '--port must be between 1 and 65535.'; return 1; }
                shift 2 ;;
            *) gw_fail "Unknown argument: $1. Use --help for usage."; return 1 ;;
        esac
    done
}

gw_os_release_value() {
    # Parse only a restricted data value. Never source/eval os-release contents.
    local value=$1
    case "$value" in
        \"*\") value=${value#\"}; value=${value%\"} ;;
        \'*\') value=${value#\'}; value=${value%\'} ;;
    esac
    case "$value" in *[!a-zA-Z0-9_.\ -]*) return 1 ;; esac
    printf '%s\n' "$value"
}

gw_family_for_id() {
    case "$1" in
        debian|ubuntu|linuxmint|pop|neon|kali|raspbian) printf 'apt\n' ;;
        fedora|rhel|centos|rocky|almalinux|ol|amzn) printf 'rpm\n' ;;
        opensuse|opensuse-leap|opensuse-tumbleweed|suse|sles) printf 'zypper\n' ;;
        arch|manjaro|endeavouros|garuda) printf 'pacman\n' ;;
        alpine|postmarketos) printf 'apk\n' ;;
        *) return 1 ;;
    esac
}

gw_detect_distro() {
    local file=${1:-/etc/os-release} line key value token
    GW_DISTRO_ID='' GW_DISTRO_LIKE='' GW_DISTRO_FAMILY=''
    [ -r "$file" ] || { gw_fail 'Linux needs a readable /etc/os-release file.'; return 1; }
    while IFS= read -r line || [ -n "$line" ]; do
        line=${line%$'\r'}
        case "$line" in ID=*|ID_LIKE=*) ;; *) continue ;; esac
        key=${line%%=*}
        value=$(gw_os_release_value "${line#*=}") || { gw_fail 'Invalid ID or ID_LIKE in /etc/os-release.'; return 1; }
        case "$key" in ID) GW_DISTRO_ID=$value ;; ID_LIKE) GW_DISTRO_LIKE=$value ;; esac
    done < "$file"
    case "$GW_DISTRO_ID" in ''|*' '*) gw_fail 'Missing or invalid Linux distribution ID.'; return 1 ;; esac
    GW_DISTRO_FAMILY=$(gw_family_for_id "$GW_DISTRO_ID") && return 0
    # Validated ID_LIKE contains only names separated by spaces, no shell syntax.
    for token in $GW_DISTRO_LIKE; do
        GW_DISTRO_FAMILY=$(gw_family_for_id "$token") && return 0
    done
    gw_fail "Unsupported Linux distribution: $GW_DISTRO_ID (ID_LIKE: $GW_DISTRO_LIKE). Supported families: Debian/Ubuntu, Fedora/RHEL, openSUSE, Arch and Alpine."
}

gw_version_at_least() {
    local actual=$1 major=$2 minor=$3 a b rest
    [[ "$actual" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]] || return 1
    IFS=. read -r a b rest <<EOF
$actual
EOF
    [ "$a" -gt "$major" ] || { [ "$a" -eq "$major" ] && [ "$b" -ge "$minor" ]; }
}

gw_detect_platform() {
    GW_OS=$(uname -s)
    GW_MACHINE=$(uname -m)
    if [ -n "${GW_INSTALL_EXPECT_OS:-}" ] && [ "$GW_OS" != "$GW_INSTALL_EXPECT_OS" ]; then
        gw_fail "This installer is for $GW_INSTALL_EXPECT_OS; this operating system is $GW_OS."; return 1
    fi
    case "$GW_OS" in
        Darwin)
            GW_PLATFORM=darwin GW_LIBC=none
            # Prefer native Apple Silicon even when Terminal itself uses Rosetta.
            if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || true)" = 1 ]; then GW_MACHINE=arm64; fi
            gw_version_at_least "$(sw_vers -productVersion)" 13 5 || { gw_fail 'macOS 13.5 or newer is required by the bundled Node.js runtime.'; return 1; }
            ;;
        Linux)
            GW_PLATFORM=linux
            gw_detect_distro
            local libc_value loader
            libc_value=$(getconf GNU_LIBC_VERSION 2>/dev/null || true)
            case "$libc_value" in
                'glibc '*)
                    GW_LIBC=gnu
                    gw_version_at_least "${libc_value#glibc }" 2 28 || { gw_fail 'Linux glibc 2.28 or newer is required.'; return 1; }
                    ;;
                *)
                    GW_LIBC=''
                    for loader in /lib/ld-musl-*.so.1 /usr/lib/ld-musl-*.so.1; do
                        if [ -e "$loader" ]; then GW_LIBC=musl; break; fi
                    done
                    if [ "$GW_DISTRO_FAMILY" = apk ]; then GW_LIBC=musl; fi
                    if [ -z "$GW_LIBC" ] && [[ "$(ldd --version 2>&1 || true)" == *musl* ]]; then GW_LIBC=musl; fi
                    [ -n "$GW_LIBC" ] || { gw_fail 'Cannot identify Linux libc. Supported: glibc >=2.28, or musl with an existing compatible Node.js installation.'; return 1; }
                    ;;
            esac
            ;;
        *) gw_fail "Unsupported operating system: $GW_OS. Use the Linux, macOS or Windows installer for your platform."; return 1 ;;
    esac
    case "$GW_MACHINE" in
        x86_64|amd64) GW_ARCH=x64 GW_UV_ARCH=x86_64 ;;
        arm64|aarch64) GW_ARCH=arm64 GW_UV_ARCH=aarch64 ;;
        *) gw_fail "Unsupported architecture: $GW_MACHINE. This installer supports x64 and arm64."; return 1 ;;
    esac
}

gw_has_certificates() {
    local cert
    for cert in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt /etc/ssl/cert.pem /var/lib/ca-certificates/ca-bundle.pem; do
        [ ! -s "$cert" ] || return 0
    done
    [ -n "${SSL_CERT_FILE:-}" ] && [ -s "$SSL_CERT_FILE" ]
}

gw_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
    else return 1
    fi
}

gw_prerequisites() {
    local missing=() packages=() manager='' hash_missing=0
    command -v curl >/dev/null 2>&1 || missing+=(curl)
    command -v tar >/dev/null 2>&1 || missing+=(tar)
    command -v gzip >/dev/null 2>&1 || missing+=(gzip)
    if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
        hash_missing=1
    fi
    if [ "$GW_PLATFORM" = darwin ]; then
        [ "${#missing[@]}" -eq 0 ] && [ "$hash_missing" -eq 0 ] || { gw_fail 'macOS system tools curl, tar, gzip and shasum are required. Restore the system tools; Homebrew is not required.'; return 1; }
        if [ "$GW_ARCH" = x64 ]; then gw_mac_require_clt; fi
        return 0
    fi
    packages=("${missing[@]}")
    [ "$hash_missing" -eq 0 ] || packages+=(coreutils)
    gw_has_certificates || packages+=(ca-certificates)
    [ "${#packages[@]}" -ne 0 ] || return 0
    command -v sudo >/dev/null 2>&1 || { gw_fail "Missing prerequisites: ${packages[*]}. Ask your administrator to install them for this distribution, then run again as your normal user."; return 1; }
    local sudo_args=()
    if [ "$GW_CHECK" -eq 1 ] || [ ! -t 0 ]; then sudo_args=(-n); fi
    gw_info "Installing missing system prerequisites only: ${packages[*]}"
    case "$GW_DISTRO_FAMILY" in
        apt)
            command -v apt-get >/dev/null 2>&1 || { gw_fail 'This Debian-like distribution does not provide apt-get.'; return 1; }
            sudo "${sudo_args[@]}" apt-get update
            sudo "${sudo_args[@]}" apt-get install -y "${packages[@]}" ;;
        rpm)
            if command -v dnf >/dev/null 2>&1; then manager=dnf
            elif command -v yum >/dev/null 2>&1; then manager=yum
            else gw_fail 'This RPM distribution needs dnf or yum.'; return 1; fi
            sudo "${sudo_args[@]}" "$manager" install -y "${packages[@]}" ;;
        zypper) sudo "${sudo_args[@]}" zypper --non-interactive install "${packages[@]}" ;;
        pacman) sudo "${sudo_args[@]}" pacman -S --needed --noconfirm "${packages[@]}" ;;
        apk) sudo "${sudo_args[@]}" apk add "${packages[@]}" ;;
        *) gw_fail 'Unsupported prerequisite package manager.'; return 1 ;;
    esac
    for manager in curl tar gzip; do command -v "$manager" >/dev/null 2>&1 || { gw_fail "The prerequisite installation did not provide $manager."; return 1; }; done
    command -v sha256sum >/dev/null 2>&1 || command -v shasum >/dev/null 2>&1 || { gw_fail 'A SHA256 utility is still missing.'; return 1; }
    gw_has_certificates || { gw_fail 'System CA certificates are still missing.'; return 1; }
}

gw_download() {
    local url=$1 archive=$2 expected=$3 actual
    case "$url" in https://*) ;; *) gw_fail 'Downloads must use HTTPS.'; return 1 ;; esac
    curl --fail --location --retry 2 --connect-timeout 20 --max-time 300 --proto '=https' --proto-redir '=https' --tlsv1.2 --output "$archive" "$url" || return 1
    actual=$(gw_sha256 "$archive") || return 1
    [ "$actual" = "$expected" ] || { gw_fail 'Download failed its pinned SHA256 check. It will not be extracted or executed.'; return 1; }
}

gw_uv_archive() {
    GW_UV_VERSION=0.12.13
    case "$GW_PLATFORM-$GW_ARCH-$GW_LIBC" in
        linux-x64-gnu) GW_UV_TARGET=x86_64-unknown-linux-gnu; GW_UV_SHA=745765a3b6e360ad76743599ae5c42e9278c7edf8bbff9fc76d05bf2623a04dd ;;
        linux-arm64-gnu) GW_UV_TARGET=aarch64-unknown-linux-gnu; GW_UV_SHA=2eaa5d94f5db7b3a1a092156b9420459e42ab0217d917fe74a876309cef9b5e9 ;;
        linux-x64-musl) GW_UV_TARGET=x86_64-unknown-linux-musl; GW_UV_SHA=4e2bfd0c9007b1032a50e539e965fd0a6037d87ad93ae1580d220a92d4c94098 ;;
        linux-arm64-musl) GW_UV_TARGET=aarch64-unknown-linux-musl; GW_UV_SHA=f44bc1037a17889fe562fffd2002d4ed108e499fbe68b4f022af244dc7b8244f ;;
        darwin-x64-none) GW_UV_TARGET=x86_64-apple-darwin; GW_UV_SHA=5e287ef61cb6a9b61b3a83fef124fd143e400468a7dac794230147a810e17119 ;;
        darwin-arm64-none) GW_UV_TARGET=aarch64-apple-darwin; GW_UV_SHA=7e6ddb9316acc00f2296c82ff4d99977870ee34b2f0ddcae9444d714db9364ed ;;
        *) gw_fail 'No pinned uv archive for this platform.'; return 1 ;;
    esac
}

gw_try_uv() {
    local candidate=$1 label version rest
    [ -x "$candidate" ] || return 1
    read -r label version rest <<EOF
$("$candidate" --version 2>/dev/null)
EOF
    [ "$label" = uv ] && [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && gw_version_at_least "$version" 0 12 || return 1
    GW_UV=$candidate
}

gw_resolve_uv() {
    local destination
    GW_UV=''
    gw_uv_archive
    destination="$GW_RUNTIME/uv/$GW_UV_VERSION-$GW_UV_TARGET"
    gw_try_uv "$destination/uv" && return 0
    gw_info "Downloading private uv $GW_UV_VERSION ($GW_UV_TARGET)..."
    gw_download "https://github.com/astral-sh/uv/releases/download/$GW_UV_VERSION/uv-$GW_UV_TARGET.tar.gz" "$GW_WORK/uv.tar.gz" "$GW_UV_SHA"
    mkdir "$GW_WORK/uv"
    tar -xzf "$GW_WORK/uv.tar.gz" -C "$GW_WORK/uv"
    [ -x "$GW_WORK/uv/uv-$GW_UV_TARGET/uv" ] || { gw_fail 'The verified uv archive is incomplete.'; return 1; }
    mkdir -p "$GW_RUNTIME/uv"
    if [ -e "$destination" ]; then mv "$destination" "$GW_WORK/previous-uv"; fi
    mv "$GW_WORK/uv/uv-$GW_UV_TARGET" "$destination"
    gw_try_uv "$destination/uv" || { gw_fail 'The verified uv runtime cannot execute on this system.'; return 1; }
}

gw_find_python() {
    local candidate
    candidate=$("$GW_UV" --no-config python find --system --no-project --no-python-downloads "$GW_PYTHON_KEY" 2>/dev/null) || return 1
    [ -x "$candidate" ] || return 1
    "$candidate" -I -c 'import platform,struct,sys,sysconfig; machine=platform.machine().lower(); expected=sys.argv[2]; ok=(machine in ("x86_64","amd64") if expected=="x64" else machine in ("aarch64","arm64")); sys.exit(not (sys.implementation.name=="cpython" and sys.version_info[:2]==(3,14) and sys.version_info.releaselevel=="final" and sys.platform==sys.argv[1] and struct.calcsize("P")==8 and ok and not sysconfig.get_config_var("Py_GIL_DISABLED")))' "$GW_PLATFORM" "$GW_ARCH" || return 1
    GW_BASE_PYTHON=$candidate
}

gw_resolve_python() {
    GW_BASE_PYTHON=''
    # uv displays the canonical OS name "macos"; Node/Python report "darwin".
    case "$GW_PLATFORM" in darwin) GW_PYTHON_OS=macos ;; *) GW_PYTHON_OS=$GW_PLATFORM ;; esac
    GW_PYTHON_KEY="cpython-3.14-$GW_PYTHON_OS-$GW_UV_ARCH-$GW_LIBC"
    export UV_PYTHON_INSTALL_DIR="$GW_RUNTIME/python"
    export UV_PYTHON_BIN_DIR="$GW_RUNTIME/python-bin"
    export UV_PYTHON_INSTALL_BIN=0
    export UV_PYTHON_PREFERENCE=only-managed
    gw_find_python && return 0
    gw_info 'Installing a private CPython 3.14 runtime with uv checksum verification...'
    "$GW_UV" --no-config python install "$GW_PYTHON_KEY"
    gw_find_python || { gw_fail 'CPython 3.14 could not be prepared for this platform.'; return 1; }
}

gw_try_npm() {
    local cli=$1 version
    [ -f "$cli" ] || return 1
    version=$("$GW_NODE_REAL" "$cli" --version 2>/dev/null) || return 1
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
    [ "${version%%.*}" -ge 10 ] || return 1
    GW_NODE=$GW_NODE_REAL GW_NPM=$cli
}

gw_try_node() {
    local candidate=$1 version actual_arch actual_platform cli
    [ -x "$candidate" ] || return 1
    version=$("$candidate" --version 2>/dev/null) || return 1
    [[ "$version" =~ ^v(22|24)\.[0-9]+\.[0-9]+$ ]] || return 1
    actual_arch=$("$candidate" -p process.arch 2>/dev/null) || return 1
    actual_platform=$("$candidate" -p process.platform 2>/dev/null) || return 1
    [ "$actual_arch" = "$GW_ARCH" ] && [ "$actual_platform" = "$GW_PLATFORM" ] || return 1
    GW_NODE_REAL=$("$candidate" -p process.execPath 2>/dev/null) || return 1
    [ -x "$GW_NODE_REAL" ] || return 1
    for cli in "${GW_NODE_REAL%/*}/../lib/node_modules/npm/bin/npm-cli.js" "${GW_NODE_REAL%/*}/node_modules/npm/bin/npm-cli.js"; do
        gw_try_npm "$cli" && return 0
    done
    return 1
}

gw_node_archive() {
    GW_NODE_VERSION=24.19.0
    case "$GW_PLATFORM-$GW_ARCH-$GW_LIBC" in
        linux-x64-gnu) GW_NODE_SHA=f625d97cd707df4ff96254916fbc5ff014f09c09effe5a1e0ca8f6d41a8789d4 ;;
        linux-arm64-gnu) GW_NODE_SHA=d28c8a5bf0a808f0ed434a1dce8c54ae98f0371c0bd86ac58abc613f73e6643f ;;
        darwin-x64-none) GW_NODE_SHA=d1b5e999db158c62fe8f7267a4476b035d8bd93b1a605bac24a3f0dd166e3316 ;;
        darwin-arm64-none) GW_NODE_SHA=8294b7aa9b03997481c06babf1e8b270c859358f27da57a11509afe537ac381d ;;
        linux-*-musl) gw_fail "Alpine/musl has no official Node.js binary for private bootstrap. Place a native Node.js 22 or 24 distribution with npm >=10 under $GW_RUNTIME/node/native (bin/node and lib/node_modules/npm), then run again. No glibc binary or compatibility shim will be installed."; return 1 ;;
        *) gw_fail 'No pinned Node.js archive for this platform.'; return 1 ;;
    esac
}

gw_resolve_node() {
    local destination archive_name
    GW_NODE='' GW_NPM=''
    # musl has no official archive; an explicitly prepared local native build is required.
    if [ "$GW_LIBC" = musl ]; then
        gw_try_node "$GW_RUNTIME/node/native/bin/node" && return 0
    fi
    gw_node_archive
    destination="$GW_RUNTIME/node/$GW_NODE_VERSION-$GW_PLATFORM-$GW_ARCH"
    gw_try_node "$destination/bin/node" && return 0
    archive_name="node-v$GW_NODE_VERSION-$GW_PLATFORM-$GW_ARCH"
    gw_info "Downloading private Node.js $GW_NODE_VERSION and npm ($GW_PLATFORM-$GW_ARCH)..."
    gw_download "https://nodejs.org/download/release/v$GW_NODE_VERSION/$archive_name.tar.gz" "$GW_WORK/node.tar.gz" "$GW_NODE_SHA"
    mkdir "$GW_WORK/node"
    tar -xzf "$GW_WORK/node.tar.gz" -C "$GW_WORK/node"
    [ -x "$GW_WORK/node/$archive_name/bin/node" ] || { gw_fail 'The verified Node.js archive is incomplete.'; return 1; }
    mkdir -p "$GW_RUNTIME/node"
    if [ -e "$destination" ]; then mv "$destination" "$GW_WORK/previous-node"; fi
    # Keep the complete official distribution, including npm and license files.
    mv "$GW_WORK/node/$archive_name" "$destination"
    if ! gw_try_node "$destination/bin/node"; then
        "$destination/bin/node" --version || true
        gw_fail 'Node.js/npm cannot execute. Check libc/libstdc++ compatibility and the error above.'; return 1
    fi
}

gw_cleanup() {
    local status=$?
    if [ -n "${GW_WORK:-}" ] && [ -n "${GW_RUNTIME:-}" ]; then
        case "$GW_WORK" in "$GW_RUNTIME"/work.*) rm -rf -- "$GW_WORK" ;; esac
    fi
    if [ "${GW_LOCK_OWNED:-0}" -eq 1 ]; then
        rm -f -- "$GW_RUNTIME/prepare.lock/pid"
        rmdir -- "$GW_RUNTIME/prepare.lock" 2>/dev/null || true
    fi
    if [ "$status" -ne 0 ]; then printf '\nInstallation failed during: %s. Review the error above and run again.\n' "${GW_PHASE:-initial checks}" >&2; fi
    if [ "${GW_NO_PAUSE:-1}" -eq 0 ] && [ -t 0 ]; then read -r -p 'Press Enter to close...' unused || true; fi
    return "$status"
}

gw_local_paths() {
    GW_RUNTIME=${GRAVEWRIGHT_RUNNER_ROOT:-$GW_ROOT/data/runner}
    case "$GW_RUNTIME" in /*) ;; *) GW_RUNTIME="$GW_ROOT/$GW_RUNTIME" ;; esac
    if [ -z "$GW_DATA" ]; then GW_DATA="$GW_ROOT/data"; fi
    case "$GW_DATA" in /*) ;; *) GW_DATA="$GW_ROOT/$GW_DATA" ;; esac
    case "$GW_RUNTIME$GW_DATA" in *$'\n'*|*$'\r'*) gw_fail 'Paths cannot contain newlines.'; return 1 ;; esac
    mkdir -p "$GW_RUNTIME" "$GW_DATA"
    GW_RUNTIME=$(CDPATH= cd -- "$GW_RUNTIME" && pwd -P)
    GW_DATA=$(CDPATH= cd -- "$GW_DATA" && pwd -P)
    export GRAVEWRIGHT_RUNNER_ROOT="$GW_RUNTIME"
}

gw_cache_environment() {
    export UV_CACHE_DIR="$GW_RUNTIME/cache" UV_PYTHON_DOWNLOADS=automatic UV_LINK_MODE=copy UV_NO_ENV_FILE=1
    export UV_PYTHON_INSTALL_DIR="$GW_RUNTIME/python" UV_PYTHON_BIN_DIR="$GW_RUNTIME/python-bin" UV_PYTHON_INSTALL_BIN=0
    export CARGO_HOME="$GW_RUNTIME/cargo" RUSTUP_HOME="$GW_RUNTIME/rustup"
    export TMPDIR="$GW_RUNTIME/tmp" TMP="$GW_RUNTIME/tmp" TEMP="$GW_RUNTIME/tmp"
    export XDG_CACHE_HOME="$GW_RUNTIME/xdg-cache" XDG_DATA_HOME="$GW_RUNTIME/xdg-data" XDG_CONFIG_HOME="$GW_RUNTIME/xdg-config"
    unset NPM_CONFIG_CACHE
    export npm_config_cache="$GW_RUNTIME/npm-cache"
    mkdir -p "$TMPDIR"
}

gw_main() {
    set -eE -o pipefail
    gw_parse_arguments "$@"
    if [ "$GW_HELP" -eq 1 ]; then gw_help; return 0; fi
    GW_PHASE='platform checks' GW_LOCK_OWNED=0 GW_WORK=''
    trap gw_cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM HUP
    [ "$(id -u)" -ne 0 ] || { gw_fail 'Run this installer as your normal user, without sudo. Only missing OS prerequisites use sudo.'; return 1; }
    gw_detect_platform
    if [ "$GW_PLATFORM" = linux ]; then
        gw_info "Detected Linux: $GW_DISTRO_ID ($GW_DISTRO_FAMILY family), $GW_ARCH, $GW_LIBC libc."
    else
        gw_info "Detected macOS: $GW_ARCH."
    fi
    GW_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
    local required
    for required in pyproject.toml uv.lock .env.example scripts/gravewright_runner.py scripts/prepare_frontend.py scripts/posix/create_runner.py scripts/posix/runner.sh scripts/posix/mac_tools.sh scripts/posix/mac_build.py gravewright/maps/frontend/package.json gravewright/maps/frontend/package-lock.json gravewright/maps/scripts/build.cjs; do
        [ -f "$GW_ROOT/$required" ] || { gw_fail "The project is incomplete ($required). Extract the entire ZIP first."; return 1; }
    done
    source "$GW_ROOT/scripts/posix/mac_tools.sh"
    gw_local_paths
    if ! mkdir "$GW_RUNTIME/prepare.lock" 2>/dev/null; then
        gw_fail "Another installer may be preparing this installation. If an earlier process was interrupted, check the PID in $GW_RUNTIME/prepare.lock/pid and remove that lock directory after it has stopped."; return 1
    fi
    GW_LOCK_OWNED=1
    printf '%s\n' "$$" > "$GW_RUNTIME/prepare.lock/pid"
    GW_WORK=$(mktemp -d "$GW_RUNTIME/work.XXXXXXXX")
    GW_PHASE='system prerequisites'
    gw_prerequisites
    cd -- "$GW_ROOT"
    # Process-local isolation: never edit shell profiles, global PATH or Python.
    unset VIRTUAL_ENV PYTHONHOME PYTHONPATH NODE_OPTIONS NODE_PATH UV_PROJECT UV_PYTHON UV_SYSTEM_PYTHON UV_MANAGED_PYTHON UV_NO_MANAGED_PYTHON UV_FROZEN UV_NO_SYNC UV_WORKING_DIR UV_CONFIG_FILE UV_PROJECT_ENVIRONMENT UV_PYTHON_INSTALL_DIR UV_PYTHON_BIN_DIR UV_PYTHON_INSTALL_MIRROR UV_PYTHON_DOWNLOADS_JSON_URL
    gw_cache_environment
    export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
    GW_PHASE='uv'; gw_info '[1/7] Checking uv...'; gw_resolve_uv; export GW_UV; "$GW_UV" --version
    GW_PHASE='Python 3.14'; gw_info '[2/7] Checking Python 3.14...'; gw_resolve_python; "$GW_BASE_PYTHON" --version
    GW_CHECKOUT=$("$GW_BASE_PYTHON" -I -c 'import hashlib,os,sys; print(hashlib.sha256(os.fsencode(sys.argv[1])).hexdigest()[:20])' "$GW_ROOT")
    export UV_PROJECT_ENVIRONMENT="$GW_RUNTIME/environments/$GW_CHECKOUT"
    GW_FRONTEND_STATE="$GW_RUNTIME/frontend/$GW_CHECKOUT"
    GW_PHASE='Node.js/npm'; gw_info '[3/7] Checking Node.js and npm...'; gw_resolve_node
    export PATH="${GW_NODE%/*}:$PATH"
    "$GW_NODE" --version; "$GW_NODE" "$GW_NPM" --version
    GW_PHASE='macOS build tools'; gw_mac_prepare_build_tools
    GW_PHASE='locked Python dependencies'; gw_info '[4/7] Installing/checking locked Python dependencies...'
    "$GW_UV" --no-config sync --project "$GW_ROOT" --locked --no-dev --no-python-downloads --python "$GW_BASE_PYTHON"
    GW_PYTHON="$UV_PROJECT_ENVIRONMENT/bin/python"
    [ -x "$GW_PYTHON" ] || { gw_fail 'The private Python environment was not created.'; return 1; }
    GW_PHASE='frontend dependencies and assets'; gw_info '[5/7] Checking npm dependencies and frontend assets...'
    "$GW_PYTHON" -X utf8 scripts/prepare_frontend.py --node "$GW_NODE" --npm-cli "$GW_NPM" --state-dir "$GW_FRONTEND_STATE"
    GW_PHASE='personal configuration and default marketplace'; gw_info '[6/7] Configuring the project and default marketplace...'
    if [ "$GW_CHECK" -eq 0 ]; then "$GW_PYTHON" -X utf8 scripts/gravewright_runner.py --data-dir "$GW_DATA" --configure-default-marketplace; fi
    GW_PHASE='database check and launcher generation'; gw_info '[7/7] Checking the database and generating Gravewright Runner...'
    local check_args=(--data-dir "$GW_DATA" --check) launcher_args=(--data-dir "$GW_DATA")
    if [ -n "$GW_PORT" ]; then check_args+=(--port "$GW_PORT"); fi
    "$GW_PYTHON" -X utf8 scripts/gravewright_runner.py "${check_args[@]}"
    "$GW_PYTHON" -X utf8 scripts/posix/create_runner.py "${launcher_args[@]}"
    gw_info 'Installation complete. Open Gravewright Runner to start.'
}

# Sourcing exposes pure helpers to offline tests; entrypoints always execute main.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then gw_main "$@"; fi
