"""
eval_harness.py — Evaluation harness for IR pipeline

Runs evaluation queries through the live retrieval pipeline and computes
standard IR metrics (precision@k, MRR, recall@k, F1@k).

Usage:
    cd BACKEND
    python eval_harness.py

Requirements:
    - Indexed library data in vector store
    - Backend dependencies installed
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Set
from pathlib import Path

from eval_dataset import get_dataset
from eval_metrics import (
    compute_metrics,
    compute_aggregate_metrics,
    format_metrics,
    MetricResult,
)

# Optional import - allows testing metrics without full pipeline
try:
    from retriever import hybrid_retrieve
    HAS_RETRIEVER = True
except ImportError as e:
    print(f"Warning: Could not import retriever: {e}")
    print("Running in mock mode for metric testing only.")
    HAS_RETRIEVER = False


def extract_function_names(retrieval_result: Dict[str, Any]) -> List[str]:
    """
    Extract function names from retrieval results.
    
    Args:
        retrieval_result: Result from hybrid_retrieve()
    
    Returns:
        List of function names in ranked order
    """
    fused_results = retrieval_result.get("fused_results", [])
    function_names = []
    
    for item in fused_results:
        # Try to get function_name from metadata
        metadata = item.get("metadata", {})
        func_name = metadata.get("name") or item.get("function_name")
        
        if func_name:
            function_names.append(func_name)
        else:
            # Fallback: use chunk_id if no function name
            function_names.append(item.get("chunk_id", ""))
    
    return function_names


def normalize_function_name(name: str) -> str:
    """
    Normalize function name for comparison.
    
    Handles variations like:
    - pandas.read_csv vs read_csv
    - DataFrame.to_csv vs to_csv
    - Case differences
    """
    if not name:
        return ""
    
    # Remove common prefixes
    name = name.replace("pandas.", "")
    name = name.replace("numpy.", "")
    name = name.replace("sklearn.", "")
    
    # Convert to lowercase for case-insensitive matching
    return name.lower().strip()


def matches_relevant(retrieved_name: str, relevant_set: Set[str]) -> bool:
    """
    Check if retrieved function matches any relevant function.
    
    Uses normalized comparison to handle naming variations.
    """
    normalized_retrieved = normalize_function_name(retrieved_name)
    
    for relevant in relevant_set:
        if normalize_function_name(relevant) == normalized_retrieved:
            return True
    
    return False


def evaluate_single_query(
    query_data: Dict[str, Any],
    k_values: List[int] = [1, 3, 5, 10],
    verbose: bool = False,
) -> tuple[MetricResult, Dict[str, Any]]:
    """
    Evaluate a single query against the retrieval pipeline.
    
    Args:
        query_data: Query dict with 'query' and 'relevant_functions'
        k_values: k values for precision/recall metrics
        verbose: Print detailed output
    
    Returns:
        Tuple of (MetricResult, debug_info)
    """
    query = query_data["query"]
    relevant_functions = set(query_data["relevant_functions"])
    expected_intent = query_data.get("intent", "function_search")
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Expected intent: {expected_intent}")
        print(f"Relevant functions: {relevant_functions}")
    
    if not HAS_RETRIEVER:
        # Mock mode for testing metrics without pipeline
        print("Warning: Running in mock mode (no retriever available)")
        # Return zero metrics
        zero_metrics = MetricResult(
            precision_at_k={k: 0.0 for k in k_values},
            mrr=0.0,
            recall_at_k={k: 0.0 for k in k_values},
            f1_at_k={k: 0.0 for k in k_values},
            avg_precision=0.0,
        )
        debug_info = {
            "query": query,
            "error": "Retriever not available - mock mode",
        }
        return zero_metrics, debug_info
    
    try:
        # Run retrieval pipeline
        result = hybrid_retrieve(query=query, source_url=None)
        
        # Extract function names from results
        retrieved_functions = extract_function_names(result)
        
        if verbose:
            print(f"\nRetrieved {len(retrieved_functions)} functions:")
            for i, func in enumerate(retrieved_functions[:10], 1):
                print(f"  {i}. {func}")
        
        # Normalize relevant functions for matching
        normalized_relevant = {normalize_function_name(f) for f in relevant_functions}
        
        # Check which retrieved functions are relevant
        relevant_retrieved = [
            f for f in retrieved_functions
            if matches_relevant(f, normalized_relevant)
        ]
        
        if verbose:
            print(f"\nRelevant retrieved: {relevant_retrieved}")
        
        # Compute metrics
        metrics = compute_metrics(
            retrieved=[normalize_function_name(f) for f in retrieved_functions],
            relevant=normalized_relevant,
            k_values=k_values,
        )
        
        debug_info = {
            "query": query,
            "expected_intent": expected_intent,
            "retrieved_count": len(retrieved_functions),
            "relevant_count": len(relevant_functions),
            "relevant_retrieved_count": len(relevant_retrieved),
            "retrieved_functions": retrieved_functions,
            "relevant_retrieved": relevant_retrieved,
        }
        
        return metrics, debug_info
        
    except Exception as e:
        print(f"Error processing query '{query}': {e}")
        # Return zero metrics on error
        zero_metrics = MetricResult(
            precision_at_k={k: 0.0 for k in k_values},
            mrr=0.0,
            recall_at_k={k: 0.0 for k in k_values},
            f1_at_k={k: 0.0 for k in k_values},
            avg_precision=0.0,
        )
        debug_info = {
            "query": query,
            "error": str(e),
        }
        return zero_metrics, debug_info


def run_evaluation(
    dataset: List[Dict[str, Any]] = None,
    k_values: List[int] = [1, 3, 5, 10],
    verbose: bool = False,
    output_file: str = None,
) -> Dict[str, float]:
    """
    Run full evaluation on dataset.
    
    Args:
        dataset: Evaluation dataset (uses default if None)
        k_values: k values for metrics
        verbose: Print per-query details
        output_file: Path to save JSON results
    
    Returns:
        Dictionary of aggregate metrics
    """
    if dataset is None:
        dataset = get_dataset()
    
    print("=" * 60)
    print("Documentor IR Evaluation Harness")
    print(f"Dataset: {len(dataset)} queries")
    print(f"K values: {k_values}")
    print("=" * 60)
    
    all_results = []
    all_debug_info = []
    
    for i, query_data in enumerate(dataset, 1):
        print(f"\n[{i}/{len(dataset)}] Processing: {query_data['query'][:50]}...")
        
        metrics, debug_info = evaluate_single_query(
            query_data, k_values=k_values, verbose=verbose
        )
        
        all_results.append(metrics)
        all_debug_info.append(debug_info)
    
    # Compute aggregate metrics
    aggregate = compute_aggregate_metrics(all_results, k_values=k_values)
    
    # Print results
    print("\n" + format_metrics(aggregate))
    
    # Save results if output file specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "dataset_size": len(dataset),
            "k_values": k_values,
            "aggregate_metrics": aggregate,
            "per_query_results": [
                {
                    "query": debug["query"],
                    "error": debug.get("error"),
                    "metrics": {
                        "precision_at_k": result.precision_at_k,
                        "mrr": result.mrr,
                        "recall_at_k": result.recall_at_k,
                        "f1_at_k": result.f1_at_k,
                        "avg_precision": result.avg_precision,
                    },
                    "debug": debug,
                }
                for result, debug in zip(all_results, all_debug_info)
            ],
        }
        
        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
    
    return aggregate


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate IR pipeline")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-query details"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="eval_results.json",
        help="Output JSON file path"
    )
    parser.add_argument(
        "--k",
        type=int,
        nargs="+",
        default=[1, 3, 5, 10],
        help="K values for precision/recall (default: 1 3 5 10)"
    )
    
    args = parser.parse_args()
    
    try:
        aggregate = run_evaluation(
            k_values=args.k,
            verbose=args.verbose,
            output_file=args.output,
        )
        
        # Exit with error if metrics are too low
        if aggregate.get("MRR", 0) < 0.1:
            print("\n⚠️  Warning: MRR is very low. Check if data is indexed.")
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
