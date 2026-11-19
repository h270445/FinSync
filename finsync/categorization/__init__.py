"""Transaction categorization: transfers to the group's own accounts, then the group's merchant rules,
then the keyword rules (the baseline)."""

from finsync.categorization.merchant_rules import CATEGORIES, MerchantRule, find_rule, merchant_key, validate_rule
from finsync.categorization.own_accounts import TRANSFER, OwnAccount, is_transfer, own_account_key
from finsync.categorization.rules import categorize_transaction

__all__ = [
    "CATEGORIES",
    "TRANSFER",
    "MerchantRule",
    "OwnAccount",
    "categorize_transaction",
    "find_rule",
    "is_transfer",
    "merchant_key",
    "own_account_key",
    "validate_rule",
]
