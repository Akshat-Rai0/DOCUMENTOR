"""
eval_metrics.py — IR metric calculation functions

Implements standard Information Retrieval metrics:
- Precision@k: Fraction of relevant results in top k
- MRR (Mean Reciprocal Rank): Average of reciprocal ranks of first relevant result
- Recall@k: Fraction of relevant items retrieved in top k
- F1@k: Harmonic mean of precision and recall at k
"""

from typing import List, Set, Dict, Any
from dataclasses import dataclass


@dataclass
class MetricResult:
    """Container for metric results."""
    precision_at_k: Dict[int, float]
    mrr: float
    recall_at_k: Dict[int, float]
    f1_at_k: Dict[int, float]
    avg_precision: float


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Calculate precision@k.
    
    Args:
        retrieved: List of retrieved item IDs (function names, etc.)
        relevant: Set of relevant item IDs
        k: Number of top results to consider
    
    Returns:
        Precision@k score (0.0 to 1.0)
    """
    if k == 0:
        return 0.0
    
    top_k = retrieved[:k]
    relevant_count = sum(1 for item in top_k if item in relevant)
    
    return relevant_count / k


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Calculate recall@k.
    
    Args:
        retrieved: List of retrieved item IDs
        relevant: Set of relevant item IDs
        k: Number of top results to consider
    
    Returns:
        Recall@k score (0.0 to 1.0)
    """
    if len(relevant) == 0:
        return 0.0
    
    top_k = retrieved[:k]
    relevant_count = sum(1 for item in top_k if item in relevant)
    
    return relevant_count / len(relevant)


def reciprocal_rank(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Calculate reciprocal rank of first relevant result.
    
    Args:
        retrieved: List of retrieved item IDs
        relevant: Set of relevant item IDs
    
    Returns:
        Reciprocal rank (1/rank of first relevant, 0 if none found)
    """
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    
    return 0.0


def average_precision(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Calculate Average Precision (AP).
    
    AP is the mean of precision scores at each rank where a relevant
    item is found.
    
    Args:
        retrieved: List of retrieved item IDs
        relevant: Set of relevant item IDs
    
    Returns:
        Average precision score (0.0 to 1.0)
    """
    if len(relevant) == 0:
        return 0.0
    
    precisions = []
    relevant_found = 0
    
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            relevant_found += 1
            precisions.append(relevant_found / i)
    
    if not precisions:
        return 0.0
    
    return sum(precisions) / len(relevant)


def f1_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Calculate F1 score at k.
    
    F1 is the harmonic mean of precision and recall.
    
    Args:
        retrieved: List of retrieved item IDs
        relevant: Set of relevant item IDs
        k: Number of top results to consider
    
    Returns:
        F1@k score (0.0 to 1.0)
    """
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    
    if p + r == 0:
        return 0.0
    
    return 2 * (p * r) / (p + r)


def compute_metrics(
    retrieved: List[str],
    relevant: Set[str],
    k_values: List[int] = [1, 3, 5, 10]
) -> MetricResult:
    """
    Compute all IR metrics for a single query.
    
    Args:
        retrieved: List of retrieved item IDs
        relevant: Set of relevant item IDs
        k_values: List of k values for precision/recall/F1
    
    Returns:
        MetricResult with all computed metrics
    """
    precision_scores = {k: precision_at_k(retrieved, relevant, k) for k in k_values}
    recall_scores = {k: recall_at_k(retrieved, relevant, k) for k in k_values}
    f1_scores = {k: f1_at_k(retrieved, relevant, k) for k in k_values}
    
    mrr = reciprocal_rank(retrieved, relevant)
    ap = average_precision(retrieved, relevant)
    
    return MetricResult(
        precision_at_k=precision_scores,
        mrr=mrr,
        recall_at_k=recall_scores,
        f1_at_k=f1_scores,
        avg_precision=ap,
    )


def mean_metric(metric_values: List[float]) -> float:
    """Calculate mean of metric values across multiple queries."""
    if not metric_values:
        return 0.0
    return sum(metric_values) / len(metric_values)


def compute_aggregate_metrics(
    all_results: List[Dict[str, Any]],
    k_values: List[int] = [1, 3, 5, 10]
) -> Dict[str, float]:
    """
    Compute aggregate metrics across multiple queries.
    
    Args:
        all_results: List of MetricResult objects or dicts
        k_values: List of k values to aggregate
    
    Returns:
        Dictionary of aggregated metric names to values
    """
    if not all_results:
        return {}
    
    # Extract metric values
    mrr_values = [r.mrr for r in all_results]
    ap_values = [r.avg_precision for r in all_results]
    
    precision_at_k = {k: [] for k in k_values}
    recall_at_k = {k: [] for k in k_values}
    f1_at_k = {k: [] for k in k_values}
    
    for result in all_results:
        for k in k_values:
            precision_at_k[k].append(result.precision_at_k[k])
            recall_at_k[k].append(result.recall_at_k[k])
            f1_at_k[k].append(result.f1_at_k[k])
    
    # Compute means
    aggregate = {
        "MRR": mean_metric(mrr_values),
        "MAP": mean_metric(ap_values),
    }
    
    for k in k_values:
        aggregate[f"Precision@{k}"] = mean_metric(precision_at_k[k])
        aggregate[f"Recall@{k}"] = mean_metric(recall_at_k[k])
        aggregate[f"F1@{k}"] = mean_metric(f1_at_k[k])
    
    return aggregate


def format_metrics(metrics: Dict[str, float]) -> str:
    """Format metrics dictionary for display."""
    lines = ["=" * 60, "Evaluation Metrics", "=" * 60]
    
    # Group metrics by type
    mrr_map = [(k, v) for k, v in metrics.items() if k in ["MRR", "MAP"]]
    precision = [(k, v) for k, v in metrics.items() if k.startswith("Precision@")]
    recall = [(k, v) for k, v in metrics.items() if k.startswith("Recall@")]
    f1 = [(k, v) for k, v in metrics.items() if k.startswith("F1@")]
    
    for label, group in [
        ("Rank-based Metrics", mrr_map),
        ("Precision@k", precision),
        ("Recall@k", recall),
        ("F1@k", f1),
    ]:
        if group:
            lines.append(f"\n{label}:")
            for name, value in sorted(group):
                lines.append(f"  {name:<15}: {value:.4f}")
    
    lines.append("=" * 60)
    return "\n".join(lines)
