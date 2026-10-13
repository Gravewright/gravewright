"""Offline POSIX bootstrap regressions; no network, sudo, tools or app install.

Run ``python -m unittest discover -s tests/posix -p test_bootstrap.py -v``.
On Windows, Git Bash can validate the same helpers without emulating a host OS.
The native installation/startup smoke lives separately in ``smoke.py``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


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
                    'MSYS2_ARG_CONV_EXCL': '*'})
        env.update(environment or {})
        result = subprocess.run([BASH, '-c', 'set -e; source "$GW_BOOTSTRAP"; ' + code],
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
        for name in ('Install Linux.sh', 'Install macOS.command', 'scripts/posix/install.sh'):
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


if __name__ == '__main__':
    unittest.main()
