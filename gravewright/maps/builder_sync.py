"""Reconcile owned native map edits into their editable builder sources."""

from copy import deepcopy
import math
import uuid

from . import services


KINDS = ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders", "regions")
_MISSING = object()


def conflict():
    raise services.MapError(
        "The same map object was edited in the builder and the VTT. Reload the project before updating it.",
        "conflict")


def inverse_blueprint(value, mapping):
    value = deepcopy(value)

    def source_id(key):
        candidate = mapping.get(key, key)
        try:
            uuid.UUID(candidate)
        except (ValueError, TypeError, AttributeError):
            return key
        return candidate

    for graph in value.get("graphs", {}).values():
        for node in graph.get("nodes", []):
            if node.get("type") in ("light", "lightReference", "reference"):
                node["targetId"] = source_id(node.get("targetId"))
            elif node.get("type") == "teleport":
                node["destinationId"] = source_id(node.get("destinationId"))
            elif node.get("type") == "elementGroup" and node.get("memberType") in ("element", "light"):
                node["targetIds"] = [source_id(key) for key in node.get("targetIds", [])]
    return value


def projection(data, kind, cell, mapping):
    """Expose authored fields, excluding states and artwork changed by play."""
    from .builder_services import NATIVE_EFFECT_FIELDS

    result = {"name": data["name"]} if "name" in data else {}
    if kind == "walls":
        result.update({key: data[key] / cell for key in ("x1", "y1", "x2", "y2")})
        result["presentation"] = data.get("presentation", "normal")
        result["vertical"] = {key: data.get("vertical_" + key) for key in ("bottom", "top")}
        if data.get("kind") != "door":
            result["behavior"] = {key: data.get(key + "_behavior", "block")
                                  for key in ("movement", "vision", "light", "sound")}
            result["discovered"] = data.get("discovered", False)
        else:
            result["assetId"] = data.get("asset_id")
            result["rotationAnchor"] = data.get("rotationAnchor", "center")
            if "thickness" in data:
                result["thickness"] = data["thickness"] / cell
    elif kind == "images":
        if "surface" in data or "surfacePlane" in data:
            return result
        component = data.get("torch", data.get("lever"))
        if isinstance(component, dict):
            width, height = component["width"], component["height"]
            result["assetId"] = component.get("baseAssetId")
        else:
            from .builder_services import ordinary_image_base
            base = ordinary_image_base(data)
            width, height = base["width"], base["height"]
            result["assetId"] = base["assetId"]
        result.update(x=(data["x"] - width / 2) / cell,
                      y=(data["y"] - height / 2) / cell,
                      width=width / cell, height=height / cell,
                      rotation=data.get("torch", {}).get("baseRotation", data.get("rotation", 0)))
    elif kind == "lights":
        result.update(x=data["x"] / cell, y=data["y"] / cell,
                      brightRadius=data["bright_radius"], dimRadius=data["dim_radius"])
        result.update({key: deepcopy(data[key]) for key in
                       ("color", "intensity", "rotation", "angle", "animation", "elevation") if key in data})
    elif kind in NATIVE_EFFECT_FIELDS:
        result.update(x=data["x"] / cell, y=data["y"] / cell)
        result.update({key: deepcopy(data[key]) for key in NATIVE_EFFECT_FIELDS[kind]
                       if key != "enabled" and key in data})
    elif kind == "zones" and "region" in data:
        geometry = data.get("geometry", {})
        if geometry.get("shape") == "rect":
            result.update({key: geometry[key] / cell for key in ("x", "y", "width", "height")})
        result["name"] = data["region"].get("name", "")
        if "filters" in data["region"]:
            result["filters"] = deepcopy(data["region"]["filters"])
        if "vertical" in data:
            result["vertical"] = deepcopy(data["vertical"])
    if "blueprint" in data and not ("surface" in data or "surfacePlane" in data):
        result["blueprint"] = inverse_blueprint(data["blueprint"], mapping)
    return result


def equal(left, right):
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-8)
    return left == right


def component_frame(data, parent, state):
    """Undo only a torch's live quarter-turn, retaining authored transforms."""
    result = deepcopy(data)
    if state == "on":
        dx, dy = data["x"] - parent["x"], data["y"] - parent["y"]
        result["x"], result["y"] = parent["x"] + dy, parent["y"] - dx
        result["rotation"] = (data.get("rotation", 0) - 90) % 360
    return result


