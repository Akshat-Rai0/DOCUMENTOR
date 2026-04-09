"""
url_utils.py — Single source of truth for extracting library names from URLs.

Fixes Issue #3: standardises the source_url → library_name mapping used by
app.py, retriever.py, and parser.py so they all agree on the collection name.
"""

import re
from urllib.parse import urlparse


def extract_library_name(url: str) -> str:
    """
    Return a canonical, human-friendly library name from a documentation URL.

    Examples
    --------
    >>> extract_library_name("https://fastapi.tiangolo.com/")
    'fastapi'
    >>> extract_library_name("https://docs.sqlalchemy.org/en/20/")
    'sqlalchemy'
    >>> extract_library_name("https://pandas.pydata.org/docs/")
    'pandas'
    >>> extract_library_name("https://scikit-learn.org/stable/")
    'scikit-learn'
    >>> extract_library_name("https://threejs.org/docs/")
    'threejs'
    >>> extract_library_name("https://numpy.org/doc/stable/")
    'numpy'
    """
    raw = url.strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = re.sub(r"^www\.", "", parsed.netloc).lower()

    parts = host.split(".")
    # If the subdomain is a generic prefix like docs/doc/api, use the next part
    name = parts[0]
    if name in ("docs", "doc", "api") and len(parts) > 1:
        name = parts[1]

    return name
