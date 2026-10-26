package hu.finsync.spike

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.time.ZoneId

/**
 * On-device storage for the spike: `captures.jsonl` in app-private storage, one JSON object
 * per line. Nothing leaves the phone unless the user exports it.
 */
class CaptureStore(context: Context) {
    private val captures = File(context.filesDir, "captures.jsonl")

    @Synchronized
    fun append(record: JSONObject) {
        record.put("device_time_ms", System.currentTimeMillis())
        record.put("device_zone", ZoneId.systemDefault().id)
        captures.appendText(record.toString() + "\n")
    }

    fun readAll(): List<JSONObject> =
        if (!captures.exists()) emptyList()
        else captures.readLines().filter { it.isNotBlank() }.map { JSONObject(it) }

    /** Copies the log to [dir] (the FileProvider's export folder) and returns the copy. */
    @Synchronized
    fun exportSnapshot(dir: File): File {
        dir.mkdirs()
        val snapshot = File(dir, "captures.jsonl")
        if (captures.exists()) captures.copyTo(snapshot, overwrite = true) else snapshot.writeText("")
        return snapshot
    }

    @Synchronized
    fun clear() {
        captures.delete()
    }
}