def merge_field(before, local, remote):
    """Merge nested authoring properties without replacing disjoint changes."""
    if equal(local, before) or equal(local, remote):
        return deepcopy(remote) if remote is not _MISSING else _MISSING
    if isinstance(before, dict) and isinstance(local, dict) and isinstance(remote, dict):
        result = deepcopy(local)
        for key in before.keys() | remote.keys():
            old, new = before.get(key, _MISSING), remote.get(key, _MISSING)
            if equal(old, new):
                continue
            merged = merge_field(old, local.get(key, _MISSING), new)
            if merged is _MISSING:
                result.pop(key, None)
            else:
                result[key] = merged
        return result
    conflict()


def merge_scene_geometry(document, baseline, scene):
    """Import native calibration without moving source objects or raster pixels."""
    previous = baseline.get("sceneGeometry")
    if not isinstance(previous, dict):
        return False
    if (scene.width, scene.height) != (previous["width"], previous["height"]):
        raise services.MapError("The scene dimensions changed. Reload the project before updating it.", "conflict")
    local = document.get("sceneGeometry")
    options = services.settings({}, scene.settings)
    changed = False
    for key in ("gridSize", "gridOffsetX", "gridOffsetY", "imageScale"):
        before, remote = previous.get(key, 1), options[key]
        if equal(before, remote):
            continue
        # Removing the imported calibration is an explicit local resize. Do
        # not replace that pending edit with a native calibration change.
        if not isinstance(local, dict):
            conflict()
        local[key] = merge_field(before, local.get(key, 1), remote)
        previous[key] = deepcopy(remote)
        changed = True
    return changed


def _native_overrides(previous, before, after, kind):
    """Retain native-only properties which have no builder control."""
    from .builder_services import strip_live

    left, right = deepcopy(before), deepcopy(after)
    strip_live(left, right, kind=kind)
    handled = {"name", "blueprint"}
    if kind == "walls":
        handled.update(("x1", "y1", "x2", "y2", "presentation", "vertical_bottom", "vertical_top",
                        "asset_id", "rotationAnchor", "thickness", "movement_behavior", "vision_behavior",
                        "light_behavior", "sound_behavior", "blocks_light", "blocks_sight", "discovered"))
    elif kind == "images" and not any(key in before for key in ("surface", "surfacePlane")):
        handled.update(("x", "y", "rotation", "asset_id", "src", "natural_width", "natural_height", "scale", "spriteBase"))
        # The component's box is projected; its base layer has no builder field.
        for key in ("lever", "torch"):
            for value in (left, right):
                if isinstance(value.get(key), dict):
                    value[key] = {"baseLayer": value[key].get("baseLayer")}
    elif kind in ("lights", "particles", "shaders"):
        handled.update(left.keys() | right.keys())
    elif kind == "zones":
        handled.update(("vertical", "region"))
        if right.get("geometry", {}).get("shape") == "rect":
            handled.add("geometry")
    allowed = {"layer", "z_index", "lever", "torch"} if kind == "images" else set()
    if "surface" in before or "surfacePlane" in before:
        allowed.update(("x", "y", "scale", "rotation"))
        handled.discard("blueprint")
    overrides = deepcopy(previous.get("nativeOverrides", {}))
    if kind == "images" and not any(key in before for key in ("lever", "torch", "surface", "surfacePlane")):
        from .builder_services import ordinary_image_base
        if ordinary_image_base(before)["layer"] != ordinary_image_base(after)["layer"]:
            overrides["layer"] = ordinary_image_base(after)["layer"]
    for key in left.keys() | right.keys():
        if key in handled or left.get(key, _MISSING) == right.get(key, _MISSING):
            continue
        if key not in allowed:
            raise services.MapError(
                "This native object change cannot be represented in the map builder. Keep its original object type and geometry.",
                "conflict")
        if key in right:
            overrides[key] = deepcopy(right[key])
        else:
            overrides.pop(key, None)
    return overrides


