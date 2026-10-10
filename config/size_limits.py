"""Human-readable size limits; MB means 1024 * 1024 bytes."""
from decimal import Decimal, InvalidOperation

MB = 1024 * 1024
SIZE_DEFAULTS = {
    'WS_MAX_MESSAGE_BYTES': 65536,
    'JOURNAL_IMAGE_MAX_BYTES': 10485760,
    'JOURNAL_PDF_MAX_BYTES': 26214400,
    'PDF_SYSTEM_UPLOAD_MAX_BYTES': 10485760,
    'MAP_UPLOAD_MAX_BYTES': 53687091200,
}


def size_bytes(values, name, default):
    key = name.removesuffix('_BYTES') + '_MB'
    if values.get(key) is None:
        value = int(values.get(name, default))
    else:
        try:
            amount = Decimal(values[key]) * MB
            if not amount.is_finite() or amount < 1 or amount != amount.to_integral_value():
                raise ValueError
            value = int(amount)
        except (InvalidOperation, ValueError):
            raise ValueError(f'{key} must be a positive size in MB (at least one whole byte).') from None
    if value < 1:
        raise ValueError(f'{name} must be positive.')
    return value


def migrate_sizes(values):
    """Preserve old byte limits when filling an existing .env from the template."""
    result = dict(values)
    for name, default in SIZE_DEFAULTS.items():
        key = name.removesuffix('_BYTES') + '_MB'
        if result.get(name) is not None:
            if result.get(key) is None:
                result[key] = format(Decimal(size_bytes(result, name, default)) / MB, 'f')
            del result[name]
    return result
