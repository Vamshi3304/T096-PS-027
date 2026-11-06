"""
Unit tests for BR-11: Term Expiry Tracking & Review Flag.
Rules:
- Expected term + 60 days triggers TERM_REVIEW flag.
"""

import pytest


def test_br11_term_review_flag_trigger():
    """Elapsed day number >= expected_term + 60 days triggers TERM_REVIEW."""
    expected_term = 150.0
    review_threshold = expected_term + 60.0  # 210.0

    day_209 = 209
    is_review_209 = day_209 >= review_threshold
    assert is_review_209 is False

    day_210 = 210
    is_review_210 = day_210 >= review_threshold
    assert is_review_210 is True

    day_215 = 215
    is_review_215 = day_215 >= review_threshold
    assert is_review_215 is True
