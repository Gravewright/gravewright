"""Verify private macOS build tools and build pinned static OpenSSL safely.

Only the Intel installer needs these helpers. Paths stay argv values; OpenSSL's
Makefiles run in a disposable path without spaces and the finished static
installation is copied to the user's chosen directory. No shell, Homebrew,
global tool installation, or runtime downloads are used here.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


MANIFEST = '.gravewright-build-tool.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    root = Path(root).resolve()
    files = {}
    for path in sorted(root.rglob('*')):
        if path.name == MANIFEST:
            continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(root):
                raise ValueError('Private build-tool symlink escapes its directory')
            files[path.relative_to(root).as_posix()] = {'link': os.readlink(path)}
        elif path.is_file():
            files[path.relative_to(root).as_posix()] = {'sha256': digest(path)}
    return files


def required(root, kind):
    names = ('bin/rustc', 'bin/cargo') if kind == 'rust' else (
        'bin/openssl', 'lib/libssl.a', 'lib/libcrypto.a', 'include/openssl/opensslv.h',
        'share/doc/openssl/LICENSE.txt',
    )
    return all((root / name).is_file() for name in names) and (
        kind != 'rust' or any((root / 'lib/rustlib/x86_64-apple-darwin/lib').glob('libstd-*.rlib'))
    )


def record(root, kind, version):
    root = Path(root).resolve()
    if not required(root, kind):
        raise ValueError('The private build-tool installation is incomplete')
    data = {'schema': 1, 'kind': kind, 'version': version, 'files': inventory(root)}
    if not data['files']:
        raise ValueError('The private build-tool installation is empty')
    temporary = root / (MANIFEST + '.tmp')
    temporary.write_text(json.dumps(data, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(root / MANIFEST)


def verify(root, kind, version):
    root = Path(root).resolve()
    data = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    if (data.get('schema'), data.get('kind'), data.get('version')) != (1, kind, version):
        raise ValueError('Private build-tool metadata does not match the pinned version')
    if not required(root, kind) or inventory(root) != data.get('files'):
        raise ValueError('Private build-tool files changed or are incomplete')


def compiler_environment(sdk):
    environment = os.environ.copy()
    for name in ('CC', 'CXX', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'AR', 'RANLIB',
                 'OPENSSL_CONF', 'OPENSSL_MODULES', 'OPENSSL_ENGINES',
                 'OPENSSL_LOCAL_CONFIG_DIR', 'MACOSX_DEPLOYMENT_TARGET',
                 'PKG_CONFIG', 'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR',
                 'PKG_CONFIG_SYSROOT_DIR', 'RUSTC', 'CARGO', 'RUSTFLAGS',
                 'CARGO_ENCODED_RUSTFLAGS', 'RUSTUP_TOOLCHAIN'):
        environment.pop(name, None)
    environment['SDKROOT'] = str(sdk)
    environment['MACOSX_DEPLOYMENT_TARGET'] = '13.5'
    return environment


def probe_openssl(root, clang, sdk):
    root = Path(root).resolve()
    paths = [root / name for name in ('include/openssl/opensslv.h', 'lib/libssl.a', 'lib/libcrypto.a')]
    if not all(path.is_file() for path in paths):
        raise ValueError('Static OpenSSL headers/libraries were not found')
    # Link the actual static libraries, rather than trusting an unrelated CLI.
    with tempfile.TemporaryDirectory(prefix='gravewright-openssl-probe-', dir='/tmp') as name:
        work = Path(name)
        source = work / 'probe.c'
        source.write_text('#include <stdio.h>\n#include <openssl/ssl.h>\n#include <openssl/crypto.h>\n'
                          '#include <openssl/opensslv.h>\nint main(void) { '
                          'if (OPENSSL_VERSION_MAJOR != 3 || OPENSSL_VERSION_MINOR != 5 || OPENSSL_VERSION_PATCH < 9) return 2; '
                          'if (!TLS_method()) return 3; puts(OpenSSL_version(OPENSSL_VERSION)); return 0; }\n')
        executable = work / 'probe'
        subprocess.run([str(clang), '-isysroot', str(sdk), '-mmacosx-version-min=13.5',
                        '-I', str(root / 'include'), str(source), str(root / 'lib/libssl.a'),
                        str(root / 'lib/libcrypto.a'), '-o', str(executable)],
                       check=True, capture_output=True, text=True, env=compiler_environment(sdk))
        output = subprocess.check_output([str(executable)], text=True).strip()
        if not output.startswith('OpenSSL 3.5.'):
            raise ValueError('The linked static OpenSSL has an unexpected version')
        return output


def extract_component(archive, destination, prefix):
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        for member in members:
            path = Path(member.name)
            if not path.parts or path.is_absolute() or '..' in path.parts or path.parts[0] != prefix:
                raise ValueError('Unexpected path in verified build-tool archive')
        stream.extractall(destination, filter='data')
    return Path(destination) / prefix


def install_rust(archives, hashes, root, version):
    if len(archives) != 3 or len(hashes) != 3:
        raise ValueError('Rust installation needs exactly rustc, cargo and rust-std')
    root = Path(root)
    if root.exists():
        raise ValueError('Rust staging destination must be new')
    with tempfile.TemporaryDirectory(prefix='gravewright-rust-install-', dir='/tmp') as name:
        work = Path(name).resolve()
        prefix = work / 'install'
        for component, archive, expected in zip(('rustc', 'cargo', 'rust-std'), archives, hashes, strict=True):
            if digest(archive) != expected:
                raise ValueError('Rust component failed its pinned SHA256 check')
            source = extract_component(archive, work, f'{component}-{version}-x86_64-apple-darwin')
            subprocess.run(['/bin/sh', str(source / 'install.sh'), f'--prefix={prefix}', '--disable-ldconfig'],
                           cwd=source, check=True)
            notices = prefix / 'share/doc/gravewright-rust' / component
            notices.mkdir(parents=True, exist_ok=True)
            for path in source.iterdir():
                if path.is_file() and path.name.startswith(('LICENSE', 'COPYRIGHT', 'NOTICE')):
                    shutil.copy2(path, notices / path.name)
        shutil.copytree(prefix, root, symlinks=True)


def build_openssl(archive, sha256, root, final_root, version, clang, sdk, log):
    if digest(archive) != sha256:
        raise ValueError('OpenSSL source archive failed its pinned SHA256 check')
    root, final_root, log = Path(root), Path(final_root).resolve(), Path(log)
    if root.exists():
        raise ValueError('OpenSSL staging destination must be new')
    log.parent.mkdir(parents=True, exist_ok=True)
    # /tmp is deliberate: a user profile or its runtime directory may contain
    # whitespace, which cannot safely appear in OpenSSL Makefile target names.
    with tempfile.TemporaryDirectory(prefix='gravewright-openssl-build-', dir='/tmp') as name:
        work = Path(name).resolve()
        source = extract_component(archive, work, f'openssl-{version}')
        prefix = work / 'install'
        environment = compiler_environment(sdk)
        environment['CC'] = '/usr/bin/clang'
        commands = [
            ['/usr/bin/perl', 'Configure', 'darwin64-x86_64-cc', 'no-shared', 'no-tests', 'no-module',
             f'--prefix={prefix}', f'--openssldir={final_root / "ssl"}', '--libdir=lib',
             '-mmacosx-version-min=13.5'],
            ['/usr/bin/make', '-j', str(min(os.cpu_count() or 2, 4))],
            ['/usr/bin/make', 'install_sw'],
        ]
        with log.open('w', encoding='utf-8') as output:
            for command in commands:
                output.write('Running: ' + repr(command) + '\n')
                output.flush()
                subprocess.run(command, cwd=source, env=environment, stdout=output,
                               stderr=subprocess.STDOUT, check=True)
        shutil.copytree(prefix, root, symlinks=True)
        notice = root / 'share/doc/openssl/LICENSE.txt'
        notice.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'LICENSE.txt', notice)
        config = root / 'ssl/openssl.cnf'
        config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'apps/openssl.cnf', config)
    probe_openssl(root, clang, sdk)
    print(f'Private static OpenSSL {version} built. Build log: {log}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('operation', choices=('record', 'verify', 'probe-openssl', 'build-openssl', 'install-rust'))
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--kind', choices=('rust', 'openssl'))
    parser.add_argument('--version')
    parser.add_argument('--clang', type=Path)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--archives', nargs=3, type=Path)
    parser.add_argument('--hashes', nargs=3)
    parser.add_argument('--sha256')
    parser.add_argument('--final-root', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    try:
        if args.operation in {'record', 'verify'}:
            if not args.kind or not args.version:
                parser.error('--kind and --version are required for manifest operations')
            (record if args.operation == 'record' else verify)(args.root, args.kind, args.version)
        elif args.operation == 'probe-openssl':
            probe_openssl(args.root, args.clang, args.sdk)
        elif args.operation == 'install-rust':
            install_rust(args.archives, args.hashes, args.root, args.version)
        else:
            build_openssl(args.archive, args.sha256, args.root, args.final_root, args.version,
                          args.clang, args.sdk, args.log)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        if not args.quiet:
            print(f'macOS build-tool preparation failed: {error}', file=sys.stderr)
            if args.log and args.log.is_file():
                print('\n'.join(args.log.read_text(encoding='utf-8', errors='replace').splitlines()[-20:]), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
