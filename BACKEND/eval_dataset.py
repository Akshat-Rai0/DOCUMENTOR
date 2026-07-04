"""
eval_dataset.py — Evaluation dataset for IR metrics

Contains test queries with ground truth relevant function names.
Used by eval_harness.py to compute precision@k, MRR, and answer relevance.

Format:
- query: The user's natural language query
- relevant_functions: List of function names that should be retrieved
- intent: Expected intent classification
"""

EVALUATION_QUERIES = [
    {
        "query": "How do I read a CSV file in pandas?",
        "relevant_functions": ["read_csv", "pandas.read_csv"],
        "intent": "function_search",
        "description": "Basic CSV reading function"
    },
    {
        "query": "normalize data in pandas",
        "relevant_functions": ["normalize", "StandardScaler", "MinMaxScaler"],
        "intent": "function_search",
        "description": "Data normalization functions"
    },
    {
        "query": "sort a list of dictionaries",
        "relevant_functions": ["sorted", "sort", "list.sort"],
        "intent": "function_search",
        "description": "Sorting functions for complex data structures"
    },
    {
        "query": "What's the difference between loc and iloc?",
        "relevant_functions": ["loc", "iloc"],
        "intent": "concept_explain",
        "description": "Concept comparison between indexing methods"
    },
    {
        "query": "Why should I avoid using iterrows?",
        "relevant_functions": ["iterrows", "itertuples", "apply"],
        "intent": "concept_explain",
        "description": "Anti-pattern explanation"
    },
    {
        "query": "ModuleNotFoundError: No module named 'sklearn'",
        "relevant_functions": ["pip install", "import", "sys.path"],
        "intent": "error_fix",
        "description": "Import error resolution"
    },
    {
        "query": "KeyError: 'column_name' in dataframe",
        "relevant_functions": ["columns", "rename", "set_index"],
        "intent": "error_fix",
        "description": "DataFrame column access error"
    },
    {
        "query": "TypeError: unsupported operand type(s)",
        "relevant_functions": ["astype", "str()", "int()", "float()"],
        "intent": "error_fix",
        "description": "Type conversion error"
    },
    {
        "query": "Which function should I use to merge dataframes?",
        "relevant_functions": ["merge", "join", "concat"],
        "intent": "function_search",
        "description": "Dataframe combination functions"
    },
    {
        "query": "How does the map function work?",
        "relevant_functions": ["map", "applymap", "apply"],
        "intent": "concept_explain",
        "description": "Understanding map vs apply"
    },
    {
        "query": "filter rows based on condition",
        "relevant_functions": ["query", "loc", "boolean indexing"],
        "intent": "function_search",
        "description": "Row filtering methods"
    },
    {
        "query": "drop missing values",
        "relevant_functions": ["dropna", "fillna", "isna"],
        "intent": "function_search",
        "description": "Missing data handling"
    },
    {
        "query": "AttributeError: 'DataFrame' object has no attribute 'to_csv'",
        "relevant_functions": ["to_csv", "DataFrame.to_csv"],
        "intent": "error_fix",
        "description": "Method not found error"
    },
    {
        "query": "group by column and aggregate",
        "relevant_functions": ["groupby", "agg", "aggregate"],
        "intent": "function_search",
        "description": "Grouping and aggregation"
    },
    {
        "query": "When should I use list comprehension?",
        "relevant_functions": ["list comprehension", "map", "filter"],
        "intent": "concept_explain",
        "description": "Best practices for list operations"
    },
]


def get_dataset():
    """Return the evaluation dataset."""
    return EVALUATION_QUERIES


def get_queries_by_intent(intent: str):
    """Return queries filtered by intent."""
    return [q for q in EVALUATION_QUERIES if q["intent"] == intent]
