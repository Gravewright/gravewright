from __future__ import annotations

from math import ceil, sqrt

from app.engine.tokens.token_placement_service import TokenPlacementService


def test_single_token_lands_on_origin():
    positions = TokenPlacementService().calculate_positions(origin_x=5, origin_y=3, count=1)
    assert positions == [(5, 3)]


def test_zero_count_returns_empty():
    assert TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=0) == []


def test_negative_count_returns_empty():
    assert TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=-1) == []


def test_four_tokens_form_2x2_grid():
    positions = TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=4)
    assert positions == [(0, 0), (1, 0), (2, 0), (3, 0)] or positions == [
        (0, 0), (1, 0),
        (0, 1), (1, 1),
    ]
                               
    assert positions == [(0, 0), (1, 0), (0, 1), (1, 1)]


def test_nine_tokens_form_3x3_grid():
    positions = TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=9)
    assert len(positions) == 9
                               
    assert positions[0] == (0, 0)
    assert positions[2] == (2, 0)                 
    assert positions[3] == (0, 1)                  
    assert positions[8] == (2, 2)        


def test_five_tokens_incomplete_last_row():
    positions = TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=5)
    assert len(positions) == 5
                               
    assert positions[0] == (0, 0)
    assert positions[1] == (1, 0)
    assert positions[2] == (2, 0)
    assert positions[3] == (0, 1)
    assert positions[4] == (1, 1)


def test_origin_offset_applied_to_all_positions():
    positions = TokenPlacementService().calculate_positions(origin_x=10, origin_y=7, count=4)
    assert positions[0] == (10, 7)
    assert positions[1] == (11, 7)
    assert positions[2] == (10, 8)
    assert positions[3] == (11, 8)


def test_no_duplicate_positions():
    for count in [1, 4, 5, 9, 16, 25]:
        positions = TokenPlacementService().calculate_positions(origin_x=0, origin_y=0, count=count)
        assert len(positions) == len(set(positions)), f"Duplicates found for count={count}"


def test_columns_match_spec_formula():
    """columns = ceil(sqrt(count)) per spec."""
    svc = TokenPlacementService()
    for count in [1, 2, 3, 4, 5, 8, 9, 10]:
        positions = svc.calculate_positions(origin_x=0, origin_y=0, count=count)
        expected_columns = ceil(sqrt(count))
        max_col_used = max(x for x, _y in positions)
        assert max_col_used == expected_columns - 1, f"count={count}"
