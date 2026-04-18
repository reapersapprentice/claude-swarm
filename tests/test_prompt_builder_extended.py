"""Extended tests for PromptBuilder encoding fallback and warnings."""

from __future__ import annotations

import warnings

from token_infra.prompt_builder import PromptBuilder, PromptBuildResult


def _make_builder() -> PromptBuilder:
    """Create a PromptBuilder that always uses the word-based fallback."""
    pb = PromptBuilder(schema_path="configs/prompt_schema.yaml")
    # Force fallback path regardless of tiktoken availability.
    pb._encoding_failed = True
    return pb


class TestEstimateTokens:
    """Tests for estimate_tokens edge cases and fallback behaviour."""

    def test_empty_string_returns_zero(self) -> None:
        pb = _make_builder()
        assert pb.estimate_tokens("") == 0

    def test_whitespace_only_returns_zero(self) -> None:
        pb = _make_builder()
        assert pb.estimate_tokens("   \n\t  ") == 0

    def test_word_based_fallback_formula(self) -> None:
        pb = _make_builder()
        text = "the quick brown fox jumps over the lazy dog"
        expected = int(len(text.split()) * 1.3) + 1
        assert pb.estimate_tokens(text) == expected

    def test_fallback_result_is_int(self) -> None:
        pb = _make_builder()
        result = pb.estimate_tokens("hello world")
        assert isinstance(result, int)


class TestEncodingCaching:
    """Verify _encoding_failed flag prevents repeated warnings."""

    def test_encoding_failed_is_cached(self) -> None:
        pb = PromptBuilder(schema_path="configs/prompt_schema.yaml")
        # Ensure we start clean.
        pb._encoding = None
        pb._encoding_failed = False

        # First call — may warn if tiktoken is present but network fails,
        # or return None silently if tiktoken is absent.
        with warnings.catch_warnings(record=True) as w1:
            warnings.simplefilter("always")
            result1 = pb._get_encoding()

        # After the first call the flag should be set (tiktoken missing or
        # encoding download failed) so the second call must NOT warn again.
        with warnings.catch_warnings(record=True) as w2:
            warnings.simplefilter("always")
            result2 = pb._get_encoding()

        if result1 is None:
            # Fallback path — no new warning on the second call.
            tiktoken_warnings = [
                x for x in w2 if "tiktoken" in str(x.message)
            ]
            assert tiktoken_warnings == []
            assert pb._encoding_failed or result1 is not None


class TestBuildFallbacks:
    """Tests for build() behaviour with missing keys."""

    def test_missing_template_key_uses_default_format(self) -> None:
        pb = _make_builder()
        result = pb.build(
            template_key="NONEXISTENT_TEMPLATE",
            role_key="ROLE_ENGINEER",
            task="do something",
            context="some context",
        )
        assert "do something" in result.user_prompt
        assert "some context" in result.user_prompt
        # Default template is "{task}\n\n{context}"
        assert result.user_prompt == "do something\n\nsome context"

    def test_missing_role_key_produces_empty_role(self) -> None:
        pb = _make_builder()
        result = pb.build(
            template_key="CODE_REVIEW",
            role_key="NONEXISTENT_ROLE",
            task="review code",
        )
        # With an empty role block, system_prompt should only contain rules (if any).
        assert "NONEXISTENT_ROLE" not in result.system_prompt


class TestBuildResult:
    """Tests for the PromptBuildResult returned by build()."""

    def test_returns_prompt_build_result(self) -> None:
        pb = _make_builder()
        result = pb.build(
            template_key="CODE_REVIEW",
            role_key="ROLE_ENGINEER",
            task="review this code",
            context="file: main.py",
        )
        assert isinstance(result, PromptBuildResult)

    def test_result_has_correct_fields(self) -> None:
        pb = _make_builder()
        result = pb.build(
            template_key="CODE_REVIEW",
            role_key="ROLE_ENGINEER",
            task="review this code",
            context="file: main.py",
        )
        assert isinstance(result.system_prompt, str)
        assert isinstance(result.user_prompt, str)
        assert isinstance(result.token_estimate, int)
        assert result.token_estimate > 0

    def test_build_with_custom_ruleset_keys(self) -> None:
        pb = _make_builder()
        result = pb.build(
            template_key="CODE_REVIEW",
            role_key="ROLE_ENGINEER",
            task="check code",
            ruleset_keys=["T0", "T2"],
        )
        assert "T0" in result.system_prompt
        assert "T2" in result.system_prompt
        # Default keys should not appear when custom ones are provided.
        assert "T1:" not in result.system_prompt
        assert "T5:" not in result.system_prompt

    def test_build_with_metadata(self) -> None:
        pb = _make_builder()
        # Default template includes {metadata} via str.format; verify it
        # renders into the user_prompt without error.
        result = pb.build(
            template_key="NONEXISTENT_TEMPLATE",
            role_key="ROLE_ENGINEER",
            task="summarise",
            context="ctx",
            metadata={"lang": "python", "version": 3},
        )
        assert "summarise" in result.user_prompt
