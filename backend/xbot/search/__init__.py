"""
xbot.search: Unified X Search & Query Matrix Package.
"""

from xbot.search.types import SearchCategory, SearchFilters, SearchTarget
from xbot.search.query_builder import XSearchQueryBuilder
from xbot.search.matrix import SearchMatrixStrategy

__all__ = [
    "SearchCategory",
    "SearchFilters",
    "SearchTarget",
    "XSearchQueryBuilder",
    "SearchMatrixStrategy",
]
