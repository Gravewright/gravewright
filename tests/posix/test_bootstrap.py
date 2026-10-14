"""Offline POSIX bootstrap regressions; no network, sudo, tools or app install.

Run ``python -m unittest discover -s tests/posix -p test_bootstrap.py -v``.
On Windows, Git Bash can validate the same helpers without emulating a host OS.
The native installation/startup smoke lives separately in ``smoke.py``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tarfile
import unittest
from unittest.mock import patch


def load_mac_helper():
    spec = importlib.util.spec_from_file_location('gravewright_mac_build', ROOT / 'scripts/posix/mac_build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / 'scripts/posix/install.sh'
BASH = shutil.which('bash')
if os.name == 'nt':
    git_bash = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe'
    if git_bash.is_file():
        BASH = str(git_bash)


def shell_path(path):
    value = Path(path).resolve().as_posix()
    if os.name == 'nt' and len(value) > 2 and value[1] == ':':
        return '/' + value[0].lower() + value[2:]
    return value


@unittest.skipUnless(BASH, 'Bash is required; use native Linux/macOS or Git Bash.')
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'data').mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix='posix bootstrap ç ', dir=ROOT / 'data')
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)

    def run_shell(self, code, *, expected=0, environment=None):
        env = os.environ.copy()
        env.pop('GW_INSTALL_EXPECT_OS', None)
        env.update({'GW_BOOTSTRAP': shell_path(BOOTSTRAP), 'GW_TEST_WORK': shell_path(self.work),
                    'GW_MAC_TOOLS': shell_path(ROOT / 'scripts/posix/mac_tools.sh'),
                    'MSYS2_ARG_CONV_EXCL': '*'})
        env.update(environment or {})
        result = subprocess.run([BASH, '-c', 'set -e; source "$GW_BOOTSTRAP"; source "$GW_MAC_TOOLS"; ' + code],
                                cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=20)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def write_executable(self, name, content):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/bash\n' + content, encoding='utf-8', newline='\n')
        path.chmod(0o700)
        return shell_path(path)

    def test_entrypoints_are_valid_lf_shell_scripts(self):
        for name in ('Install Linux.sh', 'Install macOS.command', 'scripts/posix/install.sh', 'scripts/posix/mac_tools.sh'):
            with self.subTest(name=name):
                raw = (ROOT / name).read_bytes()
                self.assertTrue(raw.startswith(b'#!/bin/bash\n'))
                self.assertNotIn(b'\r', raw)
                result = subprocess.run([BASH, '-n', shell_path(ROOT / name)], cwd=ROOT,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_exits_without_platform_or_installation(self):
        for name in ('Install Linux.sh', 'Install macOS.command'):
            with self.subTest(name=name):
                result = subprocess.run([BASH, shell_path(ROOT / name), '--help'], cwd=self.work,
                                        capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('Installation never starts the server', result.stdout)
                self.assertEqual(list(self.work.iterdir()), [])

    def test_argument_values_preserve_spaces_unicode_and_shell_metacharacters(self):
        value = "characters ç ' $(touch NEVER) & ! % data"
        output = self.run_shell('gw_parse_arguments --check --data-dir "$GW_TEST_DATA" --port 00042 --no-browser; '
                                'printf "%s\\n" "$GW_DATA" "$GW_PORT" "$GW_CHECK" "$GW_NO_PAUSE" "$GW_NO_BROWSER"',
                                environment={'GW_TEST_DATA': value})
        self.assertEqual(output.splitlines(), [value, '42', '1', '1', '1'])
        self.assertFalse((ROOT / 'NEVER').exists())

    def test_default_and_relative_storage_stay_in_project_despite_home_and_caller(self):
        project = self.work / 'Extracted project ç with spaces'
        project.mkdir()
        for tools, data in [('', ''), ('private tools', 'private state')]:
            with self.subTest(tools=tools, data=data):
                output = self.run_shell('cd /; GW_ROOT="$GW_TEST_ROOT"; GW_DATA="$GW_TEST_DATA"; '
                                        'gw_local_paths; gw_cache_environment; '
                                        'printf "%s\\n" "$GW_RUNTIME" "$GW_DATA" "$UV_CACHE_DIR" '
                                        '"$UV_PYTHON_INSTALL_DIR" "$npm_config_cache" "$CARGO_HOME" "$TMPDIR"',
                                        environment={'GW_TEST_ROOT': shell_path(project), 'GW_TEST_DATA': data,
                                                     'GRAVEWRIGHT_RUNNER_ROOT': tools, 'HOME': '/unused-home',
                                                     'XDG_DATA_HOME': '/unused-xdg'})
                expected_tools = shell_path(project / (tools or 'data/runner'))
                expected_data = shell_path(project / (data or 'data'))
                self.assertEqual(output.splitlines(), [expected_tools, expected_data,
                                 expected_tools + '/cache', expected_tools + '/python',
                                 expected_tools + '/npm-cache', expected_tools + '/cargo', expected_tools + '/tmp'])

    def test_resolvers_do_not_search_external_uv_node_rust_or_openssl(self):
        output = self.run_shell('GW_RUNTIME="$GW_TEST_WORK/runtime"; GW_PLATFORM=linux GW_ARCH=x64 GW_LIBC=gnu; '
                                'type() { touch "$GW_TEST_WORK/external-search"; exit 99; }; '
                                'gw_try_uv() { return 0; }; gw_try_node() { return 0; }; '
                                'gw_resolve_uv; gw_resolve_node; '
                                'gw_mac_pins; gw_mac_manifest() { return 0; }; '
                                'gw_mac_try_rust() { return 0; }; gw_mac_try_openssl() { return 0; }; '
                                'gw_mac_resolve_rust; gw_mac_resolve_openssl')
        self.assertFalse((self.work / 'external-search').exists(), output)

    def test_invalid_and_missing_options_fail_before_installation(self):
        for args in ('--port 0', '--port 65536', '--port 12abc', '--port -1', '--port', '--data-dir', '--bogus'):
            with self.subTest(args=args):
                self.run_shell('gw_parse_arguments ' + args, expected=1)

    def test_os_release_families_and_id_like_fallback(self):
        cases = [
            ('ID=ubuntu\nID_LIKE=debian\n', 'ubuntu', 'apt'),
            ('ID=linuxmint\nID_LIKE="ubuntu debian"\n', 'linuxmint', 'apt'),
            ('ID=fedora\n', 'fedora', 'rpm'),
            ('ID=rocky\nID_LIKE="rhel centos fedora"\n', 'rocky', 'rpm'),
            ("ID=opensuse-tumbleweed\nID_LIKE='opensuse suse'\n", 'opensuse-tumbleweed', 'zypper'),
            ('ID=manjaro\nID_LIKE=arch\n', 'manjaro', 'pacman'),
            ('ID=alpine\n', 'alpine', 'apk'),
            ('ID=derivative\nID_LIKE="unknown ubuntu debian"\n', 'derivative', 'apt'),
            ('ID=derivative\r\nID_LIKE="fedora"\r\n', 'derivative', 'rpm'),
        ]
        for text, identifier, family in cases:
            with self.subTest(identifier=identifier, family=family):
                (self.work / 'os-release').write_bytes(text.encode())
                output = self.run_shell('gw_detect_distro "$GW_TEST_WORK/os-release"; '
                                        'printf "%s %s\\n" "$GW_DISTRO_ID" "$GW_DISTRO_FAMILY"')
                self.assertEqual(output.strip(), identifier + ' ' + family)

    def test_os_release_rejects_unknown_missing_and_executable_values(self):
        sentinel = shell_path(self.work / 'injected')
        for text in ('ID=nixos\n', 'NAME=OnlyName\n', f'ID="$(touch {sentinel})"\n',
                     f'ID=ubuntu\nID_LIKE="debian; touch {sentinel}"\n'):
            with self.subTest(text=text):
                (self.work / 'os-release').write_text(text, encoding='utf-8')
                self.run_shell('gw_detect_distro "$GW_TEST_WORK/os-release"', expected=1)
                self.assertFalse((self.work / 'injected').exists())

    def test_os_release_ignores_other_fields_without_executing_them(self):
        (self.work / 'os-release').write_text('NAME="$(touch injected)"\nID=debian\n', encoding='utf-8')
        output = self.run_shell('gw_detect_distro "$GW_TEST_WORK/os-release"; printf "%s" "$GW_DISTRO_FAMILY"')
        self.assertEqual(output, 'apt')
        self.assertFalse((ROOT / 'injected').exists())

    def test_uv_minimum_and_stable_versions(self):
        for version, compatible in [('0.11.9', False), ('0.12.0', True), ('0.12.13', True),
                                    ('0.13.0', True), ('1.0.0', True), ('0.12.1rc1', False), ('bad', False)]:
            with self.subTest(version=version):
                candidate = self.write_executable('mock-uv', "printf '%s\\n' " + shlex.quote('uv ' + version) + '\n')
                self.run_shell('gw_try_uv "$GW_TEST_UV"', expected=0 if compatible else 1,
                               environment={'GW_TEST_UV': candidate})

    def test_python_lookup_uses_uv_canonical_macos_os_name(self):
        for platform, architecture, libc, key in [
            ('darwin', 'aarch64', 'none', 'cpython-3.14-macos-aarch64-none'),
            ('darwin', 'x86_64', 'none', 'cpython-3.14-macos-x86_64-none'),
            ('linux', 'x86_64', 'gnu', 'cpython-3.14-linux-x86_64-gnu'),
            ('linux', 'aarch64', 'musl', 'cpython-3.14-linux-aarch64-musl'),
        ]:
            with self.subTest(key=key):
                output = self.run_shell(f'GW_PLATFORM={platform} GW_UV_ARCH={architecture} GW_LIBC={libc}; '
                                        'gw_find_python() { return 0; }; gw_resolve_python; printf "%s" "$GW_PYTHON_KEY"')
                self.assertEqual(output, key)

    def test_node_architecture_platform_and_npm_requirements(self):
        npm = self.work / 'node/lib/node_modules/npm/bin/npm-cli.js'
        npm.parent.mkdir(parents=True)
        npm.write_text('// offline fixture\n')
        for version, arch, platform, npm_version, compatible in [
            ('v22.0.0', 'x64', 'linux', '10.0.0', True),
            ('v24.19.0', 'x64', 'linux', '11.6.0', True),
            ('v20.0.0', 'x64', 'linux', '10.0.0', False),
            ('v26.0.0', 'x64', 'linux', '11.0.0', False),
            ('v24.0.0', 'arm64', 'linux', '10.0.0', False),
            ('v24.0.0', 'x64', 'darwin', '10.0.0', False),
            ('v24.0.0', 'x64', 'linux', '9.0.0', False),
        ]:
            with self.subTest(version=version, arch=arch, platform=platform, npm=npm_version):
                content = ('case "$*" in\n'
                           f' --version) printf "%s\\n" {shlex.quote(version)} ;;\n'
                           f' "-p process.arch") printf "%s\\n" {shlex.quote(arch)} ;;\n'
                           f' "-p process.platform") printf "%s\\n" {shlex.quote(platform)} ;;\n'
                           ' "-p process.execPath") printf "%s\\n" "$0" ;;\n'
                           f' *npm-cli.js*) printf "%s\\n" {shlex.quote(npm_version)} ;;\n'
                           ' *) exit 1 ;;\nesac\n')
                candidate = self.write_executable('node/bin/node', content)
                self.run_shell('GW_ARCH=x64 GW_PLATFORM=linux GW_BASE_PYTHON=/nonexistent; gw_try_node "$GW_TEST_NODE"',
                               expected=0 if compatible else 1, environment={'GW_TEST_NODE': candidate})

    def test_all_archives_have_pinned_sha256_and_musl_has_no_glibc_node_fallback(self):
        for platform, arch, libc in [('linux', 'x64', 'gnu'), ('linux', 'arm64', 'gnu'),
                                     ('linux', 'x64', 'musl'), ('linux', 'arm64', 'musl'),
                                     ('darwin', 'x64', 'none'), ('darwin', 'arm64', 'none')]:
            with self.subTest(platform=platform, arch=arch, libc=libc):
                setup = f'GW_PLATFORM={platform} GW_ARCH={arch} GW_LIBC={libc}; '
                output = self.run_shell(setup + 'gw_uv_archive; printf "%s\\n" "$GW_UV_TARGET" "$GW_UV_SHA"')
                target, digest = output.strip().splitlines()
                self.assertRegex(digest, r'^[0-9a-f]{64}$')
                self.assertIn('apple-darwin' if platform == 'darwin' else 'linux-' + libc, target)
                if libc == 'musl':
                    output = self.run_shell(setup + 'gw_node_archive', expected=1)
                    self.assertIn('no official Node.js binary', output)
                else:
                    output = self.run_shell(setup + 'gw_node_archive; printf "%s" "$GW_NODE_SHA"')
                    self.assertRegex(output, r'^[0-9a-f]{64}$')

    def test_download_verifies_sha_and_restricts_https_redirects(self):
        digest = hashlib.sha256(b'offline verified payload').hexdigest()
        code = ('curl() { printf "%s\\n" "$@" > "$GW_TEST_WORK/curl-args"; '
                'while [ "$#" -gt 0 ]; do if [ "$1" = --output ]; then shift; printf "%s" "offline verified payload" > "$1"; break; fi; shift; done; }; '
                'gw_download https://example.test/pinned "$GW_TEST_WORK/archive" "$GW_TEST_SHA"')
        self.run_shell(code, environment={'GW_TEST_SHA': digest})
        args = (self.work / 'curl-args').read_text().splitlines()
        self.assertEqual(args[args.index('--proto') + 1], '=https')
        self.assertEqual(args[args.index('--proto-redir') + 1], '=https')
        self.run_shell(code, expected=1, environment={'GW_TEST_SHA': '0' * 64})
        self.run_shell('curl() { return 99; }; gw_download http://example.test/file "$GW_TEST_WORK/archive" ignored', expected=1)

    def test_failed_download_cannot_reuse_an_existing_matching_file(self):
        archive = self.work / 'archive'
        archive.write_bytes(b'previous download')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.run_shell('curl() { return 22; }; if gw_download https://example.test/file "$GW_TEST_WORK/archive" "$GW_TEST_SHA"; then exit 0; else exit 1; fi',
                       expected=1, environment={'GW_TEST_SHA': digest})

    def test_mac_arm_uses_optional_pure_python_autobahn_without_intel_tools(self):
        output = self.run_shell('GW_PLATFORM=darwin GW_ARCH=arm64; '
                                'gw_mac_require_clt() { exit 99; }; gw_mac_resolve_rust() { exit 98; }; '
                                'gw_mac_prepare_build_tools; printf "%s" "$AUTOBAHN_USE_NVX"')
        self.assertEqual(output, '0')

    def test_non_mac_does_not_prepare_mac_tools_or_change_autobahn(self):
        output = self.run_shell('GW_PLATFORM=linux AUTOBAHN_USE_NVX=unchanged; '
                                'gw_mac_require_clt() { exit 99; }; gw_mac_prepare_build_tools; '
                                'printf "%s" "$AUTOBAHN_USE_NVX"')
        self.assertEqual(output, 'unchanged')

    def test_unattended_missing_clt_fails_without_opening_an_apple_dialog(self):
        output = self.run_shell('GW_CHECK=1; gw_mac_clt_available() { return 1; }; '
                                'xcode-select() { touch "$GW_TEST_WORK/dialog-opened"; }; '
                                'gw_mac_require_clt', expected=1)
        self.assertIn('xcode-select --install', output)
        self.assertIn('Homebrew is not required', output)
        self.assertFalse((self.work / 'dialog-opened').exists())

    def test_rust_compatible_versions_require_native_host_and_standard_library(self):
        (self.work / 'rust/lib').mkdir(parents=True)
        (self.work / 'rust/lib/libstd-fixture.rlib').write_text('standard library fixture')
        rust_root = shell_path(self.work / 'rust')
        self.write_executable('rust/bin/cargo', "printf '%s\\n' 'cargo 1.99.0 (offline)'\n")
        for version, host, compatible in [('1.82.0', 'x86_64-apple-darwin', False),
                                          ('1.83.0', 'x86_64-apple-darwin', True),
                                          ('1.99.0', 'x86_64-apple-darwin', True),
                                          ('1.99.0-nightly', 'x86_64-apple-darwin', False),
                                          ('1.99.0', 'aarch64-apple-darwin', False)]:
            with self.subTest(version=version, host=host):
                content = ('case "$*" in\n'
                           f' "--version --verbose") printf "%s\\n" {shlex.quote("release: " + version)} {shlex.quote("host: " + host)} ;;\n'
                           f' "--print sysroot") printf "%s\\n" {shlex.quote(rust_root)} ;;\n'
                           f' "--print target-libdir") printf "%s\\n" {shlex.quote(rust_root + "/lib")} ;;\n'
                           ' *) exit 1 ;;\nesac\n')
                candidate = self.write_executable('rust/bin/rustc', content)
                self.run_shell('gw_mac_pins; gw_mac_try_rust "$GW_TEST_RUSTC"',
                               expected=0 if compatible else 1, environment={'GW_TEST_RUSTC': candidate})

    def test_mac_download_cache_reuses_only_verified_archives(self):
        content = b'verified mac archive'
        (self.work / 'archive').write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        self.run_shell('UV_OFFLINE=1; gw_download() { exit 99; }; '
                       'gw_mac_cached_download https://example.test/archive "$GW_TEST_WORK/archive" "$GW_TEST_SHA"',
                       environment={'GW_TEST_SHA': digest})
        self.run_shell('UV_OFFLINE=1; gw_download() { exit 99; }; '
                       'gw_mac_cached_download https://example.test/archive "$GW_TEST_WORK/archive" invalid', expected=1)

    def test_mac_component_pins_are_complete_and_stable(self):
        output = self.run_shell('gw_mac_pins; printf "%s\\n" "$GW_RUST_VERSION" "$GW_RUSTC_SHA" '
                                '"$GW_CARGO_SHA" "$GW_RUST_STD_SHA" "$GW_OPENSSL_VERSION" "$GW_OPENSSL_SHA"')
        lines = output.splitlines()
        self.assertEqual(lines[0], '1.99.0')
        self.assertEqual(lines[4], '3.5.9')
        for digest in lines[1:4] + lines[5:]:
            self.assertRegex(digest, '^[0-9a-f]{64}$')


class MacPrivateManifestTests(unittest.TestCase):
    def setUp(self):
        self.mac = load_mac_helper()
        self.directory = tempfile.TemporaryDirectory(prefix='mac build fixture ç ')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        for name in ('bin/openssl', 'lib/libssl.a', 'lib/libcrypto.a',
                     'include/openssl/opensslv.h', 'share/doc/openssl/LICENSE.txt'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('verified fixture\n', encoding='utf-8')

    def test_verified_private_build_detects_changed_missing_and_extra_files(self):
        self.mac.record(self.root, 'openssl', '3.5.9')
        self.mac.verify(self.root, 'openssl', '3.5.9')
        target = self.root / 'lib/libcrypto.a'
        target.write_text('changed bytes')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.mac.verify(self.root, 'openssl', '3.5.9')
        target.write_text('verified fixture\n')
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.mac.verify(self.root, 'openssl', '3.5.9')
        target.write_text('verified fixture\n')
        (self.root / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.mac.verify(self.root, 'openssl', '3.5.9')

    def test_manifest_requires_notices_and_matching_version(self):
        self.mac.record(self.root, 'openssl', '3.5.9')
        with self.assertRaisesRegex(ValueError, 'pinned version'):
            self.mac.verify(self.root, 'openssl', '3.5.8')
        (self.root / 'share/doc/openssl/LICENSE.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.mac.record(self.root, 'openssl', '3.5.9')

    def test_static_probe_compiles_literal_paths_and_checks_both_libraries(self):
        observed = []
        def compile(arguments, **kwargs):
            observed.append(arguments)
        with patch.object(self.mac.subprocess, 'run', side_effect=compile), \
                patch.object(self.mac.subprocess, 'check_output', return_value='OpenSSL 3.5.9\n'), \
                patch.dict(os.environ, {'GRAVEWRIGHT_RUNNER_ROOT': str(self.root / 'runner tools with spaces')}):
            self.mac.probe_openssl(self.root, Path('/usr/bin/clang'), Path('/fake SDK'))
        command = observed[0]
        self.assertIn(str(self.root / 'lib/libssl.a'), command)
        self.assertIn(str(self.root / 'lib/libcrypto.a'), command)
        self.assertIn(str(self.root / 'include'), command)
        self.assertIn('/fake SDK' if os.name != 'nt' else '\\fake SDK', command)
        source = Path(command[command.index('-I') + 2])
        self.assertTrue(source.is_relative_to(self.root / 'runner tools with spaces/tmp'))

    @unittest.skipIf(os.name == 'nt', 'Runs verified POSIX component installers in an isolated temporary prefix')
    def test_rust_component_install_uses_prefix_without_spaces_then_relocates_and_keeps_notices(self):
        archives, hashes = [], []
        targets = {'rustc': 'bin/rustc', 'cargo': 'bin/cargo',
                   'rust-std': 'lib/rustlib/x86_64-apple-darwin/lib/libstd-fixture.rlib'}
        for component, target in targets.items():
            archive = self.root / (component + '.tar.gz')
            folder = f'{component}-1.99.0-x86_64-apple-darwin'
            script = ('#!/bin/sh\nset -eu\nprefix=${1#--prefix=}\n'
                      'case "$prefix" in *" "*) exit 72 ;; esac\n'
                      f'mkdir -p "$prefix/{str(Path(target).parent)}"\n'
                      f'printf fixture > "$prefix/{target}"\n')
            with tarfile.open(archive, 'w:gz') as stream:
                for name, content in [('install.sh', script), ('LICENSE-MIT', 'preserve component license')]:
                    data = content.encode()
                    info = tarfile.TarInfo(folder + '/' + name)
                    info.mode = 0o755 if name.endswith('.sh') else 0o644
                    info.size = len(data)
                    stream.addfile(info, io.BytesIO(data))
            archives.append(archive)
            hashes.append(self.mac.digest(archive))
        destination = self.root / 'Private Rust tools ã with spaces'
        self.mac.install_rust(archives, hashes, destination, '1.99.0')
        for component, target in targets.items():
            self.assertTrue((destination / target).is_file())
            self.assertEqual((destination / 'share/doc/gravewright-rust' / component / 'LICENSE-MIT').read_text(),
                             'preserve component license')
        self.mac.record(destination, 'rust', '1.99.0')
        self.mac.verify(destination, 'rust', '1.99.0')

    def test_openssl_build_keeps_scratch_local_and_make_targets_relative_for_spaced_paths(self):
        archive = self.root / 'openssl-source.tar.gz'
        folder = 'openssl-3.5.9'
        with tarfile.open(archive, 'w:gz') as stream:
            for name in ('Configure', 'LICENSE.txt', 'apps/openssl.cnf'):
                raw = b'build fixture'
                info = tarfile.TarInfo(folder + '/' + name)
                info.size = len(raw)
                stream.addfile(info, io.BytesIO(raw))
        runtime = self.root / 'local tools with spaces ç'
        stage, final = runtime / 'staging install', runtime / 'openssl final'
        observed = []
        def run(command, **kwargs):
            source = Path(kwargs['cwd'])
            self.assertTrue(source.is_relative_to(runtime / 'tmp'))
            observed.append(command)
            if 'install_sw' in command:
                install = source.parent / 'install'
                (install / 'lib').mkdir(parents=True)
                (install / 'lib/libssl.a').write_bytes(b'static fixture')
        with patch.dict(os.environ, {'GRAVEWRIGHT_RUNNER_ROOT': str(runtime)}), \
                patch.object(self.mac.subprocess, 'run', side_effect=run), \
                patch.object(self.mac, 'probe_openssl') as probe:
            self.mac.build_openssl(archive, self.mac.digest(archive), stage, final, '3.5.9',
                                   Path('/usr/bin/clang'), Path('/fake SDK'), runtime / 'build.log')
        self.assertIn('--prefix=' + str(final.resolve()), observed[0])
        self.assertIn('--openssldir=' + str(final.resolve() / 'ssl'), observed[0])
        for command in observed[1:]:
            self.assertIn('INSTALLTOP=../install', command)
        self.assertNotIn('OPENSSLDIR=../install/ssl', observed[1])
        self.assertIn('OPENSSLDIR=../install/ssl', observed[2])
        self.assertTrue((stage / 'lib/libssl.a').is_file())
        self.assertTrue((stage / 'share/doc/openssl/LICENSE.txt').is_file())
        self.assertTrue((stage / 'ssl/openssl.cnf').is_file())
        self.assertEqual(list((runtime / 'tmp').iterdir()), [])
        probe.assert_called_once_with(stage, Path('/usr/bin/clang'), Path('/fake SDK'))


if __name__ == '__main__':
    unittest.main()
