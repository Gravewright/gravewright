"""Todo script de pacote precisa chamar APIs que o SDK realmente tem, com as
capabilities que o runtime realmente exige.

Por que isto existe: o validador de manifest confere a *forma* do manifest, e os
testes de pacote conferem que os arquivos existem e que os caminhos batem. Nenhum
dos dois executa o script. Então um pacote pode passar em tudo, ser publicado, e
morrer na primeira abertura de ficha com

    Package "x" attempted to use sdk.sheets.register but does not declare
    capability "sheets.runtime".

ou pior, chamar um namespace que nunca existiu (sdk.mappings) e falhar calado.

O teste é dirigido pelas tabelas do próprio SDK — CAPABILITY_REQUIREMENTS em
sdk-capabilities.js e o objeto `namespaces` em gravewright-sdk.js — então ele
acompanha o SDK sozinho, em vez de repetir uma lista que envelhece.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "static/js/sdk/gravewright-sdk.js"
CAPS = ROOT / "static/js/sdk/sdk-capabilities.js"
PACKAGES = ROOT / "data/packages"


def _capability_requirements() -> dict[str, str]:
    """api pontilhada -> capability exigida, lida de sdk-capabilities.js."""
    source = CAPS.read_text(encoding="utf-8")

    constants = dict(re.findall(r"(\w+):\s*\"([\w.]+)\"", source.split("CAPABILITY_REQUIREMENTS")[0]))

    block = source.split("CAPABILITY_REQUIREMENTS = Object.freeze({", 1)[1].split("});", 1)[0]
    requirements: dict[str, str] = {}
    for api, symbol in re.findall(r"\"([\w.]+)\":\s*CAPABILITIES\.(\w+)", block):
        assert symbol in constants, f"CAPABILITIES.{symbol} não existe"
        requirements[api] = constants[symbol]

    assert requirements, "não consegui ler o mapa de capabilities do SDK"
    return requirements


def _sdk_surface() -> dict[str, set[str]]:
    """namespace -> métodos, lido do objeto `namespaces` de gravewright-sdk.js."""
    source = SDK.read_text(encoding="utf-8")
    block = source.split("const namespaces = {", 1)[1]

    surface: dict[str, set[str]] = {}
    current: str | None = None
    depth = 0

    for line in block.splitlines():
        if re.match(r"^        \};\s*$", line) and current is None:
            break

        opener = re.match(r"^            (\w+): (?:Object\.)?freeze\(\{", line)
        scalar = re.match(r"^            (\w+): ", line)

        if opener:
            current = opener.group(1)
            surface.setdefault(current, set())
            depth = 1
            continue
        if current is None and scalar:
            # namespaces escalares (version, kind) não têm métodos
            surface.setdefault(scalar.group(1), set())
            continue

        if current is not None:
            depth += line.count("{") - line.count("}")
            method = re.match(r"^                (?:async )?(\w+)[(:]", line)
            nested = re.match(r"^                (\w+): (?:Object\.)?freeze\(\{", line)
            if nested:
                surface.setdefault(f"{current}.{nested.group(1)}", set())
                surface[current].add(nested.group(1))
            elif method:
                surface[current].add(method.group(1))
            else:
                deep = re.match(r"^                    (?:async )?(\w+)\(", line)
                if deep and surface.get(f"{current}.{_last_nested(surface, current)}") is not None:
                    surface[f"{current}.{_last_nested(surface, current)}"].add(deep.group(1))
            if depth <= 0:
                current = None

    # atalhos ergonômicos definidos fora do literal
    for shortcut in re.findall(r"namespaces\.(\w+) =", source):
        surface.setdefault(shortcut, set())

    # Factory-produced namespaces are public too, even though their methods do
    # not appear inline in the `namespaces` object literal.
    for namespace, factory in re.findall(r"^            (\w+): (createSdk\w+)\(", block, re.MULTILINE):
        factory_start = source.find(f"function {factory}(")
        factory_end = source.find("\n    function ", factory_start + 1)
        factory_source = source[factory_start:factory_end if factory_end >= 0 else len(source)]
        methods = set(re.findall(r"^            (\w+)(?:\([^)]*\)|:) ", factory_source, re.MULTILINE))
        methods.update(re.findall(r"^            (\w+): ", factory_source, re.MULTILINE))
        surface.setdefault(namespace, set()).update(methods)

    assert "sheets" in surface and "registerController" in surface["sheets"], surface.get("sheets")
    return surface


def _last_nested(surface: dict[str, set[str]], parent: str) -> str:
    nested = [key.split(".", 1)[1] for key in surface if key.startswith(f"{parent}.")]
    return nested[-1] if nested else ""


def _package_scripts() -> list[tuple[Path, dict]]:
    found = []
    for manifest_path in PACKAGES.rglob("manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for script in _declared_scripts(manifest):
            script_path = manifest_path.parent / script
            if script_path.is_file():
                found.append((script_path, manifest))
    return found


def _declared_scripts(manifest: dict) -> list[str]:
    scripts: list[str] = []
    for entry in (manifest.get("entrypoints") or {}).values():
        if isinstance(entry, dict):
            scripts.extend(entry.get("scripts") or [])
    return scripts


USES = re.compile(r"\bsdk\.(\w+)(?:\.(\w+))?(?:\.(\w+))?")


@pytest.mark.parametrize(
    "script_path, manifest",
    _package_scripts(),
    ids=lambda value: value.name if isinstance(value, Path) else "",
)
def test_package_script_calls_only_real_sdk_apis(script_path: Path, manifest: dict):
    surface = _sdk_surface()
    source = script_path.read_text(encoding="utf-8")

    for namespace, member, deep in USES.findall(source):
        assert namespace in surface, (
            f"{script_path.name}: sdk.{namespace} não existe "
            f"(namespaces: {sorted(surface)})"
        )
        if not member:
            continue
        nested_key = f"{namespace}.{member}"
        assert member in surface[namespace], (
            f"{script_path.name}: sdk.{namespace}.{member} não existe "
            f"(disponíveis: {sorted(surface[namespace])})"
        )
        if deep and nested_key in surface:
            assert deep in surface[nested_key], (
                f"{script_path.name}: sdk.{nested_key}.{deep} não existe "
                f"(disponíveis: {sorted(surface[nested_key])})"
            )


@pytest.mark.parametrize(
    "script_path, manifest",
    _package_scripts(),
    ids=lambda value: value.name if isinstance(value, Path) else "",
)
def test_package_declares_every_capability_its_script_needs(script_path: Path, manifest: dict):
    requirements = _capability_requirements()
    declared = set(manifest.get("capabilities") or [])
    source = script_path.read_text(encoding="utf-8")

    missing: list[str] = []
    for namespace, member, deep in USES.findall(source):
        for api in (f"{namespace}.{member}.{deep}", f"{namespace}.{member}", namespace):
            capability = requirements.get(api.rstrip("."))
            if capability and capability not in declared:
                missing.append(f"sdk.{api.rstrip('.')} exige '{capability}'")
            if capability:
                break

    assert not missing, (
        f"{script_path.name}: capability faltando no manifest "
        f"(declaradas: {sorted(declared)})\n  " + "\n  ".join(sorted(set(missing)))
    )
