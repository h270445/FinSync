package hu.finsync.spike

/**
 * The only apps whose notifications the spike reads. Matching is by package name (the
 * application id shown in the Play Store link, `?id=...`), which is stable and unique,
 * unlike the app's display name. Notifications of every other app are dropped unread.
 */
object BankApps {
    val packages: Map<String, String> = mapOf(
        "hu.otpbank.mobile" to "OTP Bank", // confirmed on the test phone, 2026-10-27
        "com.revolut.revolut" to "Revolut",
    )

    /** Sender of `adb shell cmd notification post`; watched only in debug builds, for simulated bank notifications. */
    const val ADB_SHELL = "com.android.shell"

    fun isBank(packageName: String): Boolean = packageName in packages
}
