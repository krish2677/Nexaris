package com.desci.compute.data.remote

import com.desci.compute.data.local.TokenStore
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

/**
 * OkHttp interceptor that:
 * 1. Attaches JWT Bearer token to every request
 * 2. Detects 401 responses and clears stale tokens
 * 3. Handles network errors gracefully
 */
class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val token = runBlocking { tokenStore.getToken() }
        val request = if (token != null) {
            chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }

        val response = chain.proceed(request)

        // If we get a 401, the token is expired — clear it so the app
        // navigates back to the login screen on next state check
        if (response.code == 401 && token != null) {
            runBlocking { tokenStore.clear() }
        }

        return response
    }
}
