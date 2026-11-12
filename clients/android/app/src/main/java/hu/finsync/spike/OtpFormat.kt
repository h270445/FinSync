package hu.finsync.spike

/**
 * The M2 forwarding rule: only notifications that match a known OTP Bank transaction pattern leave
 * the phone (accept, do not reject; 2026-10-28). Everything else is dropped and only counted.
 *
 * The text starts with the signed amount, a space as thousands separator and the currency (`Ft`).
 * A transfer continues with a comma and the counterparty, a card purchase with a sentence that
 * names the merchant in capitals. Written from the masked shapes in
 * docs/design/android-notification-spike.md; the server parser in
 * finsync/ingestion/notifications.py has the same rule and stays the authority (400 = not a transaction).
 */
object OtpFormat {
    const val PACKAGE = "hu.otpbank.mobile"

    private const val CAPS = "A-ZÁÉÍÓÖŐÚÜŰ"
    private val AMOUNT = Regex("""^[+-]\d{1,3}(?:[   ]\d{3})*(?:,\d{1,2})?[  ](?:Ft|[A-Z]{3})((?:,| ).*)$""")
    private val CAPITAL_WORD = Regex("""[${CAPS}0-9&.'-]*[${CAPS}][${CAPS}0-9&.'-]*""")
    // The transaction number at the end of the tag ("AAA-Aaaaaaaaaaaa:999999999").
    private val TAG_REFERENCE = Regex(""":(\d{6,})$""")

    fun isTransaction(text: String?): Boolean {
        val match = AMOUNT.matchEntire(text?.trim() ?: return false) ?: return false
        val rest = match.groupValues[1]
        if (rest.startsWith(",")) return rest.drop(1).trim().trimEnd('.').isNotBlank()
        return rest.split(' ').any { token ->
            val word = token.trim('.', ',', '!', '?', '-', '\'', '&')
            word.length >= 2 && CAPITAL_WORD.matches(word)
        }
    }

    /** The bank's transaction number from the notification tag, used as `source_ref`; null if the tag has none. */
    fun sourceReference(tag: String?): String? = tag?.let { TAG_REFERENCE.find(it)?.groupValues?.get(1) }
}
