"""Runner frontend preparation: reuse, repairs, failed builds and literal paths."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from scripts import prepare_frontend as frontend


class FrontendPreparationTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='Gravewright & (frontend) ! ç ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / frontend.FRONTEND
        self.source.mkdir(parents=True)
        (self.source / 'package.json').write_text('{"name":"test"}', encoding='utf-8')
        self.lock = {'packages': {'': {}, 'node_modules/esbuild': {'version': '1.0.0'},
                                 'node_modules/other-platform': {'version': '1.0.0', 'optional': True}}}
        self.write_lock()
        (self.source / 'entry.js').write_text('export const value = 1;', encoding='utf-8')
        script = self.root / 'gravewright/maps/scripts/build.cjs'
        script.parent.mkdir(parents=True)
        script.write_text('// build', encoding='utf-8')
        self.state = self.root / 'private state'
        self.output = 'gravewright/maps/static/gravewright_maps/vendor/board.js'
        self.external_input = self.root / 'gravewright/pdf_system/sheet-shape.js'
        self.external_input.parent.mkdir(parents=True)
        self.external_input.write_text('// schema', encoding='utf-8')
        self.node = self.root / 'Node & tools' / 'node.exe'
        self.npm = self.node.parent / 'node_modules/npm/bin/npm-cli.js'
        self.calls = []
        self.native_healthy = True
        self.fail_build = False
        self.mock_run = patch.object(frontend.subprocess, 'run', side_effect=self.command)
        self.mock_run.start()
        self.addCleanup(self.mock_run.stop)

    def write_lock(self):
        (self.source / 'package-lock.json').write_text(json.dumps(self.lock), encoding='utf-8')

    def install(self):
        package = self.source / 'node_modules/esbuild/package.json'
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text(json.dumps(self.lock['packages']['node_modules/esbuild']), encoding='utf-8')
        self.native_healthy = True

    def command(self, arguments, **kwargs):
        self.assertEqual(arguments[0], str(self.node))
        self.assertFalse(kwargs.get('shell', False))
        self.assertEqual(kwargs['cwd'], self.source)
        self.assertEqual(kwargs['env']['PATH'].split(os.pathsep)[0], str(self.node.parent))
        self.calls.append(arguments[1:])
        if arguments[1:] == ['--version']:
            return subprocess.CompletedProcess(arguments, 0, 'v24.19.0\n')
        if arguments[1:] == [str(self.npm), '--version']:
            return subprocess.CompletedProcess(arguments, 0, '11.17.0\n')
        if arguments[1] == '-e':
            return subprocess.CompletedProcess(arguments, 0 if self.native_healthy else 1, '')
        if arguments[2] == 'ci':
            self.assertIn('--include=dev', arguments)
            self.assertIn('--include=optional', arguments)
            self.install()
        elif arguments[2:] == ['run', 'build']:
            if self.fail_build:
                raise subprocess.CalledProcessError(1, arguments)
            output = self.root / self.output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text('built assets', encoding='utf-8')
            Path(kwargs['env']['GRAVEWRIGHT_BUILD_MANIFEST']).write_text(json.dumps({
                'outputs': [self.output], 'inputs': [self.external_input.relative_to(self.root).as_posix()],
            }), encoding='utf-8')
        else:
            self.fail(f'Unexpected command: {arguments}')
        return subprocess.CompletedProcess(arguments, 0, '')

    def prepare(self):
        frontend.prepare(self.root, self.node, self.npm, self.state)

    def mutation_commands(self):
        return [call[1:] for call in self.calls if call[0] == str(self.npm) and call[1] != '--version']

    def test_first_launch_installs_builds_then_reuses_without_changing_environment(self):
        environment = os.environ.copy()
        lock = (self.source / 'package-lock.json').read_bytes()
        self.prepare()
        self.assertEqual(len(self.mutation_commands()), 2)
        self.calls.clear()
        self.prepare()
        self.assertEqual(self.mutation_commands(), [])
        self.assertEqual(os.environ.copy(), environment)
        self.assertEqual((self.source / 'package-lock.json').read_bytes(), lock)

    def test_existing_compatible_dependencies_are_reused_on_first_launch(self):
        self.install()
        self.prepare()
        self.assertEqual(self.mutation_commands(), [['run', 'build']])

    def test_source_added_changed_or_removed_rebuilds_without_reinstalling(self):
        self.prepare()
        extra = self.source / 'extra.js'
        for content in ('// new', '// changed', None):
            self.calls.clear()
            if content is None:
                extra.unlink()
            else:
                extra.write_text(content, encoding='utf-8')
            self.prepare()
            self.assertEqual(self.mutation_commands(), [['run', 'build']])

    def test_missing_or_changed_bundle_is_repaired(self):
        self.prepare()
        for missing in (True, False):
            self.calls.clear()
            output = self.root / self.output
            if missing:
                output.unlink()
            else:
                output.write_text('damaged', encoding='utf-8')
            self.prepare()
            self.assertEqual(self.mutation_commands(), [['run', 'build']])
            self.assertEqual(output.read_text(encoding='utf-8'), 'built assets')

    def test_lock_change_reinstalls_even_when_package_metadata_is_current(self):
        self.prepare()
        self.calls.clear()
        self.lock['packages']['node_modules/esbuild']['integrity'] = 'new-lock-input'
        self.write_lock()
        self.prepare()
        self.assertEqual(len(self.mutation_commands()), 2)

    def test_missing_package_or_broken_native_esbuild_is_reinstalled(self):
        self.prepare()
        for missing in (True, False):
            self.calls.clear()
            if missing:
                (self.source / 'node_modules/esbuild/package.json').unlink()
            else:
                self.native_healthy = False
            self.prepare()
            self.assertEqual(len(self.mutation_commands()), 2)

    def test_failed_build_is_not_cached_and_next_launch_retries(self):
        self.prepare()
        original = (self.state / 'state.json').read_bytes()
        (self.source / 'entry.js').write_text('// changed', encoding='utf-8')
        self.fail_build = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertEqual((self.state / 'state.json').read_bytes(), original)
        self.fail_build = False
        self.calls.clear()
        self.prepare()
        self.assertEqual(self.mutation_commands(), [['run', 'build']])

    def test_corrupt_state_rebuilds_and_reuses_valid_dependencies(self):
        self.prepare()
        (self.state / 'state.json').write_text('incomplete json', encoding='utf-8')
        self.calls.clear()
        self.prepare()
        self.assertEqual(self.mutation_commands(), [['run', 'build']])

    def test_concurrent_preparation_stops_before_running_npm(self):
        self.state.mkdir()
        with frontend.preparation_lock(self.state):
            with self.assertRaisesRegex(RuntimeError, 'Another Runner'):
                self.prepare()
        self.assertEqual(self.calls, [])

    def test_inherited_uppercase_npm_settings_cannot_override_local_installation(self):
        with patch.dict(os.environ, {'NPM_CONFIG_GLOBAL': 'true', 'NPM_CONFIG_SCRIPT_SHELL': 'unexpected-shell'}):
            self.prepare()
        for call in frontend.subprocess.run.call_args_list:
            environment = call.kwargs['env']
            self.assertNotIn('NPM_CONFIG_GLOBAL', environment)
            self.assertNotIn('NPM_CONFIG_SCRIPT_SHELL', environment)
            self.assertEqual(environment['npm_config_global'], 'false')

    def test_import_outside_frontend_directory_invalidates_build(self):
        self.prepare()
        self.calls.clear()
        self.external_input.write_text('// changed schema', encoding='utf-8')
        self.prepare()
        self.assertEqual(self.mutation_commands(), [['run', 'build']])

    def test_batch_plan_and_record_handoff_never_runs_npm_mutations(self):
        self.assertEqual(frontend.prepare(self.root, self.node, self.npm, self.state, mode='plan'), 10)
        self.assertEqual(self.mutation_commands(), [])
        self.assertFalse((self.state / 'state.json').exists())
        self.install()  # The batch file runs npm ci between helper calls.
        self.assertEqual(frontend.prepare(self.root, self.node, self.npm, self.state, mode='plan'), 11)
        output = self.root / self.output
        output.parent.mkdir(parents=True)
        output.write_text('built by external npm command', encoding='utf-8')
        (self.state / 'build-outputs.json').write_text(json.dumps({
            'outputs': [self.output], 'inputs': [self.external_input.relative_to(self.root).as_posix()],
        }), encoding='utf-8')
        self.assertEqual(frontend.prepare(self.root, self.node, self.npm, self.state, mode='record'), 0)
        self.assertEqual(frontend.prepare(self.root, self.node, self.npm, self.state, mode='plan'), 0)
        self.assertEqual(self.mutation_commands(), [])

    def test_batch_plan_discards_old_manifest_before_external_build(self):
        self.prepare()
        previous = (self.state / 'state.json').read_bytes()
        self.calls.clear()
        (self.source / 'entry.js').write_text('// needs rebuilding', encoding='utf-8')
        self.assertTrue((self.state / 'build-outputs.json').exists())
        self.assertEqual(frontend.prepare(self.root, self.node, self.npm, self.state, mode='plan'), 11)
        self.assertFalse((self.state / 'build-outputs.json').exists())
        with self.assertRaises(FileNotFoundError):
            frontend.prepare(self.root, self.node, self.npm, self.state, mode='record')
        self.assertEqual((self.state / 'state.json').read_bytes(), previous)
        self.assertEqual(self.mutation_commands(), [])

    def test_batch_record_rejects_incomplete_dependencies_and_missing_outputs(self):
        with self.assertRaisesRegex(RuntimeError, 'dependencies are incomplete'):
            frontend.prepare(self.root, self.node, self.npm, self.state, mode='record')
        self.install()
        (self.state / 'build-outputs.json').write_text(json.dumps({
            'outputs': [self.output], 'inputs': [],
        }), encoding='utf-8')
        with self.assertRaises(FileNotFoundError):
            frontend.prepare(self.root, self.node, self.npm, self.state, mode='record')
        self.assertFalse((self.state / 'state.json').exists())
        self.assertEqual(self.mutation_commands(), [])

    def test_batch_record_rejects_manifest_output_outside_project(self):
        self.install()
        self.state.mkdir()
        (self.state / 'build-outputs.json').write_text(json.dumps({
            'outputs': ['../../static/outside.js'], 'inputs': [],
        }), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'invalid output path'):
            frontend.prepare(self.root, self.node, self.npm, self.state, mode='record')
        self.assertFalse((self.state / 'state.json').exists())
        self.assertEqual(self.mutation_commands(), [])
