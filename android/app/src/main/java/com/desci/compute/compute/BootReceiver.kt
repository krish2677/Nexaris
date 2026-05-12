package com.desci.compute.compute

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.desci.compute.data.local.TokenStore
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.runBlocking
import javax.inject.Inject

/**
 * Boot receiver — resumes compute automatically after device reboot
 * if the user was previously contributing.
 */
@AndroidEntryPoint
class BootReceiver : BroadcastReceiver() {

    @Inject lateinit var tokenStore: TokenStore

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return

        val isLoggedIn = runBlocking { tokenStore.isLoggedIn() }
        if (isLoggedIn) {
            val serviceIntent = Intent(context, ComputeService::class.java).apply {
                action = ComputeService.ACTION_START
            }
            context.startForegroundService(serviceIntent)
        }
    }
}
