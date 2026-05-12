package com.desci.compute.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.desci.compute.data.model.*
import com.desci.compute.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CampaignState(
    val campaigns: List<CampaignResponse> = emptyList(),
    val selectedCampaign: CampaignDetailResponse? = null,
    val rankings: UserRankingsResponse? = null,
    val treasury: TreasuryBalanceResponse? = null,
    val isLoading: Boolean = false,
    val isJoining: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class CampaignViewModel @Inject constructor(
    private val apiService: ApiService,
) : ViewModel() {

    private val _state = MutableStateFlow(CampaignState())
    val state: StateFlow<CampaignState> = _state.asStateFlow()

    init {
        loadCampaigns()
        loadRankings()
        loadTreasury()
        startAutoRefresh()
    }

    fun loadCampaigns() {
        viewModelScope.launch {
            try {
                val response = apiService.getActiveCampaigns()
                if (response.isSuccessful) {
                    _state.value = _state.value.copy(
                        campaigns = response.body()?.campaigns ?: emptyList()
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = "Failed to load campaigns")
            }
        }
    }

    fun loadRankings() {
        viewModelScope.launch {
            try {
                val response = apiService.getUserRankings()
                if (response.isSuccessful) {
                    _state.value = _state.value.copy(rankings = response.body())
                }
            } catch (_: Exception) {}
        }
    }

    fun loadTreasury() {
        viewModelScope.launch {
            try {
                val response = apiService.getTreasuryBalance()
                if (response.isSuccessful) {
                    _state.value = _state.value.copy(treasury = response.body())
                }
            } catch (_: Exception) {}
        }
    }

    fun selectCampaign(campaignId: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val response = apiService.getCampaignDetail(campaignId)
                if (response.isSuccessful) {
                    _state.value = _state.value.copy(
                        selectedCampaign = response.body(),
                        isLoading = false,
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun clearSelection() {
        _state.value = _state.value.copy(selectedCampaign = null)
    }

    fun joinCampaign(campaignId: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isJoining = true)
            try {
                val response = apiService.joinCampaign(campaignId)
                if (response.isSuccessful) {
                    // Refresh campaign detail
                    selectCampaign(campaignId)
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = "Failed to join campaign")
            }
            _state.value = _state.value.copy(isJoining = false)
        }
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    private fun startAutoRefresh() {
        viewModelScope.launch {
            while (isActive) {
                delay(8000)
                loadCampaigns()
                _state.value.selectedCampaign?.let { selectCampaign(it.id) }
            }
        }
    }
}