def apply_overrides(row, overrides):
    """Apply persisted native presentation after source generation and binding."""
    if not overrides:
        return
    from .objects import choice, number
    allowed = {"layer", "z_index", "lever", "torch"} if row.kind == "images" else set()
    if "surface" in row.data or "surfacePlane" in row.data:
        allowed.update(("x", "y", "scale", "rotation"))
    if not isinstance(overrides, dict) or set(overrides) - allowed:
        raise services.MapError("Invalid native map presentation history.")
    for key, value in overrides.items():
        if key == "layer":
            choice(value, {"map", "gm-image-layer"})
        elif key in ("lever", "torch"):
            if not isinstance(value, dict) or set(value) != {"baseLayer"} or key not in row.data:
                raise services.MapError("Invalid native map presentation history.")
            choice(value["baseLayer"], {"map", "gm-image-layer"})
        else:
            number(value, *({"scale": (.001, 100), "z_index": (-10000, 10000),
                            "rotation": (-36000, 36000)}.get(key, (-1e6, 1e6))))
    row.builder_native_overrides = deepcopy(overrides)
    for key, value in overrides.items():
        if key in ("lever", "torch") and key in row.data:
            row.data[key].update(deepcopy(value))
        else:
            row.data[key] = deepcopy(value)
    if any(key in overrides for key in ("lever", "torch")):
        from .blueprint_runtime import apply_lever_appearance
        apply_lever_appearance(row)
    elif "layer" in overrides and isinstance(row.data.get("spriteBase"), dict):
        from .blueprint_actions import change_sprite
        row.data["spriteBase"]["layer"] = overrides["layer"]
        change_sprite(row.scene, row, row.data["sprite"])


