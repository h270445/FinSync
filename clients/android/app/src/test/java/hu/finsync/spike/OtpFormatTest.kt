package hu.finsync.spike

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Made-up texts in the masked shapes of docs/design/android-notification-spike.md; the same cases as tests/test_android_ingest.py. */
class OtpFormatTest {
    @Test
    fun transactionsAreForwarded() {
        for (text in listOf(
            "-4 990 Ft értékben vásárolt a PELDABOLT KFT 12. üzletében.",
            "-12 000 Ft, Minta Anna Beata",
            "+1 500 Ft, Minta Bela",
            "-990 Ft vásárlás a SPAR-123 boltban.",
            "-1 234 567 Ft vásárlás a NAGY ÁRUHÁZ boltban.",
            "-12,50 EUR vásárlás a CAFE PELDA üzletben.",
            "-4 990 Ft vásárlás a PELDABOLT üzletben.",
        )) assertTrue(text, OtpFormat.isTransaction(text))
    }

    @Test
    fun everythingElseIsDropped() {
        for (text in listOf(
            "Nyerj 10 EUR jóváírást, ha meghívod a barátodat!",
            "-4 990 Ft értékben vásároltál, köszönjük.",
            "-4 990 Ft,",
            "4 990 Ft, Minta Anna",
            "-4990Ft, Minta Anna",
            "Új üzenete érkezett.",
            "",
            null,
        )) assertFalse(text.toString(), OtpFormat.isTransaction(text))
    }

    @Test
    fun theReferenceIsTheNumberAtTheEndOfTheTag() {
        assertEquals("000000101", OtpFormat.sourceReference("OTP-Tranzakcio:000000101"))
        assertNull(OtpFormat.sourceReference("sim-1"))
        assertNull(OtpFormat.sourceReference(null))
    }
}
