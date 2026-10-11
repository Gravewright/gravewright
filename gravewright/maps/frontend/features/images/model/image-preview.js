/** Keep gestures working when a browser still has the previous board module cached. */
export function previewBoardImage(board, state, image) {
    if (typeof board.previewImage === 'function') return board.previewImage(image);
    return board.update({state: image ? {
        ...state, images: state.images.map(row => row.id === image.id ? image : row),
    } : state});
}