def reconcile(source, scene, who):
    """Return updated source and manifest without modifying native resources."""
    from . import builder_services as builder

    manifest = deepcopy(source.generation)
    if manifest == {}:
        manifest = builder.legacy_generation(source, who) or manifest
    if (not isinstance(manifest, dict) or manifest.get("formatVersion") != 1
            or manifest.get("sceneId") != str(scene.pk) or not isinstance(manifest.get("objects"), list)):
        raise services.MapError("This scene has no update history. Generate a new scene to preserve existing content.", "conflict")
    doc = builder.clean_document(source.document, who)
    baseline = deepcopy(manifest.get("sourceDocument"))
    has_baseline = isinstance(baseline, dict)
    baseline = builder.clean_document(baseline, who) if has_baseline else deepcopy(doc)
    cell = manifest.get("cellSize")
    if type(cell) not in (int, float) or not math.isfinite(cell) or cell <= 0:
        raise services.MapError("This scene has no valid update history. Generate a new scene.", "conflict")
    entries, native_ids, source_ids = [], set(), set()
    for item in manifest["objects"]:
        if (not isinstance(item, dict) or not isinstance(item.get("data"), dict)
                or not isinstance(item.get("sourceId"), str) or not item["sourceId"]
                or len(item["sourceId"]) > 256 or item["sourceId"] in source_ids):
            raise services.MapError("This scene has no valid update history. Generate a new scene.", "conflict")
        key = str(builder.identifier(item.get("id")))
        if key in native_ids:
            raise services.MapError("This scene has no valid update history. Generate a new scene.", "conflict")
        native_ids.add(key)
        source_ids.add(item["sourceId"])
        entries.append(item)
    current = {str(row.pk): row for row in scene.elements.filter(pk__in=native_ids)}
    mapping = {entry["id"]: entry["sourceId"] for entry in entries}
    component_parents = {}
    for entry in entries:
        row = current.get(entry["id"])
        if row is None or "torch" not in entry["data"] or "torch" not in row.data:
            continue
        parent_changed = projection(entry["data"], "images", cell, mapping) != projection(row.data, "images", cell, mapping)
        for link in row.data["torch"].get("components", {}).values():
            component_parents[link["id"]] = (entry["data"], row.data, parent_changed)
    expected = None
    by_source = {item["id"]: (kind, item) for kind in KINDS for item in doc.get(kind, [])}
    old_sources = {item["id"]: item for kind in KINDS for item in baseline.get(kind, [])}
    from .builder_dynamic import plan
    surface_groups = {item["sourceId"]: item for item in plan(baseline)}
    changed_walls, removed = set(), set()
    changed = merge_scene_geometry(doc, baseline, scene)
    for entry in entries:
        key, kind = entry["sourceId"], entry["kind"]
        row = current.get(entry["id"])
        if row and row.kind != kind:
            raise services.MapError("A generated object changed type. Generate a new scene to preserve the existing object.", "conflict")
        before = entry["data"]
        if row and kind == "walls" and before.get("kind") != row.data.get("kind"):
            raise services.MapError("A generated object changed type. Generate a new scene to preserve the existing object.", "conflict")
        left, right = deepcopy(before), deepcopy(row.data) if row else None
        if row:
            builder.strip_live(left, right, kind=kind)
        parent_frames = component_parents.get(entry["id"])
        if row and left == right and not (parent_frames and parent_frames[2]):
            continue
        changed = True
        source_key = key if key in by_source else key.split(":", 1)[0]
        record = by_source.get(source_key)
        if (kind == "walls" and before.get("kind") == "door"
                and (row is None or any(not equal(before[field], row.data[field])
                                        for field in ("x1", "y1", "x2", "y2")))):
            previous_door = {field: before[field] / cell for field in ("x1", "y1", "x2", "y2")}
            changed_walls.update(wall["id"] for wall in baseline.get("walls", [])
                                 if builder.collinear_overlap(wall, previous_door) is not None)
        if kind == "walls" and before.get("kind") == "wall" and key != source_key:
            changed_walls.add(source_key)
            continue
        if record is None:
            group = surface_groups.get(key)
            if group and kind == "images" and "surfacePlane" in before:
                if row is not None:
                    entry["nativeOverrides"] = _native_overrides(entry, before, row.data, kind)
                    entry["data"] = deepcopy(row.data)
                else:
                    for selected in group["selection"].values():
                        for selected_key in selected:
                            local = by_source.get(selected_key)
                            if local and has_baseline and local[1] != old_sources.get(selected_key):
                                conflict()
                            removed.add(selected_key)
                continue
            # A source already removed in the builder may only disappear in the VTT.
            if row is not None:
                conflict()
            removed.add(key)
            continue
        _, target = record
        baseline_target = old_sources.get(source_key)
        old_source = deepcopy(baseline_target if baseline_target is not None else target)
        if row is None:
            if has_baseline and target != old_source:
                conflict()
            removed.add(source_key)
            continue
        old_data, new_data = before, row.data
        if parent_frames:
            previous_parent, current_parent, _ = parent_frames
            state = current_parent["torch"]["state"]
            old_data = component_frame(before, previous_parent, state)
            new_data = component_frame(row.data, current_parent, state)
        old = projection(old_data, kind, cell, mapping)
        new = projection(new_data, kind, cell, mapping)
        if parent_frames and has_baseline:
            for field in ("x", "y", "rotation"):
                old[field] = old_source.get(field, 0)
        if not has_baseline:
            if expected is None:
                expected = {item.builder_source_id: item for item in builder.native_objects(doc, scene)}
                mapping.update({str(item.pk): item.builder_source_id for item in expected.values()})
            wanted = expected.get(key)
            wanted = projection(wanted.data, kind, doc["cellSize"], mapping) if wanted else {}
        for field in old.keys() | new.keys():
            previous, updated = old.get(field, _MISSING), new.get(field, _MISSING)
            if equal(previous, updated):
                continue
            base_value = old_source.get(field, _MISSING)
            if field == "blueprint":
                # The graph editor can adopt a native graph into the project
                # without regenerating the scene or its other source fields.
                base_value = previous
            next_value = updated
            if kind == "images" and field in ("x", "y", "width", "height"):
                # Preserve contain-fit padding in old ordinary image sources.
                dimension = "width" if field in ("x", "width") else "height"
                ratio = new[dimension] / old[dimension]
                if field in ("width", "height"):
                    next_value = old_source[field] * ratio
                else:
                    next_value = new[field] + new[dimension] / 2 - old_source[dimension] * ratio / 2
            if has_baseline:
                merged = merge_field(base_value, target.get(field, _MISSING), next_value)
            else:
                wanted_value = wanted.get(field, _MISSING)
                if not equal(wanted_value, previous) and not equal(wanted_value, updated):
                    conflict()
                merged = next_value
            if merged is _MISSING:
                target.pop(field, None)
                if baseline_target is not None:
                    baseline_target.pop(field, None)
            else:
                target[field] = deepcopy(merged)
                if baseline_target is not None:
                    baseline_target[field] = deepcopy(next_value)
        entry["nativeOverrides"] = _native_overrides(entry, before, row.data, kind)
        entry["data"] = deepcopy(row.data)

    # One native wall span can be edited or removed independently of its siblings.
    # Replace that authored stroke with its surviving spans, retaining native IDs.
    for source_key in changed_walls:
        record = by_source.get(source_key)
        if record is None:
            if any(current.get(entry["id"]) for entry in entries if entry["sourceId"].startswith(source_key + ":")):
                conflict()
            continue
        _, target = record
        old_source = old_sources.get(source_key, target)
        geometry_fields = ("x1", "y1", "x2", "y2")
        if has_baseline and any(not equal(target[field], old_source[field]) for field in geometry_fields):
            conflict()
        if (has_baseline and target != old_source
                and not any(entry["id"] in current for entry in entries
                            if entry["sourceId"].startswith(source_key + ":"))):
            conflict()
        if not has_baseline:
            if expected is None:
                expected = {item.builder_source_id: item for item in builder.native_objects(doc, scene)}
                mapping.update({str(item.pk): item.builder_source_id for item in expected.values()})
            spans = [entry for entry in entries if entry["sourceId"].startswith(source_key + ":")]
            for entry in spans:
                wanted = expected.get(entry["sourceId"])
                if wanted is None or any(not equal(wanted.data[field], entry["data"][field]) for field in geometry_fields):
                    conflict()
        removed.add(source_key)
        for entry in entries:
            if not entry["sourceId"].startswith(source_key + ":"):
                continue
            row = current.get(entry["id"])
            if row is None:
                continue
            replacement = deepcopy(target)
            source_replacement = deepcopy(old_source)
            replacement["id"] = str(uuid.uuid5(source.pk, "native-span:" + entry["id"]))
            source_replacement["id"] = replacement["id"]
            previous = projection(entry["data"], "walls", cell, mapping)
            imported = projection(row.data, "walls", cell, mapping)
            for field in geometry_fields:
                replacement[field] = source_replacement[field] = imported[field]
            for field in (previous.keys() | imported.keys()) - set(geometry_fields):
                old, new = previous.get(field, _MISSING), imported.get(field, _MISSING)
                if equal(old, new):
                    continue
                if has_baseline:
                    merged = merge_field(old_source.get(field, _MISSING), target.get(field, _MISSING), new)
                else:
                    wanted = projection(expected[entry["sourceId"]].data, "walls", cell, mapping)
                    if not equal(wanted.get(field, _MISSING), old) and not equal(wanted.get(field, _MISSING), new):
                        conflict()
                    merged = new
                if merged is _MISSING:
                    replacement.pop(field, None)
                    source_replacement.pop(field, None)
                else:
                    replacement[field], source_replacement[field] = deepcopy(merged), deepcopy(new)
            doc["walls"].append(replacement)
            baseline["walls"].append(source_replacement)
            entry["sourceId"] = replacement["id"] + ":" + ":".join(
                format(replacement[field], ".12g") for field in ("x1", "y1", "x2", "y2"))
            entry["data"] = deepcopy(row.data)

    if removed:
        from .blueprint_runtime import detach_blueprint_light
        from .torches import COMPONENTS
        for document in (doc, baseline):
            for kind in KINDS:
                if kind in document:
                    document[kind] = [item for item in document[kind] if item["id"] not in removed]
            for item in (*document.get("doors", []), *document.get("decorations", []), *document.get("regions", [])):
                for key in removed:
                    detach_blueprint_light(item.get("blueprint"), key)
                for field in COMPONENTS:
                    if item.get("torch", {}).get(field) in removed:
                        item["torch"].pop(field)
        entries = [entry for entry in entries if entry["id"] in current and entry["sourceId"] not in removed]
    # Native artwork can be changed to another campaign asset without first
    # classifying it in the separate builder catalog.
    roles = {item["assetId"]: item["role"] for item in doc.get("assets", [])}
    for kind, role in (("doors", "door"), ("decorations", "decoration")):
        for item in doc.get(kind, []):
            artwork = {item.get("assetId")}
            blueprint = item.get("blueprint", {})
            artwork.update(state.get("assetId") for state in blueprint.get("states", {}).values())
            for graph in blueprint.get("graphs", {}).values():
                artwork.update(node.get("assetId") for node in graph.get("nodes", []))
            for key in artwork - {None}:
                if key not in roles:
                    doc["assets"].append({"assetId": key, "role": role})
                    baseline["assets"].append({"assetId": key, "role": role})
                    roles[key] = role
    if changed and doc["schemaVersion"] != 3:
        layer_id = str(uuid.uuid5(source.pk, "native-sync-layer"))
        for document in (doc, baseline):
            document["schemaVersion"] = 3
            document["layers"] = [{"id": layer_id, "name": "Base", "visible": True, "locked": False}]
            document.setdefault("decorations", [])
            document.setdefault("lights", [])
            for kind in KINDS:
                for item in document.get(kind, []):
                    item["layerId"] = layer_id
                    if kind == "floors":
                        item.setdefault("rotation", 0)
    doc = builder.clean_document(doc, who)
    manifest["objects"] = entries
    if has_baseline:
        manifest["sourceDocument"] = baseline
    return doc, manifest, changed
