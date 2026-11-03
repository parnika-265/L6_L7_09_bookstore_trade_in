import pytest
from bookstore_trade_in import process_book_buybacks, inspect_scanner_calibration


def make_batch(fmt="paperback", books=None, approved=True, credit=False):
    return {
        "intake_approved": approved,
        "format": fmt,
        "payout_in_credit": credit,
        "books": books if books is not None else [],
    }


def book(condition="good", missing=0, counterfeit=False):
    return {"missing_pages": missing, "condition": condition, "counterfeit": counterfeit}


# ===== Input validation: both halves of the OR condition =====
def test_invalid_batches_not_a_list():
    with pytest.raises(ValueError):
        process_book_buybacks("not a list", 5.0)


def test_invalid_negative_bonus():
    with pytest.raises(ValueError):
        process_book_buybacks([], -1)


def test_valid_zero_bonus_boundary():
    assert process_book_buybacks([], 0)["status"] == "ZERO_CREDIT"


# ===== Outer loop: skipped / empty / approved =====
def test_empty_batches_list_loop_never_runs():
    assert process_book_buybacks([], 5.0) == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_unapproved_batch_skipped():
    result = process_book_buybacks([make_batch(approved=False, books=[book()])], 5.0)
    assert result["status"] == "ZERO_CREDIT"


def test_missing_intake_key_defaults_to_not_approved():
    result = process_book_buybacks([{"format": "paperback", "books": [book()]}], 5.0)
    assert result["status"] == "ZERO_CREDIT"


# ===== Format branches =====
def test_format_defaults_to_paperback_when_missing():
    batch = {"intake_approved": True, "books": [book()]}
    assert process_book_buybacks([batch], 0)["total_payout"] == 8.0


def test_paperback_good():
    assert process_book_buybacks([make_batch("paperback", [book()])], 0)["total_payout"] == 8.0


def test_hardcover_good():
    assert process_book_buybacks([make_batch("hardcover", [book()])], 0)["total_payout"] == 15.0


def test_textbook_good():
    assert process_book_buybacks([make_batch("textbook", [book()])], 0)["total_payout"] == 40.0


def test_unknown_format_rejected_and_skipped():
    result = process_book_buybacks([make_batch("comic", [book()])], 0)
    assert result["status"] == "ZERO_CREDIT"


# ===== Condition branches =====
def test_condition_mint():
    assert process_book_buybacks([make_batch("hardcover", [book("mint")])], 0)["total_payout"] == 18.75


def test_condition_poor():
    assert process_book_buybacks([make_batch("hardcover", [book("poor")])], 0)["total_payout"] == 6.0


def test_condition_default_when_missing():
    b = {"missing_pages": 0, "counterfeit": False}
    assert process_book_buybacks([make_batch("paperback", [b])], 0)["total_payout"] == 8.0


def test_book_with_no_keys_uses_all_defaults():
    assert process_book_buybacks([make_batch("paperback", [{}])], 0)["total_payout"] == 8.0


# ===== Inner loop: empty books =====
def test_approved_batch_with_no_books():
    result = process_book_buybacks([make_batch("paperback", [])], 0)
    assert result["status"] == "ZERO_CREDIT"


# ===== Missing pages: True / False (boundary 0 vs 1) =====
def test_missing_pages_zero_accepted():
    assert process_book_buybacks([make_batch("paperback", [book(missing=0)])], 0)["total_payout"] == 8.0


def test_missing_pages_one_rejected():
    result = process_book_buybacks([make_batch("paperback", [book(missing=1), book()])], 0)
    assert result["total_payout"] == 8.0  # bad book skipped, good book paid


# ===== Counterfeit branches =====
def test_counterfeit_textbook_breaks_and_zeroes_batch():
    books = [book("good"), book(counterfeit=True), book("good")]
    result = process_book_buybacks([make_batch("textbook", books)], 0)
    assert result["status"] == "ZERO_CREDIT"


def test_counterfeit_non_textbook_keeps_other_books():
    books = [book(counterfeit=True), book("good")]
    result = process_book_buybacks([make_batch("hardcover", books)], 0)
    assert result["total_payout"] == 15.0


# ===== payout_in_credit True / False =====
def test_payout_in_credit_true_adds_bonus():
    result = process_book_buybacks([make_batch("paperback", [book()], credit=True)], 5.0)
    assert result["total_payout"] == 13.0


def test_payout_in_credit_false_no_bonus():
    result = process_book_buybacks([make_batch("paperback", [book()], credit=False)], 5.0)
    assert result["total_payout"] == 8.0


# ===== Final status: rejected_items boundary 4 vs 5 =====
def test_exactly_four_rejections_not_audited():
    books = [book(missing=1)] * 4 + [book()]
    result = process_book_buybacks([make_batch("paperback", books)], 0)
    assert result["status"] == "COMPLETED"


def test_five_rejections_audit_rejected():
    books = [book(missing=1)] * 5 + [book()]
    result = process_book_buybacks([make_batch("paperback", books)], 0)
    assert result == {"total_payout": 8.0, "status": "AUDIT_REJECTED"}


def test_zero_credit_status():
    result = process_book_buybacks([make_batch("paperback", [book(missing=2)])], 0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_completed_status_multiple_batches():
    batches = [make_batch("textbook", [book("mint")]), make_batch("paperback", [book("poor")])]
    result = process_book_buybacks(batches, 0)
    assert result["total_payout"] == 53.2
    assert result["status"] == "COMPLETED"


# ===== inspect_scanner_calibration =====
def test_scanner_none_and_empty_list():
    assert inspect_scanner_calibration([]) == "NO_DATA"
    assert inspect_scanner_calibration(None) == "NO_DATA"


def test_scanner_two_consecutive_bad_readings_recalibrate():
    assert inspect_scanner_calibration([[1, 6, 7]]) == "RECALIBRATE"


def test_scanner_single_bad_reading_then_reset_calibrated():
    assert inspect_scanner_calibration([[6, 1, 6, 1]]) == "CALIBRATED"


def test_scanner_boundary_exactly_five_is_ok():
    assert inspect_scanner_calibration([[5, 5, 5]]) == "CALIBRATED"


def test_scanner_second_device_triggers_recalibrate():
    assert inspect_scanner_calibration([[1, 2], [9, 9]]) == "RECALIBRATE"


def test_scanner_empty_device_readings():
    assert inspect_scanner_calibration([[]]) == "CALIBRATED"
