package com.desci.compute.ui.viewmodel

import android.app.Application
import android.content.Intent
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.desci.compute.compute.ComputeService
import com.desci.compute.compute.DeviceHealthCheck
import com.desci.compute.data.local.AppDatabase
import com.desci.compute.data.local.TokenStore
import com.desci.compute.data.model.*
import com.desci.compute.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardState(
    val isComputing: Boolean = false,
    val healthStatus: DeviceHealthCheck.HealthStatus? = null,
    val stats: PlatformStats? = null,
    val leaderboard: List<LeaderboardEntry> = emptyList(),
    val jobs: List<JobResponse> = emptyList(),
    val completedTasks: Int = 0,
    val totalTasks: Int = 0,
    val userScore: Double = 0.0,
    val userEmail: String = "",
    val error: String? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val app: Application,
    private val apiService: ApiService,
    private val tokenStore: TokenStore,
    private val database: AppDatabase,
) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(DashboardState())
    val state: StateFlow<DashboardState> = _state.asStateFlow()

    init {
        loadData()
    }

    fun loadData() {
        viewModelScope.launch {
            _state.value = _state.value.copy(
                userEmail = tokenStore.getEmail() ?: "",
            )
            loadStats()
            loadLeaderboard()
            loadJobs()
            loadLocalHistory()
        }
    }

    fun startComputing() {
        viewModelScope.launch {
            val health = DeviceHealthCheck.check(app)
            _state.value = _state.value.copy(healthStatus = health)

            if (!health.canCompute) {
                _state.value = _state.value.copy(
                    error = when {
                        !health.internetAvailable -> "No internet connection"
                        !health.batteryOk && !health.isCharging -> "Battery too low (${health.batteryLevel}%)"
                        else -> "Device cannot compute right now"
                    }
                )
                return@launch
            }

            // Register device if needed
            if (tokenStore.getDeviceId() == null) {
                registerDevice()
            }

            val intent = Intent(app, ComputeService::class.java).apply {
                action = ComputeService.ACTION_START
            }
            app.startForegroundService(intent)
            _state.value = _state.value.copy(isComputing = true, error = null)
        }
    }

    fun stopComputing() {
        val intent = Intent(app, ComputeService::class.java).apply {
            action = ComputeService.ACTION_STOP
        }
        app.startService(intent)
        _state.value = _state.value.copy(isComputing = false)
    }

    private suspend fun registerDevice() {
        try {
            val cores = Runtime.getRuntime().availableProcessors()
            val ram = (Runtime.getRuntime().maxMemory() / 1024 / 1024).toInt()
            val response = apiService.registerDevice(
                DeviceRegisterRequest(
                    deviceType = "android",
                    cpuCores = cores,
                    ram = ram,
                    devicePowerFactor = cores * 0.5,
                )
            )
            response.body()?.let { device ->
                tokenStore.saveDeviceId(device.id)
            }
        } catch (e: Exception) {
            _state.value = _state.value.copy(error = "Device registration failed: ${e.message}")
        }
    }

    private suspend fun loadStats() {
        try {
            val response = apiService.getStats()
            response.body()?.let { stats ->
                _state.value = _state.value.copy(stats = stats)
            }
        } catch (_: Exception) {}
    }

    private suspend fun loadLeaderboard() {
        try {
            val response = apiService.getLeaderboard(limit = 20)
            response.body()?.let { lb ->
                _state.value = _state.value.copy(leaderboard = lb.leaderboard)
            }
        } catch (_: Exception) {}
    }

    private suspend fun loadJobs() {
        try {
            val response = apiService.getJobs()
            response.body()?.let { jobs ->
                _state.value = _state.value.copy(jobs = jobs)
            }
        } catch (_: Exception) {}
    }

    private suspend fun loadLocalHistory() {
        try {
            val completed = database.computeHistoryDao().getCompletedCount()
            val total = database.computeHistoryDao().getTotalCount()
            _state.value = _state.value.copy(completedTasks = completed, totalTasks = total)
        } catch (_: Exception) {}
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }
}
