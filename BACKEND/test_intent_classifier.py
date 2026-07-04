"""
test_intent_classifier.py — Unit tests for intent classifier

Tests the intent classification logic to ensure proper detection of:
- Error fix queries (tracebacks, error names)
- Concept explanation queries
- Function search queries
- Ambiguous queries requiring LLM disambiguation
- Edge cases (empty queries, etc.)

Run with:
    cd BACKEND
    pytest test_intent_classifier.py -v
"""

import pytest
from intent_classifier import (
    classify_intent,
    IntentClassification,
    INTENT_FUNCTION_SEARCH,
    INTENT_ERROR_FIX,
    INTENT_CONCEPT_EXPLAIN,
    ALLOWED_INTENTS,
)


class TestErrorFixDetection:
    """Test detection of error/fix intent."""

    def test_traceback_pattern(self):
        """Should detect error_fix when traceback is present."""
        query = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    x = undefined_var
NameError: name 'undefined_var' is not defined
"""
        result = classify_intent(query)
        assert result.intent == INTENT_ERROR_FIX
        assert "Traceback" in result.reason
        assert not result.used_llm

    def test_file_line_error_pattern(self):
        """Should detect error_fix with file/line pattern."""
        query = 'File "script.py", line 42, in function'
        result = classify_intent(query)
        assert result.intent == INTENT_ERROR_FIX
        assert not result.used_llm

    def test_capitalized_error_name(self):
        """Should detect error_fix starting with capitalized error name."""
        queries = [
            "NameError: variable not defined",
            "ValueError: invalid literal for int()",
            "TypeError: unsupported operand type",
            "KeyError: 'column_name'",
            "AttributeError: module has no attribute",
            "ImportError: No module named 'sklearn'",
            "RuntimeError: maximum recursion depth exceeded",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_ERROR_FIX, f"Failed for: {query}"
            assert "error name" in result.reason.lower()
            assert not result.used_llm

    def test_error_name_with_exception_suffix(self):
        """Should detect error names ending in Exception/Warning/Fault."""
        queries = [
            "CustomException: something went wrong",
            "UserWarning: deprecated usage",
            "SystemFault: critical failure",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_ERROR_FIX, f"Failed for: {query}"
            assert not result.used_llm

    def test_error_case_insensitive(self):
        """Error detection should be case-insensitive for traceback patterns."""
        query = "TRACEBACK (MOST RECENT CALL LAST):"
        result = classify_intent(query)
        assert result.intent == INTENT_ERROR_FIX
        assert not result.used_llm


class TestConceptQueryDetection:
    """Test detection of concept explanation intent."""

    def test_concept_prefix_words(self):
        """Should detect concept queries starting with concept-specific words."""
        queries = [
            "Why does pandas use copy-on-write?",
            "Explain the difference between loc and iloc",
            "Difference between list and tuple",
            "Compare merge and join",
            "Concept of virtual environments",
            "Meaning of __init__ in Python",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_CONCEPT_EXPLAIN, f"Failed for: {query}"
            assert "concept" in result.reason.lower()
            assert not result.used_llm

    def test_concept_hint_words(self):
        """Should detect concept queries containing hint words."""
        queries = [
            "What is the trade-off between speed and memory?",
            "How does garbage collection work internally?",
            "When should I use list comprehension?",
            "Architecture of React components",
            "Internals of Python's GIL",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_CONCEPT_EXPLAIN, f"Failed for: {query}"
            assert not result.used_llm

    def test_how_does_pattern(self):
        """'How does' should trigger concept intent."""
        query = "How does the map function work?"
        result = classify_intent(query)
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm

    def test_when_should_pattern(self):
        """'When should' should trigger concept intent."""
        query = "When should I use async vs await?"
        result = classify_intent(query)
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm


class TestFunctionQueryDetection:
    """Test detection of function search intent (default fallback)."""

    def test_function_hint_words(self):
        """Should detect function queries with function-specific words."""
        queries = [
            "How do I read a CSV file?",
            "Which function sorts a list?",
            "Best way to parse JSON",
            "API for making HTTP requests",
            "Method to split a string",
            "Parameters for the plot function",
            "Arguments for the fit method",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_FUNCTION_SEARCH, f"Failed for: {query}"
            assert not result.used_llm

    def test_parentheses_pattern(self):
        """Queries with parentheses should be function search."""
        queries = [
            "How to use pandas.read_csv()",
            "What does print() do?",
            "Usage of len() function",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_FUNCTION_SEARCH, f"Failed for: {query}"
            assert not result.used_llm

    def test_default_fallback(self):
        """Generic queries should default to function search."""
        queries = [
            "normalize data",
            "sort array",
            "filter list",
            "transform dataframe",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_FUNCTION_SEARCH, f"Failed for: {query}"
            assert "fallback" in result.reason.lower()
            assert not result.used_llm


class TestAmbiguousQueries:
    """Test queries that could match multiple intents."""

    def test_concept_and_function_hints(self):
        """Queries with both concept and function hints without LLM should prefer concept."""
        query = "Explain the function parameters for pandas merge"
        result = classify_intent(query, llm_disambiguator=None)
        # Without LLM, concept prefix wins
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm

    def test_ambiguous_with_llm_disambiguator(self):
        """Ambiguous queries should use LLM when available."""
        # This query has both concept ("how does") and function ("function") hints
        query = "How does the map function work"
        
        def mock_llm_disambiguator(text: str) -> str:
            return INTENT_FUNCTION_SEARCH
        
        result = classify_intent(query, llm_disambiguator=mock_llm_disambiguator)
        assert result.intent == INTENT_FUNCTION_SEARCH
        assert result.used_llm
        assert "LLM" in result.reason

    def test_llm_returns_invalid_intent(self):
        """Should ignore LLM if it returns invalid intent."""
        query = "How does the function work"
        
        def mock_llm_disambiguator(text: str) -> str:
            return "invalid_intent"
        
        result = classify_intent(query, llm_disambiguator=mock_llm_disambiguator)
        # Should fall back to concept detection
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm

    def test_llm_returns_none(self):
        """Should handle LLM returning None gracefully."""
        query = "How does the function work"
        
        def mock_llm_disambiguator(text: str) -> str:
            return None
        
        result = classify_intent(query, llm_disambiguator=mock_llm_disambiguator)
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_query(self):
        """Empty query should fallback to function search."""
        result = classify_intent("")
        assert result.intent == INTENT_FUNCTION_SEARCH
        assert "empty" in result.reason.lower()
        assert not result.used_llm

    def test_whitespace_only_query(self):
        """Whitespace-only query should be treated as empty."""
        result = classify_intent("   \n\t  ")
        assert result.intent == INTENT_FUNCTION_SEARCH
        assert not result.used_llm

    def test_case_insensitive_matching(self):
        """Pattern matching should be case-insensitive."""
        queries = [
            "WHY DOES THIS HAPPEN",
            "Explain the concept",
            "DIFFERENCE BETWEEN X AND Y",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_CONCEPT_EXPLAIN, f"Failed for: {query}"
            assert not result.used_llm

    def test_leading_whitespace(self):
        """Leading whitespace should not affect classification."""
        query = "   Explain the difference"
        result = classify_intent(query)
        assert result.intent == INTENT_CONCEPT_EXPLAIN
        assert not result.used_llm

    def test_mixed_case_error_name(self):
        """Error names should match regardless of case after first letter."""
        queries = [
            "NameError: test",
            "ValueError: test",
            "CustomError: test",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_ERROR_FIX, f"Failed for: {query}"
            assert not result.used_llm

    def test_error_name_not_at_start(self):
        """Error name not at start should not trigger error_fix."""
        query = "I have a question about NameError"
        result = classify_intent(query)
        # Should not match error pattern since it doesn't start with error name
        assert result.intent != INTENT_ERROR_FIX
        assert not result.used_llm


class TestIntentConstants:
    """Test that intent constants are properly defined."""

    def test_allowed_intents_set(self):
        """ALLOWED_INTENTS should contain all intent constants."""
        assert INTENT_FUNCTION_SEARCH in ALLOWED_INTENTS
        assert INTENT_ERROR_FIX in ALLOWED_INTENTS
        assert INTENT_CONCEPT_EXPLAIN in ALLOWED_INTENTS

    def test_intent_values_are_strings(self):
        """Intent constants should be strings."""
        assert isinstance(INTENT_FUNCTION_SEARCH, str)
        assert isinstance(INTENT_ERROR_FIX, str)
        assert isinstance(INTENT_CONCEPT_EXPLAIN, str)


class TestRealWorldQueries:
    """Test with realistic user queries."""

    def test_real_error_queries(self):
        """Test actual error messages users might submit."""
        queries = [
            "ModuleNotFoundError: No module named 'sklearn'",
            "KeyError: 'column_name' in dataframe",
            "TypeError: can only concatenate str (not \"int\") to str",
            "AttributeError: 'DataFrame' object has no attribute 'to_csv'",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_ERROR_FIX, f"Failed for: {query}"
            assert not result.used_llm

    def test_real_function_queries(self):
        """Test actual function search queries."""
        queries = [
            "How do I normalize data in pandas?",
            "Which function should I use to read a CSV?",
            "Best way to sort a list of dictionaries",
            "API for making HTTP requests in Python",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_FUNCTION_SEARCH, f"Failed for: {query}"
            assert not result.used_llm

    def test_real_concept_queries(self):
        """Test actual concept explanation queries."""
        queries = [
            "What's the difference between loc and iloc?",
            "Why should I avoid using iterrows?",
            "Explain the concept of virtual environments",
            "How does Python's garbage collection work?",
        ]
        for query in queries:
            result = classify_intent(query)
            assert result.intent == INTENT_CONCEPT_EXPLAIN, f"Failed for: {query}"
            assert not result.used_llm


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
