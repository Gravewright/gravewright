from app.engine.tokens.token_service import TokenService


def _dimensions(*, config=None, projection=None):
    service = TokenService.__new__(TokenService)
    return service._resolve_token_dimensions(
        config=config or {},
        projection=projection or {},
    )


def test_numeric_mapped_size_sets_a_square_grid_footprint():
    assert _dimensions(projection={"size": 3}) == (3, 3)


def test_named_sizes_remain_compatible():
    assert _dimensions(projection={"size": "large"}) == (2, 2)
    assert _dimensions(projection={"size": "gargantuan"}) == (4, 4)


def test_explicit_token_config_still_overrides_the_mapping():
    assert _dimensions(
        config={"width_cells": 2, "height_cells": 4},
        projection={"size": 3},
    ) == (2, 4)


def test_invalid_or_non_positive_mapped_size_falls_back_to_one_cell():
    assert _dimensions(projection={"size": 0}) == (1, 1)
    assert _dimensions(projection={"size": "invalid"}) == (1, 1)
