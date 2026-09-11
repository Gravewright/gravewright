import { text as gwText } from '../../../shared/config/i18n/text.js';
export const IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp';
export const AUDIO_ACCEPT = 'audio/ogg,audio/opus,audio/mpeg,audio/mp4,audio/wav,.ogg,.opus,.mp3,.m4a,.wav';
const mimeByExtension = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', ogg: 'audio/ogg', opus: 'audio/opus', mp3: 'audio/mpeg', m4a: 'audio/mp4', wav: 'audio/wav', pdf: 'application/pdf' };
export function uploadMime(file) { return file.type || mimeByExtension[file.name.split('.').at(-1)?.toLowerCase() ?? ''] || ''; }
export function validateUpload(file, imagesOnly = false) {
    const mime = uploadMime(file), image = IMAGE_ACCEPT.split(',').includes(mime), audio = AUDIO_ACCEPT.split(',').includes(mime), pdf = mime === 'application/pdf';
    if (!image && (imagesOnly || (!audio && !pdf)))
        return gwText('Unsupported format.');
    if (!file.size)
        return gwText('The file is empty.');
    const max = (image ? 10 : pdf ? 25 : 100) * 1024 * 1024;
    if (file.size > max)
        return gwText('This file\'s limit is {0} MB.', max / 1024 / 1024);
}
export function uploadFile(file) { const type = uploadMime(file); return type === file.type ? file : new File([file], file.name, { type, lastModified: file.lastModified }); }
export function assetKinds(asset) {
    if (asset.kind !== 'audio')
        return [asset.kind];
    return asset.audio_kinds?.length ? [...new Set(asset.audio_kinds.map(kind => kind === 'music' || kind === 'ambience' ? 'ambient' : kind === 'sound-effect' ? 'effect' : 'audio'))] : ['audio'];
}
export function bytesLabel(bytes) { return bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`; }
export function uploadError(error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes('asset_in_use'))
        return gwText('This file is in use and cannot be deleted.');
    if (message.includes('too_large'))
        return 'O arquivo excede o tamanho permitido.';
    if (message.includes('unsupported') || message.includes('invalid_image'))
        return gwText('Invalid file or unsupported format.');
    if (message.includes('denied') || message.includes('forbidden'))
        return gwText('You do not have permission for this action.');
    return gwText('Could not complete the action. Check the connection and try again.');
}
