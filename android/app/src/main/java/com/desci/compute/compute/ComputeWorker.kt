package com.desci.compute.compute

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.desci.compute.data.local.AppDatabase
import com.desci.compute.data.local.ComputeHistoryEntity
import com.desci.compute.data.local.TokenStore
import com.desci.compute.data.model.HeartbeatRequest
import com.desci.compute.data.model.TaskSubmission
import com.desci.compute.data.remote.ApiService
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

/**
 * WorkManager-based compute worker for persistent, reliable task processing.
 * Survives app kills, battery optimizations, and device reboots.
 * Includes offline queueing via Room and exponential backoff.
 *
 * NOTE: This worker is the BACKUP mechanism. The primary compute loop runs
 * in ComputeService (foreground service). When ComputeService is active,
 * this worker is cancelled to prevent duplicate task processing.
 */
@HiltWorker
class ComputeWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val apiService: ApiService,
    private val tokenStore: TokenStore,
    private val database: AppDatabase,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val deviceId = tokenStore.getDeviceId() ?: return Result.failure()

        // Check device health
        val health = DeviceHealthCheck.check(applicationContext)
        if (!health.canCompute) {
            return Result.retry()  // Will retry with backoff
        }

        return try {
            // Send heartbeat
            sendHeartbeat(deviceId)

            // First, flush any offline queue
            flushOfflineQueue(deviceId)

            // Request new task
            val response = apiService.getTask(deviceId)
            if (!response.isSuccessful) {
                if (response.code() == 401) {
                    // Auth expired — don't retry, need re-login
                    return Result.failure()
                }
                return Result.retry()
            }

            val task = response.body() ?: return Result.success()  // No work available

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

            // Try to submit result
            val submission = TaskSubmission(
                taskId = task.id,
                deviceId = deviceId,
                resultJson = resultJson
            )

            val submitResponse = apiService.submitResult(submission)
            if (submitResponse.isSuccessful) {
                // ✅ Submission accepted — mark as completed
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
            } else if (submitResponse.code() == 409) {
                // 409 Conflict = task already completed or duplicate result.
                // Mark as completed locally to prevent infinite retry loop.
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

            Result.success()
        } catch (e: Exception) {
            // Network error — queue for retry
            Result.retry()
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
                val response = apiService.submitResult(submission)
                if (response.isSuccessful) {
                    // ✅ Accepted — mark completed
                    database.computeHistoryDao().insert(
                        entry.copy(status = "completed", completedAt = System.currentTimeMillis())
                    )
                } else if (response.code() in listOf(409, 404)) {
                    // 409 = already completed/duplicate, 404 = task gone.
                    // Either way, stop retrying — mark as completed locally.
                    database.computeHistoryDao().insert(
                        entry.copy(status = "completed", completedAt = System.currentTimeMillis())
                    )
                }
                // For other errors (500, etc.), leave as pending_submit for next cycle
            }
        } catch (_: Exception) { /* will retry next cycle */ }
    }

    companion object {
        const val WORK_NAME = "desci_compute_loop"

        fun enqueuePeriodicWork(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()

            val request = PeriodicWorkRequestBuilder<ComputeWorker>(
                15, TimeUnit.MINUTES  // Minimum interval for WorkManager
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS,
                )
                .build()

            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    request,
                )
        }

        fun cancelWork(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
