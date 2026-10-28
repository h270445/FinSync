package hu.finsync.spike

import java.security.MessageDigest

/**
 * Tells transaction notifications from everything else a bank app posts (marketing, news,
 * security tips), so only likely transactions are kept in full. A notification counts as a
 * transaction candidate when any of its texts contains an amount with a currency, such as
 * `-4 500 Ft`, `1,234.56 HUF` or `€4.50`. Everything else is kept only in masked form.
 */
object TransactionFilter {
    private val CURRENCY = "(?:Ft|HUF|EUR|USD|GBP|CHF)"
    private val NUMBER = """\d{1,3}(?:[   .,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"""
    private val AMOUNT = Regex(
        """[+\-−]?\s?(?:$NUMBER)\s?$CURRENCY\b|$CURRENCY\s?(?:$NUMBER)|[€${'$'}£]\s?\d|\d\s?[€${'$'}£]""",
        RegexOption.IGNORE_CASE,
    )

    fun looksLikeTransaction(texts: List<String>): Boolean = texts.any { AMOUNT.containsMatchIn(it) }

    /** Keeps the shape of a text without its content: letters become a/A, digits 9. */
    fun mask(text: String): String = buildString(text.length) {
        for (c in text) {
            append(
                when {
                    c.isDigit() -> '9'
                    c.isUpperCase() -> 'A'
                    c.isLetter() -> 'a'
                    else -> c
                }
            )
        }
    }

    /** Short stable hash, so a removal can be matched to its post without storing the key. */
    fun hash(value: String): String =
        MessageDigest.getInstance("SHA-256").digest(value.toByteArray())
            .take(8).joinToString("") { "%02x".format(it) }
}
