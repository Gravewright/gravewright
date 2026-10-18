/** Empty Objects are GM controllers, including legacy rows stored on the map. */
export function isGMImage(image) {
    return image.empty === true || ['gm', 'gm-image-layer'].includes(image.layer);
}

export function imageInWorkspace(image, layer = 'game') {
    return isGMImage(image) ? layer === 'gm' : layer !== 'gm';
}

export function canMoveImageToGame(image) {
    return image.empty !== true;
}

export function imageMarkerVisible(image, layer = 'game', gm = true) {
    return !isGMImage(image) || gm;
}
