"""Tests for utils/diff_manager.py"""

from utils.diff_manager import generate_unified_diff, apply_unified_diff


def test_generate_unified_diff_simple_change():
    original = "hello\nworld\n"
    updated = "hello\nuniverse\n"
    diff = generate_unified_diff(original, updated)
    assert "---" in diff
    assert "+++" in diff


def test_generate_unified_diff_no_changes():
    text = "same\ncontent\n"
    diff = generate_unified_diff(text, text)
    assert diff == ""


def test_generate_unified_diff_custom_filenames():
    original = "a\n"
    updated = "b\n"
    diff = generate_unified_diff(original, updated, fromfile="old.txt", tofile="new.txt")
    assert "old.txt" in diff
    assert "new.txt" in diff


def test_round_trip():
    original = "line1\nline2\nline3\n"
    updated = "line1\nmodified\nline3\nextra\n"
    diff = generate_unified_diff(original, updated)
    result = apply_unified_diff(original, diff)
    assert result == updated


def test_apply_unified_diff_empty_diff():
    original = "keep\nthis\ntext\n"
    result = apply_unified_diff(original, "")
    assert result == original


def test_apply_unified_diff_insertion_only():
    original = "a\nb\n"
    updated = "a\nnew\nb\n"
    diff = generate_unified_diff(original, updated)
    result = apply_unified_diff(original, diff)
    assert result == updated


def test_apply_unified_diff_deletion_only():
    original = "a\nremove\nb\n"
    updated = "a\nb\n"
    diff = generate_unified_diff(original, updated)
    result = apply_unified_diff(original, diff)
    assert result == updated
