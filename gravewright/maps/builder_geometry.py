"""Exact imported canvas dimensions alongside the Builder's bounded cell workspace."""


def canvas_size(document):
    geometry = document.get("sceneGeometry")
    if geometry:
        return geometry["width"], geometry["height"]
    return document["columns"] * document["cellSize"], document["rows"] * document["cellSize"]


def scene_options(document):
    geometry = document.get("sceneGeometry")
    if geometry:
        return {**{key: geometry[key] for key in ("gridSize", "gridOffsetX", "gridOffsetY")},
                "imageScale": geometry.get("imageScale", 1)}
    return {"gridSize": document["cellSize"]}
