package hu.finsync.spike

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.time.ZoneId

/**
 * On-device storage for the spike. Nothing leaves the phone unless the user exports it.
 *
 * - `captures.jsonl`: one JSON object per line, full notification fields, only for allowed packages.
 * - `seen_packages`: package name -> count for every other app; no notification content.
 * - `allowed_packages`: the packages the user picked on the main screen (the bank app).
 */
class CaptureStore(context: Context) {
    private val captures = File(context.filesDir, "captures.jsonl")
    private val prefs = context.getSharedPreferences("spike", Context.MODE_PRIVATE)
    private val ownPackage = context.packageName

    fun isAllowed(packageName: String): Boolean =
        packageName == ownPackage || packageName in allowedPackages()

    fun allowedPackages(): Set<String> = prefs.getStringSet(KEY_ALLOWED, emptySet()).orEmpty()

    fun setAllowed(packageName: String, allowed: Boolean) {
        val updated = allowedPackages().toMutableSet()
        if (allowed) updated += packageName else updated -= packageName
        prefs.edit().putStringSet(KEY_ALLOWED, updated).apply()
    }

    @Synchronized
    fun countSeen(packageName: String) {
        val key = SEEN_PREFIX + packageName
        prefs.edit().putInt(key, prefs.getInt(key, 0) + 1).apply()
    }

    fun seenPackages(): Map<String, Int> =
        prefs.all
            .filterKeys { it.startsWith(SEEN_PREFIX) }
            .mapKeys { it.key.removePrefix(SEEN_PREFIX) }
            .mapValues { (it.value as? Int) ?: 0 }

    @Synchronized
    fun append(record: JSONObject) {
        record.put("device_time_ms", System.currentTimeMillis())
        record.put("device_zone", ZoneId.systemDefault().id)
        captures.appendText(record.toString() + "\n")
    }

    fun readAll(): List<JSONObject> =
        if (!captures.exists()) emptyList()
        else captures.readLines().filter { it.isNotBlank() }.map { JSONObject(it) }

    fun exportText(): String = if (captures.exists()) captures.readText() else ""

    @Synchronized
    fun clear() {
        captures.delete()
        val editor = prefs.edit()
        prefs.all.keys.filter { it.startsWith(SEEN_PREFIX) }.forEach { editor.remove(it) }
        editor.apply()
    }

    private companion object {
        const val KEY_ALLOWED = "allowed_packages"
        const val SEEN_PREFIX = "seen:"
    }
}
