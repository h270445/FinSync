package hu.finsync.spike

import android.app.Notification
import android.content.pm.ApplicationInfo
import android.os.Bundle
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONArray
import org.json.JSONObject

/**
 * Logs notifications of the bank apps in [BankApps] so the spike can answer:
 * which fields carry the purchase text, how the printed time relates to `postTime`,
 * whether one purchase produces several posts (updates, group summaries), and
 * whether the listener survives restarts and battery optimisation.
 */
class SpikeListenerService : NotificationListenerService() {
    private val store by lazy { CaptureStore(this) }

    override fun onListenerConnected() {
        store.append(JSONObject().put("type", "listener_connected"))
        // Notifications posted while the listener was down (force-stop, reboot, battery saving)
        // are not replayed by Android; those still in the shade are caught here.
        activeNotifications.orEmpty()
            .filter { isWatched(it.packageName) }
            .forEach { store.append(toRecord("active_on_connect", it)) }
    }

    override fun onListenerDisconnected() {
        store.append(JSONObject().put("type", "listener_disconnected"))
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (isWatched(sbn.packageName)) {
            store.append(toRecord("posted", sbn))
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification, rankingMap: RankingMap, reason: Int) {
        if (isWatched(sbn.packageName)) {
            // Only a hash of the key: some apps (Revolut) put the whole notification text into it.
            store.append(
                JSONObject()
                    .put("type", "removed")
                    .put("package", sbn.packageName)
                    .put("key_hash", TransactionFilter.hash(sbn.key))
                    .put("reason", reason)
                    .put("reason_name", REMOVAL_REASONS[reason] ?: "other")
            )
        }
    }

    private val isDebugBuild by lazy { applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0 }

    /**
     * Bank apps, this app's own test notifications and, in debug builds only, notifications
     * posted with adb (simulated bank text). Anything else is ignored without being read.
     */
    private fun isWatched(packageName: String): Boolean =
        BankApps.isBank(packageName) ||
            packageName == this.packageName ||
            (isDebugBuild && packageName == BankApps.ADB_SHELL)

    /**
     * A transaction candidate is recorded in full; anything else (marketing, news) only as a
     * masked shape with its channel, so the filter can be checked without keeping the content.
     */
    private fun toRecord(type: String, sbn: StatusBarNotification): JSONObject {
        val texts = texts(sbn.notification.extras)
        return if (TransactionFilter.looksLikeTransaction(texts)) {
            fullRecord(type, sbn).put("kind", "transaction_candidate")
        } else {
            maskedRecord(type, sbn, texts)
        }
    }

    private fun maskedRecord(type: String, sbn: StatusBarNotification, texts: List<String>): JSONObject {
        val notification = sbn.notification
        return JSONObject()
            .put("type", type)
            .put("kind", "other")
            .put("package", sbn.packageName)
            .put("key_hash", TransactionFilter.hash(sbn.key))
            .put("post_time_ms", sbn.postTime)
            .put("channel", notification.channelId ?: JSONObject.NULL)
            .put("category", notification.category ?: JSONObject.NULL)
            .put("group_summary", notification.flags and Notification.FLAG_GROUP_SUMMARY != 0)
            .put("extras_keys", JSONArray(notification.extras.keySet().sorted()))
            .put("masked_texts", JSONArray(texts.map { TransactionFilter.mask(it) }))
    }

    /** Title, texts, InboxStyle lines and MessagingStyle messages, in that order. */
    @Suppress("DEPRECATION")
    private fun texts(extras: Bundle): List<String> {
        val result = mutableListOf<String>()
        for (key in listOf(Notification.EXTRA_TITLE, Notification.EXTRA_TEXT, Notification.EXTRA_BIG_TEXT, Notification.EXTRA_SUB_TEXT)) {
            extras.getCharSequence(key)?.toString()?.let { result += it }
        }
        extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.forEach { result += it.toString() }
        extras.getParcelableArray(Notification.EXTRA_MESSAGES)?.forEach { message ->
            (message as? Bundle)?.getCharSequence("text")?.let { result += it.toString() }
        }
        return result
    }

    private fun fullRecord(type: String, sbn: StatusBarNotification): JSONObject {
        val notification = sbn.notification
        val extras = notification.extras
        return JSONObject()
            .put("type", type)
            .put("package", sbn.packageName)
            .put("simulated", !BankApps.isBank(sbn.packageName))
            .put("key", sbn.key)
            .put("key_hash", TransactionFilter.hash(sbn.key))
            .put("id", sbn.id)
            .put("tag", sbn.tag ?: JSONObject.NULL)
            .put("post_time_ms", sbn.postTime)
            .put("when_ms", notification.`when`)
            .put("channel", notification.channelId ?: JSONObject.NULL)
            .put("category", notification.category ?: JSONObject.NULL)
            .put("group_summary", notification.flags and Notification.FLAG_GROUP_SUMMARY != 0)
            .put("ongoing", sbn.isOngoing)
            .put("title", extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: JSONObject.NULL)
            .put("text", extras.getCharSequence(Notification.EXTRA_TEXT)?.toString() ?: JSONObject.NULL)
            .put("big_text", extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString() ?: JSONObject.NULL)
            .put("sub_text", extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString() ?: JSONObject.NULL)
            .put("ticker", notification.tickerText?.toString() ?: JSONObject.NULL)
            .put("group_key", sbn.groupKey ?: JSONObject.NULL)
            .put("group", notification.group ?: JSONObject.NULL)
            .put("sort_key", notification.sortKey ?: JSONObject.NULL)
            .put("extras", textExtras(extras))
    }

    /**
     * Every extra with a text value, under its own key, so a bank that uses InboxStyle
     * (`android.textLines`), MessagingStyle (`android.messages`), summary or info text is not
     * lost. Non-text extras (icons, pending intents) are recorded by type name only.
     */
    @Suppress("DEPRECATION")
    private fun textExtras(extras: Bundle): JSONObject {
        val result = JSONObject()
        for (key in extras.keySet()) {
            result.put(key, describe(extras.get(key)))
        }
        return result
    }

    @Suppress("DEPRECATION")
    private fun describe(value: Any?): Any = when (value) {
        null -> JSONObject.NULL
        is CharSequence -> value.toString()
        is Boolean, is Int, is Long -> value
        is Array<*> -> JSONArray(value.map { describe(it) })
        is Bundle -> JSONObject().also { json ->
            // MessagingStyle messages arrive as bundles with "text", "sender" and "time".
            for (key in value.keySet()) json.put(key, describe(value.get(key)))
        }
        else -> "<${value.javaClass.simpleName}>"
    }

    private companion object {
        val REMOVAL_REASONS = mapOf(
            NotificationListenerService.REASON_CLICK to "click",
            NotificationListenerService.REASON_CANCEL to "user_dismissed",
            NotificationListenerService.REASON_CANCEL_ALL to "user_dismissed_all",
            NotificationListenerService.REASON_APP_CANCEL to "app_cancelled",
            NotificationListenerService.REASON_APP_CANCEL_ALL to "app_cancelled_all",
            NotificationListenerService.REASON_GROUP_SUMMARY_CANCELED to "group_summary_cancelled",
            NotificationListenerService.REASON_PACKAGE_BANNED to "package_blocked",
            NotificationListenerService.REASON_CHANNEL_BANNED to "channel_blocked",
            NotificationListenerService.REASON_SNOOZED to "snoozed",
            NotificationListenerService.REASON_TIMEOUT to "timeout",
            NotificationListenerService.REASON_LISTENER_CANCEL to "listener_cancelled",
        )
    }
}
