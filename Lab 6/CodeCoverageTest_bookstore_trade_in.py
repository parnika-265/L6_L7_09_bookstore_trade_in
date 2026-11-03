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


# ---- Provided example ----
def test_single_paperback_good():
    batches = [make_batch("paperback", [book("good")])]
    result = process_book_buybacks(batches, 5.0)
    assert result["total_payout"] == 8.0
    assert result["status"] == "COMPLETED"


# ---- process_book_buybacks: validation ----
def test_invalid_batches_not_a_list():
    with pytest.raises(ValueError):
        process_book_buybacks("not a list", 5.0)


# ---- process_book_buybacks: batch handling ----
def test_unapproved_batch_is_skipped():
    result = process_book_buybacks([make_batch(approved=False, books=[book()])], 5.0)
    assert result == {"total_payout": 0.0, "status": "ZERO_CREDIT"}


def test_textbook_mint_with_credit_bonus():
    batches = [make_batch("textbook", [book("mint")], credit=True)]
    result = process_book_buybacks(batches, 5.0)
    assert result["total_payout"] == 55.0  # 40*1.25 + 5
    assert result["status"] == "COMPLETED"


def test_hardcover_poor():
    result = process_book_buybacks([make_batch("hardcover", [book("poor")])], 0)
    assert result["total_payout"] == 6.0  # 15*0.40


def test_unknown_format_rejected():
    result = process_book_buybacks([make_batch("comic", [book()])], 0)
    assert result["status"] == "ZERO_CREDIT"


def test_missing_pages_rejected():
    result = process_book_buybacks([make_batch("paperback", [book(missing=3)])], 0)
    assert result["status"] == "ZERO_CREDIT"


def test_counterfeit_textbook_wipes_batch():
    books = [book("good"), book(counterfeit=True), book("good")]
    result = process_book_buybacks([make_batch("textbook", books)], 0)
    assert result["status"] == "ZERO_CREDIT"


def test_counterfeit_paperback_only_that_book_rejected():
    books = [book(counterfeit=True), book("good")]
    result = process_book_buybacks([make_batch("paperback", books)], 0)
    assert result["total_payout"] == 8.0
    assert result["status"] == "COMPLETED"


def test_audit_rejected_when_more_than_four_rejections():
    books = [book(missing=1)] * 5
    result = process_book_buybacks([make_batch("paperback", books)], 0)
    assert result["status"] == "AUDIT_REJECTED"


# ---- inspect_scanner_calibration ----
def test_scanner_no_data():
    assert inspect_scanner_calibration([]) == "NO_DATA"


def test_scanner_recalibrate():
    assert inspect_scanner_calibration([[1, 6, 7]]) == "RECALIBRATE"


def test_scanner_calibrated():
    assert inspect_scanner_calibration([[1, 6, 2, 6]]) == "CALIBRATED"
