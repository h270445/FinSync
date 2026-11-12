package hu.finsync.spike

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit

/**
 * Sends matched notifications to `POST /v1/notifications/ingest` with the member's API token.
 *
 * Each notification goes into an outbox file first, so nothing is lost while the phone is offline
 * or the server is down; WorkManager sends the outbox when a network is available and retries with
 * backoff. A retry is never counted twice: the server recognises the same text, title, post time
 * and reference as a re-delivery, and the phone also remembers what it has already sent, so a
 * notification read again on reconnect is not sent again.
 *
 * Answers: 201 sent (removed); 400 not a transaction for the server (removed, counted, never
 * retried); 401/403 token problem (kept, shown on the screen); anything else or no network (kept, retried).
 */
class Forwarder(context: Context) {
    private val app = context.applicationContext
    private val prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val outbox = File(app.filesDir, "outbox.jsonl")
    private val sentKeys = File(app.filesDir, "sent-keys.txt")
    // Hashes only: the key of some bank notifications contains their text (Revolut).
    private val droppedKeys = File(app.filesDir, "dropped-keys.txt")

    var serverUrl: String
        get() = prefs.getString("server_url", "").orEmpty()
        set(value) = prefs.edit().putString("server_url", value.trim().trimEnd('/')).apply()

    var token: String
        get() = prefs.getString("token", "").orEmpty()
        set(value) = prefs.edit().putString("token", value.trim()).apply()

    val lastResult: String get() = prefs.getString("last_result", "nothing sent yet").orEmpty()
    val sentCount: Int get() = prefs.getInt("sent", 0)
    val refusedCount: Int get() = prefs.getInt("refused", 0)

    fun pending(): Int = synchronized(LOCK) { readOutbox().size }

    /** Per bank and channel, how many notifications were dropped on the phone (no known pattern). */
    fun droppedCounts(): Map<String, Int> =
        prefs.all.filterKeys { it.startsWith("dropped:") }.mapKeys { it.key.removePrefix("dropped:") }
            .mapValues { (it.value as? Int) ?: 0 }

    /** Counts a dropped notification once, even when it is read again on reconnect (same key and post time). */
    fun countDropped(packageName: String, channel: String?, notificationKey: String, postTimeMs: Long) {
        val counter = "dropped:$packageName/${channel ?: "-"}"
        val seen = TransactionFilter.hash("$notificationKey|$postTimeMs")
        synchronized(LOCK) {
            val keys = if (droppedKeys.exists()) droppedKeys.readLines().filter { it.isNotBlank() } else emptyList()
            if (seen in keys) return
            droppedKeys.writeText((keys + seen).takeLast(MAX_SENT_KEYS).joinToString("\n"))
            prefs.edit().putInt(counter, prefs.getInt(counter, 0) + 1).apply()
        }
    }

    /** Queues one matched notification and asks WorkManager to send. A notification already queued or sent is ignored. */
    fun enqueue(packageName: String, postTimeMs: Long, title: String?, text: String, tag: String?) {
        val key = TransactionFilter.hash("$packageName|$postTimeMs|$text")
        val payload = JSONObject()
            .put("message", text)
            .put("title", title ?: JSONObject.NULL)
            .put("posted_at", POSTED_AT.format(Instant.ofEpochMilli(postTimeMs).atOffset(ZoneOffset.UTC)))
            .put("source_ref", OtpFormat.sourceReference(tag) ?: JSONObject.NULL)
        synchronized(LOCK) {
            if (key in readSentKeys() || readOutbox().any { it.optString("key") == key }) return
            outbox.appendText(JSONObject().put("key", key).put("payload", payload).toString() + "\n")
        }
        schedule(app)
    }

    /** Sends the outbox in order. Returns false when a retry is needed later. */
    fun flush(): Boolean {
        val url = serverUrl
        val token = token
        if (url.isBlank() || token.isBlank()) {
            record("not configured: set the server address and the token")
            return true // Nothing to retry until the settings change; saving them schedules a send.
        }
        val items = synchronized(LOCK) { readOutbox() }
        for (item in items) {
            val status = try {
                post("$url/v1/notifications/ingest", token, item.getJSONObject("payload"))
            } catch (error: IOException) {
                record("no connection (${error.javaClass.simpleName}); will retry")
                return false
            }
            when {
                status == 201 -> {
                    done(item, sent = true)
                    record("sent ($status)")
                }
                status == 400 -> {
                    done(item, sent = false)
                    record("server says not a transaction (400); dropped")
                }
                status == 401 || status == 403 -> {
                    record("token refused ($status): check the token")
                    return true // Retrying will not help until the token changes.
                }
                else -> {
                    record("server error ($status); will retry")
                    return false
                }
            }
        }
        return true
    }

    private fun post(url: String, token: String, body: JSONObject): Int {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 10_000
            connection.readTimeout = 15_000
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $token")
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            return connection.responseCode
        } finally {
            connection.disconnect()
        }
    }

    private fun done(item: JSONObject, sent: Boolean) = synchronized(LOCK) {
        val key = item.optString("key")
        val rest = readOutbox().filter { it.optString("key") != key }
        outbox.writeText(rest.joinToString("") { it.toString() + "\n" })
        val keys = (readSentKeys() + key).takeLast(MAX_SENT_KEYS)
        sentKeys.writeText(keys.joinToString("\n"))
        val counter = if (sent) "sent" else "refused"
        prefs.edit().putInt(counter, prefs.getInt(counter, 0) + 1).apply()
    }

    private fun record(result: String) {
        prefs.edit().putString("last_result", "${Instant.now().atZone(ZoneId.systemDefault()).toLocalTime().withNano(0)} $result").apply()
    }

    private fun readOutbox(): List<JSONObject> =
        if (!outbox.exists()) emptyList()
        else outbox.readLines().filter { it.isNotBlank() }.mapNotNull { runCatching { JSONObject(it) }.getOrNull() }

    private fun readSentKeys(): List<String> =
        if (!sentKeys.exists()) emptyList() else sentKeys.readLines().filter { it.isNotBlank() }

    companion object {
        private const val PREFS = "forwarder"
        private const val MAX_SENT_KEYS = 500
        private const val WORK_NAME = "finsync-send"
        private val LOCK = Any()
        private val POSTED_AT = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSxxx")

        /** Sends the outbox as soon as a network is available; a call during a send runs after it, so nothing queued meanwhile waits. */
        fun schedule(context: Context) {
            val request = OneTimeWorkRequestBuilder<SendWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(WORK_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, request)
        }
    }
}

class SendWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result = if (Forwarder(applicationContext).flush()) Result.success() else Result.retry()
}
