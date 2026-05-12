package com.desci.compute

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class DeSciApplication : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val computeChannel = NotificationChannel(
                COMPUTE_CHANNEL_ID,
                "Compute Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows when your device is contributing compute power"
            }
            val rewardChannel = NotificationChannel(
                REWARD_CHANNEL_ID,
                "Rewards",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Notifications about rewards and achievements"
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(computeChannel)
            nm.createNotificationChannel(rewardChannel)
        }
    }

    companion object {
        const val COMPUTE_CHANNEL_ID = "desci_compute"
        const val REWARD_CHANNEL_ID = "desci_rewards"
    }
}
