import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def test_scene_runtime_core_runtime_harness():
    result=subprocess.run(["node","tests/js/semantic_runtime_harness.js"],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert "scene-runtime runtime harness: ok" in result.stdout

def test_semantic_pointer_host_harness():
    result=subprocess.run(["node","tests/js/semantic_pointer_host_harness.js"],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert "semantic pointer host harness: ok" in result.stdout

def test_input_command_runtime_harness():
    result=subprocess.run(["node","tests/js/input_command_runtime_harness.js"],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert "input command runtime harness: ok" in result.stdout
