"""
test_eval_metrics.py — Unit tests for evaluation metrics

Tests the metric calculation functions independently of the pipeline.
"""

import pytest
from eval_metrics import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    average_precision,
    f1_at_k,
    compute_metrics,
    compute_aggregate_metrics,
    MetricResult,
)


class TestPrecisionAtK:
    """Test precision@k calculation."""

    def test_perfect_precision(self):
        """All retrieved items are relevant."""
        result = precision_at_k(["a", "b", "c"], {"a", "b", "c"}, 3)
        assert result == 1.0

    def test_zero_precision(self):
        """No retrieved items are relevant."""
        result = precision_at_k(["x", "y", "z"], {"a", "b", "c"}, 3)
        assert result == 0.0

    def test_partial_precision(self):
        """Some retrieved items are relevant."""
        result = precision_at_k(["a", "x", "b"], {"a", "b", "c"}, 3)
        assert result == 2/3

    def test_k_larger_than_retrieved(self):
        """k larger than number of retrieved items."""
        result = precision_at_k(["a", "b"], {"a", "b"}, 5)
        # 2 relevant out of 5 positions = 0.4
        assert result == 0.4

    def test_k_zero(self):
        """k=0 should return 0."""
        result = precision_at_k(["a", "b"], {"a"}, 0)
        assert result == 0.0


class TestRecallAtK:
    """Test recall@k calculation."""

    def test_perfect_recall(self):
        """All relevant items retrieved."""
        result = recall_at_k(["a", "b", "c"], {"a", "b", "c"}, 10)
        assert result == 1.0

    def test_zero_recall(self):
        """No relevant items retrieved."""
        result = recall_at_k(["x", "y"], {"a", "b"}, 10)
        assert result == 0.0

    def test_partial_recall(self):
        """Some relevant items retrieved."""
        result = recall_at_k(["a", "x"], {"a", "b", "c"}, 10)
        assert result == 1/3

    def test_empty_relevant_set(self):
        """Empty relevant set should return 0."""
        result = recall_at_k(["a", "b"], set(), 10)
        assert result == 0.0


class TestReciprocalRank:
    """Test reciprocal rank calculation."""

    def test_first_item_relevant(self):
        """First item is relevant."""
        result = reciprocal_rank(["a", "x", "y"], {"a", "b"})
        assert result == 1.0

    def test_second_item_relevant(self):
        """Second item is relevant."""
        result = reciprocal_rank(["x", "a", "y"], {"a", "b"})
        assert result == 0.5

    def test_no_relevant_items(self):
        """No relevant items in results."""
        result = reciprocal_rank(["x", "y", "z"], {"a", "b"})
        assert result == 0.0

    def test_later_item_relevant(self):
        """Relevant item at position 5."""
        result = reciprocal_rank(["x", "y", "z", "w", "a"], {"a"})
        assert result == 0.2


class TestAveragePrecision:
    """Test average precision calculation."""

    def test_perfect_ap(self):
        """All items relevant in order."""
        result = average_precision(["a", "b", "c"], {"a", "b", "c"})
        assert result == 1.0

    def test_zero_ap(self):
        """No relevant items."""
        result = average_precision(["x", "y", "z"], {"a", "b"})
        assert result == 0.0

    def test_partial_ap(self):
        """Some relevant items."""
        result = average_precision(["x", "a", "y", "b"], {"a", "b"})
        # Precision at rank 2: 1/2, at rank 4: 2/4
        # AP = (1/2 + 2/4) / 2 = 0.5
        assert result == 0.5

    def test_empty_relevant(self):
        """Empty relevant set."""
        result = average_precision(["a", "b"], set())
        assert result == 0.0


class TestF1AtK:
    """Test F1@k calculation."""

    def test_perfect_f1(self):
        """Perfect precision and recall."""
        result = f1_at_k(["a", "b", "c"], {"a", "b", "c"}, 3)
        assert result == 1.0

    def test_zero_f1(self):
        """Zero precision or recall."""
        result = f1_at_k(["x", "y"], {"a", "b"}, 2)
        assert result == 0.0

    def test_balanced_f1(self):
        """Equal precision and recall."""
        result = f1_at_k(["a", "x"], {"a", "b"}, 2)
        # P = 0.5, R = 0.5, F1 = 2*0.5*0.5/(0.5+0.5) = 0.5
        assert result == 0.5


class TestComputeMetrics:
    """Test the compute_metrics function."""

    def test_full_metrics(self):
        """Test computing all metrics at once."""
        result = compute_metrics(
            retrieved=["a", "b", "x", "c"],
            relevant={"a", "b", "c"},
            k_values=[1, 3, 5]
        )
        
        assert isinstance(result, MetricResult)
        assert result.precision_at_k[1] == 1.0  # First is relevant
        assert result.mrr == 1.0  # First is relevant
        assert result.avg_precision > 0
        assert result.f1_at_k[3] > 0


class TestAggregateMetrics:
    """Test aggregation across multiple queries."""

    def test_mean_metrics(self):
        """Test computing mean across multiple results."""
        results = [
            MetricResult(
                precision_at_k={1: 1.0, 3: 0.5},
                mrr=1.0,
                recall_at_k={1: 0.5, 3: 0.5},
                f1_at_k={1: 0.67, 3: 0.5},
                avg_precision=0.75,
            ),
            MetricResult(
                precision_at_k={1: 0.0, 3: 0.33},
                mrr=0.5,
                recall_at_k={1: 0.0, 3: 0.33},
                f1_at_k={1: 0.0, 3: 0.33},
                avg_precision=0.25,
            ),
        ]
        
        aggregate = compute_aggregate_metrics(results, k_values=[1, 3])
        
        assert aggregate["MRR"] == 0.75  # (1.0 + 0.5) / 2
        assert aggregate["MAP"] == 0.5  # (0.75 + 0.25) / 2
        assert aggregate["Precision@1"] == 0.5  # (1.0 + 0.0) / 2

    def test_empty_results(self):
        """Empty results should return empty dict."""
        aggregate = compute_aggregate_metrics([])
        assert aggregate == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
