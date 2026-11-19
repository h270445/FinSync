"""Transaction categorization: transfers to the group's own accounts, then the hybrid categorizer's
deterministic layer (the group's merchant rules, then the built-in Hungarian dictionary). The keyword
rules of rules.py stay as the measured baseline."""

from finsync.categorization.dictionary import DICTIONARY_VERSION
from finsync.categorization.hybrid import CategoryDecision, categorize_record
from finsync.categorization.merchant_rules import CATEGORIES, MerchantRule, find_rule, merchant_key, validate_rule
from finsync.categorization.own_accounts import TRANSFER, OwnAccount, is_transfer, own_account_key
from finsync.categorization.rules import categorize_transaction

__all__ = [
    "CATEGORIES",
    "DICTIONARY_VERSION",
    "TRANSFER",
    "CategoryDecision",
    "MerchantRule",
    "OwnAccount",
    "categorize_record",
    "categorize_transaction",
    "find_rule",
    "is_transfer",
    "merchant_key",
    "own_account_key",
    "validate_rule",
]
