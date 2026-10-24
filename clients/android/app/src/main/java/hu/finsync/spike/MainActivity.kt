package hu.finsync.spike

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

class MainActivity : ComponentActivity() {
    private val store by lazy { CaptureStore(this) }
    private var refresh by mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { SpikeScreen(refresh) } }
    }

    override fun onResume() {
        super.onResume()
        refresh++
    }

    @Composable
    private fun SpikeScreen(@Suppress("UNUSED_PARAMETER") tick: Int) {
        val records = remember(tick) { store.readAll() }

        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(if (hasListenerAccess()) "Listener access: granted" else "Listener access: NOT granted")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)) }) { Text("Access") }
                Button(onClick = { postTestNotification() }) { Text("Test") }
                Button(onClick = { refresh++ }) { Text("Refresh") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { share() }) { Text("Export") }
                Button(onClick = { store.clear(); refresh++ }) { Text("Clear") }
            }

            Text("Watched bank apps:")
            BankApps.packages.forEach { (pkg, name) ->
                val count = records.count { it.optString("package") == pkg && it.optString("type") == "posted" }
                Text("$name ($pkg): ${if (isInstalled(pkg)) "installed" else "not installed"}, $count captured")
            }

            Text("Captured records: ${records.size}")
            LazyColumn(Modifier.weight(1f)) {
                items(records.takeLast(20).reversed()) { record ->
                    Text(record.toString(), style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }

    private fun isInstalled(packageName: String): Boolean =
        try {
            packageManager.getPackageInfo(packageName, 0)
            true
        } catch (_: PackageManager.NameNotFoundException) {
            false
        }

    private fun hasListenerAccess(): Boolean {
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners").orEmpty()
        val me = ComponentName(this, SpikeListenerService::class.java).flattenToString()
        return flat.split(':').any { it == me }
    }

    /** Posts a notification in the supported FinSync format, so the pipeline can be checked without a real purchase. */
    private fun postTestNotification() {
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 0)
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "Spike test", NotificationManager.IMPORTANCE_DEFAULT))
        val now = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"))
        val notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Test bank")
            .setContentText("CARD PURCHASE -1234.56 HUF at Test Shop on $now")
            .build()
        try {
            NotificationManagerCompat.from(this).notify(System.currentTimeMillis().toInt(), notification)
        } catch (_: SecurityException) {
            // Permission not granted yet; press Test again after allowing it.
        }
    }

    private fun share() {
        val intent = Intent(Intent.ACTION_SEND)
            .setType("text/plain")
            .putExtra(Intent.EXTRA_TEXT, store.exportText())
        startActivity(Intent.createChooser(intent, "Export captures"))
    }

    private companion object {
        const val CHANNEL = "spike-test"
    }
}
