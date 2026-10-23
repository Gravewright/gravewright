"""Bounded Pillow rasterization of the editable source before native tiling."""

from io import BytesIO
import math
import threading

from django.core.files.base import ContentFile
from PIL import Image, ImageChops, ImageDraw, ImageMath

from .models import MapAsset
from .services import MapError
from .wall_joins import wall_join_geometry
from .terrain_brush import terrain_brush_mask
from .builder_geometry import canvas_size

_rendering = threading.Lock()


def _wall_image(row):
    """Decode one wall's art, omitting transparent upload padding.

    A small alpha threshold excludes near-invisible export noise from the
    thickness calculation while retaining the artwork's antialiased edges.
    Floor textures deliberately keep their original image bounds.
    """
    try:
        with row.file.open("rb") as stream, Image.open(stream) as image:
            if image.width * image.height > 40_000_000:
                raise MapError("A map asset exceeds the image pixel limit.")
            bounds = None
            if "A" in image.getbands() or "transparency" in image.info:
                with image.convert("RGBA") as rgba, rgba.getchannel("A") as alpha:
                    with alpha.point(lambda value: 255 if value >= 8 else 0) as visible:
                        bounds = visible.getbbox()
            if bounds is None:
                return image.convert("RGBA")
            with image.crop(bounds) as cropped:
                return cropped.convert("RGBA")
    except (OSError, ValueError) as error:
        raise MapError(f"Unable to read map asset: {row.name}.") from error


def _wall_strip(image, length, thickness, phase, repeated=None):
    """Sample repeated art in the wall's local coordinates without wide tiles.

    Sampling only the visible interval bounds allocation by wall geometry even
    when an uploaded image has an extreme aspect ratio. Door cuts retain the
    original wall's phase rather than restarting its texture on each side.
    """
    size = (max(1, math.ceil(length)), max(1, math.ceil(thickness)))
    strip = Image.new("RGBA", size)
    scale = thickness / image.height
    period = image.width * scale
    try:
        if repeated is not None:
            # Integer-sized repeats have no fractional boundary columns. The
            # renderer keeps one small transformed repeat instead of decoding
            # and transforming it again for each connected strip.
            offset = round(phase) % repeated.width
            for x in range(-offset, size[0], repeated.width):
                strip.paste(repeated, (x, 0))
            return strip
        if period < 1:
            # A complete repeat smaller than one raster pixel resolves to its
            # horizontal average, avoiding an unbounded number of tiny repeats.
            with image.resize((1, image.height), Image.Resampling.BOX) as average:
                with average.resize((1, size[1]), Image.Resampling.LANCZOS) as column:
                    with column.resize(size) as repeated:
                        strip.paste(repeated, (0, 0))
            return strip
        first, last = math.floor(phase / period), math.ceil((phase + length) / period)
        for repeat in range(first, last):
            start = max(0, math.floor(repeat * period - phase))
            end = min(size[0], math.ceil((repeat + 1) * period - phase))
            if end <= start:
                continue
            with image.transform((end - start, size[1]), Image.Transform.AFFINE,
                    (1 / scale, 0, (start + phase - repeat * period) / scale,
                     0, 1 / scale, 0), Image.Resampling.BICUBIC) as piece:
                # Fractional repeat boundaries overlap one raster column. Keep
                # the valid sample when the neighboring tile falls outside it.
                strip.alpha_composite(piece, (start, 0))
        return strip
    except Exception:
        strip.close()
        raise


def render(doc, campaign_id, *, selection=None, crop=None, mask=False):
    """Serialize raster allocations; the existing tiler owns its own decode lock."""
    with _rendering:
        return _render_document(doc, campaign_id, selection=selection, crop=crop, mask=mask)


def _floor_shape_mask(row, cell, left, top, size):
    """Sample contour unions minus cuts at pixel centers, with bounded 2x AA.

    Separate rings paint the same mask, so overlapping pencil capsules never
    cancel each other. Even-odd scan lines match SVG ring coverage, including
    self-intersecting polygons. The validated edge/scan-line budget bounds this
    loop; the temporary mask is at most four times the canvas pixel limit.
    """
    sample = 2
    width, height = size[0] * sample, size[1] * sample
    mask = Image.new("L", (width, height))
    try:
        draw = ImageDraw.Draw(mask)
        for kind, value in (("contours", 255), ("cuts", 0)):
            for ring in row["shape"][kind]:
                points = [(((row["x"] + u * row["width"]) * cell - left) * sample,
                           ((row["y"] + v * row["height"]) * cell - top) * sample) for u, v in ring]
                edges = [(first, last) for first, last in zip(points, points[1:] + points[:1]) if first[1] != last[1]]
                start = max(0, math.ceil(min(point[1] for point in points) - .5))
                end = min(height, math.ceil(max(point[1] for point in points) - .5))
                for y in range(start, end):
                    center = y + .5
                    intersections = sorted(first[0] + (center - first[1]) * (last[0] - first[0]) / (last[1] - first[1])
                        for first, last in edges if (first[1] > center) != (last[1] > center))
                    for index in range(0, len(intersections) - 1, 2):
                        first = max(0, math.ceil(intersections[index] - .5))
                        last = min(width, math.ceil(intersections[index + 1] - .5))
                        if last > first:
                            draw.line((first, y, last - 1, y), fill=value)
        return mask.resize(size, Image.Resampling.BOX)
    finally:
        mask.close()


