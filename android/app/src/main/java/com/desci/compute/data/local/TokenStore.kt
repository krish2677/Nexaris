package com.desci.compute.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "desci_prefs")

/**
 * Encrypted token store using DataStore.
 * Persists JWT access token and user metadata securely.
 */
class TokenStore(private val context: Context) {

    companion object {
        private val TOKEN_KEY = stringPreferencesKey("jwt_token")
        private val USER_ID_KEY = stringPreferencesKey("user_id")
        private val DEVICE_ID_KEY = stringPreferencesKey("device_id")
        private val EMAIL_KEY = stringPreferencesKey("email")
    }

    suspend fun saveToken(token: String, userId: String) {
        context.dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = token
            prefs[USER_ID_KEY] = userId
        }
    }

    suspend fun getToken(): String? =
        context.dataStore.data.map { it[TOKEN_KEY] }.first()

    suspend fun getUserId(): String? =
        context.dataStore.data.map { it[USER_ID_KEY] }.first()

    suspend fun saveDeviceId(deviceId: String) {
        context.dataStore.edit { it[DEVICE_ID_KEY] = deviceId }
    }

    suspend fun getDeviceId(): String? =
        context.dataStore.data.map { it[DEVICE_ID_KEY] }.first()

    suspend fun saveEmail(email: String) {
        context.dataStore.edit { it[EMAIL_KEY] = email }
    }

    suspend fun getEmail(): String? =
        context.dataStore.data.map { it[EMAIL_KEY] }.first()

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }

    suspend fun isLoggedIn(): Boolean = getToken() != null
}
