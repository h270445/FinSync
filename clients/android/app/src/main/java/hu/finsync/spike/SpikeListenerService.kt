package hu.finsync.spike

import android.app.Notification
import android.content.pm.ApplicationInfo
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
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
    }

    override fun onListenerDisconnected() {
        store.append(JSONObject().put("type", "listener_disconnected"))
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (isWatched(sbn.packageName)) {
            store.append(toRecord("posted", sbn))
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        if (isWatched(sbn.packageName)) {
            store.append(JSONObject().put("type", "removed").put("key", sbn.key))
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

    private fun toRecord(type: String, sbn: StatusBarNotification): JSONObject {
        val notification = sbn.notification
        val extras = notification.extras
        return JSONObject()
            .put("type", type)
            .put("package", sbn.packageName)
            .put("simulated", !BankApps.isBank(sbn.packageName))
            .put("key", sbn.key)
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
    }
}
