package com.desci.compute.compute

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager

/**
 * Checks device health conditions before starting compute.
 */
object DeviceHealthCheck {

    data class HealthStatus(
        val internetAvailable: Boolean,
        val batteryOk: Boolean,
        val batteryLevel: Int,
        val isCharging: Boolean,
        val canCompute: Boolean,
    )

    fun check(context: Context): HealthStatus {
        val internet = isInternetAvailable(context)
        val batteryInfo = getBatteryInfo(context)

        val canCompute = internet &&
                (batteryInfo.first > 20 || batteryInfo.second) // >20% or charging

        return HealthStatus(
            internetAvailable = internet,
            batteryOk = batteryInfo.first > 20,
            batteryLevel = batteryInfo.first,
            isCharging = batteryInfo.second,
            canCompute = canCompute,
        )
    }

    private fun isInternetAvailable(context: Context): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }

    private fun getBatteryInfo(context: Context): Pair<Int, Boolean> {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = intent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        val percent = if (level >= 0 && scale > 0) (level * 100 / scale) else 50

        val plugged = intent?.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1) ?: 0
        val isCharging = plugged != 0

        return Pair(percent, isCharging)
    }
}
