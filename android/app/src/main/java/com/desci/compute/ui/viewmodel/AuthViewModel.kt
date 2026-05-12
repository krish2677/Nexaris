package com.desci.compute.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.desci.compute.data.local.TokenStore
import com.desci.compute.data.model.LoginRequest
import com.desci.compute.data.model.RegisterRequest
import com.desci.compute.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthState(
    val isLoading: Boolean = false,
    val isLoggedIn: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val apiService: ApiService,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _state = MutableStateFlow(AuthState())
    val state: StateFlow<AuthState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoggedIn = tokenStore.isLoggedIn())
        }
    }

    fun register(email: String, password: String, walletAddress: String? = null) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val regResponse = apiService.register(
                    RegisterRequest(email = email, password = password, walletAddress = walletAddress)
                )
                if (!regResponse.isSuccessful) {
                    _state.value = _state.value.copy(isLoading = false, error = "Registration failed")
                    return@launch
                }
                // Auto-login after registration
                login(email, password)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val response = apiService.login(LoginRequest(email = email, password = password))
                val token = response.body()
                if (token != null) {
                    tokenStore.saveToken(token.accessToken, token.userId)
                    tokenStore.saveEmail(email)
                    _state.value = _state.value.copy(isLoading = false, isLoggedIn = true)
                } else {
                    _state.value = _state.value.copy(isLoading = false, error = "Invalid credentials")
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            tokenStore.clear()
            _state.value = AuthState(isLoggedIn = false)
        }
    }
}
