package com.desci.compute.compute

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.desci.compute.DeSciApplication
import com.desci.compute.data.local.AppDatabase
import com.desci.compute.data.local.ComputeHistoryEntity
import com.desci.compute.data.local.TokenStore
import com.desci.compute.data.model.HeartbeatRequest
import com.desci.compute.data.model.TaskSubmission
import com.desci.compute.data.remote.ApiService
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import javax.inject.Inject

/**
 * Foreground service that continuously fetches and executes compute tasks.
 * Also enqueues WorkManager for reliable persistence beyond service lifecycle.
 *
 * IMPORTANT: When this service is running, the WorkManager-based ComputeWorker
 * is NOT enqueued to prevent duplicate task processing.
 */
@AndroidEntryPoint
class ComputeService : Service() {

    @Inject lateinit var apiService: ApiService
    @Inject lateinit var tokenStore: TokenStore
    @Inject lateinit var database: AppDatabase

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var isRunning = false
    private var tasksCompleted = 0
    private var consecutiveErrors = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startCompute()
            ACTION_STOP -> stopCompute()
        }
        return START_STICKY
    }

    private fun startCompute() {
        if (isRunning) return
        isRunning = true
        startForeground(NOTIFICATION_ID, buildNotification("Initializing…"))

        // Cancel WorkManager backup while foreground service is running
        // to prevent BOTH from processing tasks simultaneously.
        ComputeWorker.cancelWork(this)

        scope.launch { computeLoop() }
    }

    private fun stopCompute() {
        isRunning = false
        scope.coroutineContext.cancelChildren()

        // Re-enable WorkManager as a backup now that foreground service is stopping
        ComputeWorker.enqueuePeriodicWork(this)

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private suspend fun computeLoop() {
        val deviceId = tokenStore.getDeviceId() ?: return

        while (isRunning) {
            try {
                // Check device health
                val health = DeviceHealthCheck.check(this@ComputeService)
                if (!health.canCompute) {
                    updateNotification(
                        "Paused: ${if (!health.internetAvailable) "No internet" else "Low battery (${health.batteryLevel}%)"}"
                    )
                    delay(30_000)
                    continue
                }

                // Send heartbeat
                sendHeartbeat(deviceId)

                // Flush offline queue first
                flushOfflineQueue(deviceId)

                // Request task
                val response = apiService.getTask(deviceId)

                if (!response.isSuccessful) {
                    when (response.code()) {
                        401 -> {
                            updateNotification("Session expired. Please re-login.")
                            delay(60_000)
                            continue
                        }
                        429 -> {
                            updateNotification("Rate limited. Waiting…")
                            delay(30_000)
                            continue
                        }
                        else -> {
                            consecutiveErrors++
                            val backoff = minOf(consecutiveErrors * 5_000L, 60_000L)
                            updateNotification("Server error (${response.code()}). Retrying…")
                            delay(backoff)
                            continue
                        }
                    }
                }

                val task = response.body()
                if (task == null) {
                    updateNotification("Waiting for tasks… ($tasksCompleted completed)")
                    delay(5_000)
                    continue
                }

                consecutiveErrors = 0
                updateNotification("Computing: ${task.templateType}…")

                // Log to local DB
                database.computeHistoryDao().insert(
                    ComputeHistoryEntity(
                        taskId = task.id,
                        jobId = task.jobId,
                        templateType = task.templateType,
                        status = "in_progress"
                    )
                )

                // Execute compute template
                val resultJson = ComputeTemplates.execute(
                    templateType = task.templateType,
                    paramsJson = task.parametersJson,
                    rangeStart = task.rangeStart ?: 0,
                    rangeEnd = task.rangeEnd ?: 0,
                    chunkRef = task.chunkReference
                )

                // Submit result
                val submission = TaskSubmission(
                    taskId = task.id,
                    deviceId = deviceId,
                    resultJson = resultJson
                )

                val submitResp = apiService.submitResult(submission)
                if (submitResp.isSuccessful) {
                    // ✅ Submission accepted — mark as completed, move on
                    database.computeHistoryDao().insert(
                        ComputeHistoryEntity(
                            taskId = task.id,
                            jobId = task.jobId,
                            templateType = task.templateType,
                            status = "completed",
                            resultJson = resultJson,
                            completedAt = System.currentTimeMillis()
                        )
                    )
                    tasksCompleted++
                } else if (submitResp.code() == 409) {
                    // 409 Conflict = task already completed or duplicate.
                    // Mark as completed locally to stop retrying.
                    database.computeHistoryDao().insert(
                        ComputeHistoryEntity(
                            taskId = task.id,
                            jobId = task.jobId,
                            templateType = task.templateType,
                            status = "completed",
                            resultJson = resultJson,
                            completedAt = System.currentTimeMillis()
                        )
                    )
                } else {
                    // Other error — queue for offline retry
                    database.computeHistoryDao().insert(
                        ComputeHistoryEntity(
                            taskId = task.id,
                            jobId = task.jobId,
                            templateType = task.templateType,
                            status = "pending_submit",
                            resultJson = resultJson,
                        )
                    )
                }

                updateNotification("Contributing… $tasksCompleted tasks completed")

            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                consecutiveErrors++
                val backoff = minOf(consecutiveErrors * 5_000L, 60_000L)
                updateNotification("Retrying… (${e.message?.take(30)})")
                delay(backoff)
            }
        }
    }

    private suspend fun sendHeartbeat(deviceId: String) {
        try {
            apiService.heartbeat(
                HeartbeatRequest(deviceId = deviceId, status = "computing")
            )
        } catch (_: Exception) { /* non-critical */ }
    }

    private suspend fun flushOfflineQueue(deviceId: String) {
        try {
            val pending = database.computeHistoryDao().getPendingSubmissions()
            for (entry in pending) {
                if (entry.resultJson == null) {
                    // No result data — can't submit, mark as failed
                    database.computeHistoryDao().insert(
                        entry.copy(status = "failed")
                    )
                    continue
                }
                val submission = TaskSubmission(
                    taskId = entry.taskId,
                    deviceId = deviceId,
                    resultJson = entry.resultJson
                )
                val resp = apiService.submitResult(submission)
                if (resp.isSuccessful) {
                    // ✅ Accepted — mark completed
                    database.computeHistoryDao().insert(
                        entry.copy(status = "completed", completedAt = System.currentTimeMillis())
                    )
                } else if (resp.code() in listOf(409, 404)) {
                    // 409 = already completed/duplicate, 404 = task not found.
                    // Either way, stop retrying — mark as completed.
                    database.computeHistoryDao().insert(
                        entry.copy(status = "completed", completedAt = System.currentTimeMillis())
                    )
                }
                // For other errors (500, etc.), leave as pending_submit for next retry
            }
        } catch (_: Exception) { /* will retry next loop */ }
    }

    private fun buildNotification(text: String): Notification {
        val stopIntent = Intent(this, ComputeService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPending = PendingIntent.getService(
            this, 0, stopIntent, PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, DeSciApplication.COMPUTE_CHANNEL_ID)
            .setContentTitle("DeSci Compute")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_manage)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_media_pause, "Stop", stopPending)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        nm.notify(NOTIFICATION_ID, buildNotification(text))
    }

    override fun onDestroy() {
        isRunning = false
        scope.cancel()
        // Re-enable WorkManager when service dies unexpectedly
        ComputeWorker.enqueuePeriodicWork(this)
        super.onDestroy()
    }

    companion object {
        const val ACTION_START = "com.desci.compute.START"
        const val ACTION_STOP = "com.desci.compute.STOP"
        private const val NOTIFICATION_ID = 1001
    }
}
