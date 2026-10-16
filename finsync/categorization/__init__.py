"""Transaction categorization. The rule-based categorizer is the baseline."""

from finsync.categorization.rules import categorize_transaction

__all__ = ["categorize_transaction"]
