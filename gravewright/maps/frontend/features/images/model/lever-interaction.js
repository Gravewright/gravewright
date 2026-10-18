import { isGMImage as privateLayer, imageInWorkspace } from './image-layer.js';

export function interactiveImageKind(image) {
    if (['off', 'on'].includes(image.torch?.state) && typeof image.torch.lit === 'boolean') return 'torch';
    if (['off', 'on'].includes(image.lever?.state)) return 'lever';
}
export function canInteractWithImage(image, gm = false) {
    return !!image && !!interactiveImageKind(image) && (gm || image.interactionEnabled !== false);
}

/** Pick the visible image in front, using the same centered box as its sprite. */
export function createInteractiveImageHitTest(images, gm, layer) {
    const ordered = images.filter(image => gm ? layer === undefined || imageInWorkspace(image, layer) : !privateLayer(image))
        .map((image, index) => ({ image, index }))
        .sort((a, b) => Number(privateLayer(b.image)) - Number(privateLayer(a.image))
            || b.image.z_index - a.image.z_index || b.index - a.index);
    return point => { for (const { image } of ordered) {
        const width = image.natural_width * image.scale, height = image.natural_height * image.scale;
        if (![image.x, image.y, image.rotation, width, height].every(Number.isFinite) || width <= 0 || height <= 0)
            continue;
        const angle = -image.rotation * Math.PI / 180, dx = point.x - image.x, dy = point.y - image.y;
        if (Math.abs(dx * Math.cos(angle) - dy * Math.sin(angle)) > width / 2
            || Math.abs(dx * Math.sin(angle) + dy * Math.cos(angle)) > height / 2)
            continue;
        // Ordinary artwork in front also covers a Smart Object's interaction area.
        return canInteractWithImage(image, gm) ? image : undefined;
    } };
}

export function interactiveImageAt(images, point, gm) { return createInteractiveImageHitTest(images, gm)(point); }

// Older native integrations can retain the established hit-test name.
export const leverAt = interactiveImageAt;
