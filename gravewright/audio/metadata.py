"""Read audio duration without decoding the entire track into memory."""
import math
from mutagen import File, MutagenError
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from gravewright.maps.services import MapError

TYPES = {WAVE: ('audio/wav','.wav'), MP3: ('audio/mpeg','.mp3'),
         FLAC: ('audio/flac','.flac'), OggVorbis: ('audio/ogg','.ogg'),
         OggOpus: ('audio/ogg','.ogg')}


def inspect(source):
    try:
        source.seek(0)
        audio = File(source, options=list(TYPES))
        if type(audio) not in TYPES:
            raise ValueError('Unsupported audio')
        length = float(audio.info.length)
        if not math.isfinite(length) or length <= 0:
            raise ValueError('Invalid audio duration')
        content_type, extension = TYPES[type(audio)]
        return content_type, extension, length
    except (MutagenError, OSError, ValueError, EOFError):
        raise MapError('Choose valid WAV, Ogg, FLAC or MP3 audio.') from None
    finally:
        source.seek(0)