def _wall_polygon_mask(polygons, left, top, size):
    """Union mesh pieces at pixel centers; shared edges have one owner."""
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    for polygon in polygons:
        points = [(x - left, y - top) for x, y in polygon]
        edges = [(a, b) for a, b in zip(points, points[1:] + points[:1]) if a[1] != b[1]]
        start = max(0, math.ceil(min(y for _, y in points) - .5))
        end = min(size[1], math.ceil(max(y for _, y in points) - .5))
        for y in range(start, end):
            center = y + .5
            intersections = sorted(a[0] + (center - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                for a, b in edges if (a[1] > center) != (b[1] > center))
            for index in range(0, len(intersections) - 1, 2):
                first = max(0, math.ceil(round(intersections[index] - .5, 9)))
                last = min(size[0], math.ceil(round(intersections[index + 1] - .5, 9)))
                if last > first:
                    draw.line((first, y, last - 1, y), fill=255)
    return mask


def _render_document(doc, campaign_id, *, selection=None, crop=None, mask=False):
    from .builder_services import segments

    cell = doc["cellSize"]
    mask_only = mask
    width, height = canvas_size(doc)
    extent = crop or (0, 0, width, height)
    canvas = Image.new("RGBA" if selection is not None else "RGB",
                       (extent[2] - extent[0], extent[3] - extent[1]),
                       (0, 0, 0, 0) if selection is not None else doc["background"])
    textures = {}
    wall_image = None
    wall_asset_id = None
    wall_repeat = None
    wall_repeat_key = None
    asset_ids = [row["assetId"] for row in doc["assets"]]
    if doc.get("backgroundImage"):
        asset_ids.append(doc["backgroundImage"]["assetId"])
    assets = {str(row.pk): row for row in MapAsset.objects.filter(campaign_id=campaign_id,
               pk__in=asset_ids)}

    def composite(patch, position, alpha):
        position = position[0] - extent[0], position[1] - extent[1]
        if canvas.mode == "RGBA":
            if not isinstance(patch, Image.Image):
                patch = Image.new("RGBA", alpha.size, patch)
                try:
                    patch.putalpha(alpha)
                    canvas.alpha_composite(patch, position)
                finally:
                    patch.close()
            else:
                patch.putalpha(alpha)
                canvas.alpha_composite(patch, position)
        else:
            canvas.paste(patch, position, alpha)

    def texture(asset_id):
        if asset_id is None:
            return None
        if asset_id not in textures:
            row = assets.get(asset_id)
            if row is None:
                raise MapError("A map asset is missing.")
            try:
                with row.file.open("rb") as stream, Image.open(stream) as image:
                    if image.width * image.height > 40_000_000:
                        raise MapError("A map asset exceeds the image pixel limit.")
                    decoded = image.convert("RGBA")
                    try:
                        textures[asset_id] = decoded.resize((cell, cell), Image.Resampling.LANCZOS)
                    finally:
                        decoded.close()
            except (OSError, ValueError) as error:
                raise MapError(f"Unable to read map asset: {row.name}.") from error
        return textures[asset_id]

    def paint(bounds, asset_id, fallback, polygon=None, rotation=0, floor_shape=None, floor_paint=None,
              floor_brush=None, target=None, target_origin=(0, 0)):
        if floor_paint is not None and floor_paint["opacity"] == 0:
            return
        left, top, right, bottom = bounds
        left, top = max(extent[0], math.floor(left)), max(extent[1], math.floor(top))
        right, bottom = min(extent[2], math.ceil(right)), min(extent[3], math.ceil(bottom))
        if right <= left or bottom <= top:
            return
        size = (right - left, bottom - top)
        erasing = floor_brush is not None and floor_brush["brush"]["operation"] == "erase"
        patch = None if erasing else Image.new("RGBA", size, fallback)
        rotated = None
        mask = None
        try:
            tile = None if erasing else texture(asset_id)
            if tile is not None:
                if rotation:
                    # Source angles increase clockwise, as on the native board.
                    operation = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180,
                                 270: Image.Transpose.ROTATE_90}[rotation]
                    rotated = tile.transpose(operation)
                    tile = rotated
                for y in range(-(top % cell), size[1], cell):
                    for x in range(-(left % cell), size[0], cell):
                        patch.paste(tile, (x, y))
            if floor_shape is not None:
                mask = _floor_shape_mask(floor_shape, cell, left, top, size)
            elif polygon:
                mask = Image.new("L", size)
                ImageDraw.Draw(mask).polygon([(x - left, y - top) for x, y in polygon], fill=255)
            if floor_brush is not None:
                brush_mask = terrain_brush_mask(floor_brush, cell, left, top, size)
                if mask is None:
                    mask = brush_mask
                else:
                    combined = ImageChops.multiply(mask, brush_mask)
                    mask.close()
                    brush_mask.close()
                    mask = combined
            if mask is not None:
                if patch is not None:
                    alpha = patch.getchannel("A")
                    # Transparent user textures preserve underlying floor/background.
                    combined = ImageChops.multiply(mask, alpha)
                    alpha.close()
                    mask.close()
                    mask = combined
            else:
                mask = patch.getchannel("A")
            if floor_paint is not None and floor_paint["opacity"] < 1:
                opacity = floor_paint["opacity"]
                faded = mask.point(lambda value: int(value * opacity + .5))
                mask.close()
                mask = faded
            if erasing:
                active = mask.getbbox()
                if active is not None:
                    box = (left + active[0] - target_origin[0], top + active[1] - target_origin[1],
                           left + active[2] - target_origin[0], top + active[3] - target_origin[1])
                    with target.crop(box) as previous, previous.getchannel("A") as alpha, mask.crop(active) as removal:
                        # Destination-out acts on the composed layer once, so
                        # two translucent strokes are not erased separately.
                        multiplied = ImageMath.lambda_eval(lambda values: (values["alpha"] * (255 - values["removal"]) + 127) / 255,
                            alpha=alpha, removal=removal)
                        try:
                            with multiplied.convert("L") as faded:
                                previous.putalpha(faded)
                            target.paste(previous, box)
                        finally:
                            multiplied.close()
            elif target is not None:
                patch.putalpha(mask)
                target.alpha_composite(patch, (left - target_origin[0], top - target_origin[1]))
            else:
                composite(patch, (left, top), mask)
        finally:
            if patch is not None:
                patch.close()
            if rotated is not None:
                rotated.close()
            if mask is not None:
                mask.close()

    def paint_wall(wall, frame):
        nonlocal wall_image, wall_asset_id, wall_repeat, wall_repeat_key
        if not frame["polygons"]:
            return
        x1, y1 = (value * cell for value in frame["origin"])
        ux, uy = frame["direction"]
        thickness = wall["thickness"] * cell
        polygons = [[(x1 + (x * ux - y * uy) * cell, y1 + (x * uy + y * ux) * cell)
                     for x, y in ring] for ring in frame["polygons"]]
        points = [point for ring in polygons for point in ring]
        bounds = (min(x for x, _ in points), min(y for _, y in points),
                  max(x for x, _ in points), max(y for _, y in points))
        left, top = max(extent[0], math.floor(bounds[0])), max(extent[1], math.floor(bounds[1]))
        right, bottom = min(extent[2], math.ceil(bounds[2])), min(extent[3], math.ceil(bounds[3]))
        if right <= left or bottom <= top:
            return
        asset_id = None if mask_only else wall["assetId"]
        if asset_id is None:
            with _wall_polygon_mask(polygons, left, top, (right - left, bottom - top)) as mask:
                composite((255, 255, 255) if mask_only else (141, 129, 112), (left, top), mask)
            return
        if wall_asset_id != asset_id:
            # Keep at most one decoded wall image; a campaign may reference
            # hundreds of distinct uploads, each individually within the limit.
            if wall_image is not None:
                wall_image.close()
                wall_image = None
            row = assets.get(asset_id)
            if row is None:
                raise MapError("A map asset is missing.")
            wall_image = _wall_image(row)
            wall_asset_id = asset_id
        start = min(x for ring in frame["polygons"] for x, _ in ring) * cell
        distance = max(x for ring in frame["polygons"] for x, _ in ring) * cell - start
        phase = start + frame["phase"] * cell
        period = wall_image.width * thickness / wall_image.height
        repeated = None
        if (abs(thickness - round(thickness)) <= 1e-9 and abs(period - round(period)) <= 1e-9
                and abs(phase - round(phase)) <= 1e-9 and period >= 1
                and round(period) * round(thickness) <= 262_144):
            repeat_key = asset_id, round(period), round(thickness)
            if wall_repeat_key != repeat_key:
                if wall_repeat is not None:
                    wall_repeat.close()
                scale = thickness / wall_image.height
                wall_repeat = wall_image.transform((round(period), round(thickness)), Image.Transform.AFFINE,
                    (1 / scale, 0, 0, 0, 1 / scale, 0), Image.Resampling.BICUBIC)
                wall_repeat_key = repeat_key
            repeated = wall_repeat
        with _wall_strip(wall_image, distance, thickness, phase, repeated) as strip:
            offset_x, offset_y = left - x1, top - y1
            with strip.transform((right - left, bottom - top), Image.Transform.AFFINE,
                    (ux, uy, offset_x * ux + offset_y * uy - start,
                     -uy, ux, -offset_x * uy + offset_y * ux + thickness / 2),
                    Image.Resampling.BICUBIC) as patch:
                with _wall_polygon_mask(polygons, left, top, patch.size) as shape:
                    with patch.getchannel("A") as alpha, ImageChops.multiply(shape, alpha) as mask:
                        composite(patch, (left, top), mask)

    try:
        if selection is None and not mask_only and doc.get("backgroundImage"):
            background = assets.get(doc["backgroundImage"]["assetId"])
            if background is None:
                raise MapError("A map background image is missing.")
            try:
                with background.file.open("rb") as stream, Image.open(stream) as image:
                    if image.width * image.height > 40_000_000:
                        raise MapError("A map asset exceeds the image pixel limit.")
                    # One stretched base spans the document; cropped surface
                    # renders and masks never bake this image a second time.
                    sx, sy = image.width / width, image.height / height
                    box = (extent[0] * sx, extent[1] * sy, extent[2] * sx, extent[3] * sy)
                    with image.convert("RGBA") as decoded:
                        with decoded.resize(canvas.size, Image.Resampling.LANCZOS, box=box) as resized:
                            with resized.getchannel("A") as alpha:
                                canvas.paste(resized, (0, 0), alpha)
            except (OSError, ValueError) as error:
                raise MapError(f"Unable to read map asset: {background.name}.") from error
        layers = doc.get("layers")
        if layers is None:
            layers = [{"id": None}]
        first_layer = layers[0]["id"] if layers else None
        solid_spans = []
        for span in segments(doc):
            # Door strips remain native objects so opening one removes its art;
            # the same clipped wall spans define the raster and live geometry.
            if span["door"] or span["wall"].get("artwork") is False:
                continue
            solid_spans.append(span)
        wall_geometry = wall_join_geometry(doc, solid_spans)
        for layer in layers:
            # Visibility and locking organize the editor, not the generated map.
            floors = [floor for floor in doc["floors"] if floor.get("layerId", first_layer) == layer["id"]
                      and (selection is None or floor["id"] in selection.get("floors", ())
                           or layer["id"] == selection.get("eraseLayer") and floor.get("brush", {}).get("operation") == "erase")]
            if not floors:
                continue
            target, target_origin = None, (0, 0)
            if any(floor.get("brush", {}).get("operation") == "erase" for floor in floors):
                left = max(extent[0], math.floor(min(floor["x"] for floor in floors) * cell))
                top = max(extent[1], math.floor(min(floor["y"] for floor in floors) * cell))
                right = min(extent[2], math.ceil(max(floor["x"] + floor["width"] for floor in floors) * cell))
                bottom = min(extent[3], math.ceil(max(floor["y"] + floor["height"] for floor in floors) * cell))
                if right <= left or bottom <= top:
                    continue
                target_origin = left, top
                target = Image.new("RGBA", (right - left, bottom - top))
            try:
                for floor in floors:
                    paint((floor["x"] * cell, floor["y"] * cell,
                           (floor["x"] + floor["width"]) * cell,
                           (floor["y"] + floor["height"]) * cell), None if mask_only else floor["assetId"],
                          "#ffffff" if mask_only else floor.get("paint", {}).get("color") or "#49473f",
                          rotation=floor.get("rotation", 0), floor_shape=floor if "shape" in floor else None,
                          floor_paint=floor.get("paint"), floor_brush=floor if "brush" in floor else None,
                          target=target, target_origin=target_origin)
                if target is not None:
                    with target.getchannel("A") as alpha:
                        composite(target, target_origin, alpha)
            finally:
                if target is not None:
                    target.close()
        for layer in layers:
            for wall in doc["walls"]:
                if (wall.get("layerId", first_layer) == layer["id"] and wall["id"] in wall_geometry
                        and (selection is None or wall["id"] in selection.get("walls", ()))):
                    paint_wall(wall, wall_geometry[wall["id"]])
        output = BytesIO()
        canvas.save(output, "PNG")
        return ContentFile(output.getvalue(), name="map-builder.png")
    finally:
        canvas.close()
        for tile in textures.values():
            tile.close()
        if wall_image is not None:
            wall_image.close()
        if wall_repeat is not None:
            wall_repeat.close()
