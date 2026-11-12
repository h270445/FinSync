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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.FileProvider
import java.io.File
import java.time.LocalDateTime

class MainActivity : ComponentActivity() {
    private val store by lazy { CaptureStore(this) }
    private val forwarder by lazy { Forwarder(this) }
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

            ForwardingSection(tick)

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

    /** M2: where to send, the member's API token, and what happened to the last notifications. */
    @Composable
    private fun ForwardingSection(tick: Int) {
        var url by remember { mutableStateOf(forwarder.serverUrl) }
        var token by remember { mutableStateOf(forwarder.token) }
        Text("Forwarding to FinSync (OTP Bank only)", style = MaterialTheme.typography.titleSmall)
        OutlinedTextField(url, { url = it }, label = { Text("Server, e.g. http://10.0.2.2:8080") }, singleLine = true)
        OutlinedTextField(
            token,
            { token = it },
            label = { Text("API token (fs_...)") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {
                forwarder.serverUrl = url
                forwarder.token = token
                Forwarder.schedule(this@MainActivity)
                refresh++
            }) { Text("Save") }
            Button(onClick = { Forwarder.schedule(this@MainActivity); refresh++ }) { Text("Send now") }
        }
        // Read again on every refresh (onResume, Refresh, Save, Send now): Compose skips a section
        // whose inputs did not change, so the status must depend on tick.
        val status = remember(tick) {
            "Waiting: ${forwarder.pending()}, sent: ${forwarder.sentCount}, refused by server: ${forwarder.refusedCount}"
        }
        val last = remember(tick) { forwarder.lastResult }
        val dropped = remember(tick) { forwarder.droppedCounts() }
        Text(status)
        Text("Last: $last")
        if (dropped.isNotEmpty()) Text("Dropped on the phone: " + dropped.entries.joinToString { "${it.key} ${it.value}" })
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

    /**
     * Posts a made-up notification in the OTP Bank card-purchase shape, so listening and (in debug
     * builds) forwarding can be checked without a real purchase.
     */
    private fun postTestNotification() {
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 0)
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "Spike test", NotificationManager.IMPORTANCE_DEFAULT))
        // A different amount each minute (100 to 1 539 Ft), so presses in different minutes are different purchases.
        val now = LocalDateTime.now()
        val amount = 100 + now.hour * 60 + now.minute
        val shown = if (amount >= 1000) "${amount / 1000} ${"%03d".format(amount % 1000)}" else "$amount"
        val notification = NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Teszt vásárlás")
            .setContentText("-$shown Ft értékben vásárolt a TESZT BOLT KFT üzletében.")
            .build()
        try {
            NotificationManagerCompat.from(this).notify(System.currentTimeMillis().toInt(), notification)
        } catch (_: SecurityException) {
            // Permission not granted yet; press Test again after allowing it.
        }
    }

    /**
     * Shares a snapshot of the log as a file. Putting the text itself into the intent would fail
     * with TransactionTooLargeException once the log passes the ~1 MB Binder limit.
     */
    private fun share() {
        val snapshot = store.exportSnapshot(File(cacheDir, "exports"))
        val uri = FileProvider.getUriForFile(this, "$packageName.exports", snapshot)
        val intent = Intent(Intent.ACTION_SEND)
            .setType("text/plain")
            .putExtra(Intent.EXTRA_STREAM, uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        startActivity(Intent.createChooser(intent, "Export captures"))
    }

    private companion object {
        const val CHANNEL = "spike-test"
    }
}
