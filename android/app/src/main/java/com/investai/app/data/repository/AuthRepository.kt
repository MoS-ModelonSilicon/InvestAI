package com.investai.app.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import com.investai.app.data.api.AuthInterceptor.Companion.SESSION_COOKIE_KEY
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.LoginRequest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: InvestAIApi,
    private val dataStore: DataStore<Preferences>,
) {
    val isLoggedIn: Flow<Boolean> = dataStore.data.map { prefs ->
        prefs[SESSION_COOKIE_KEY] != null
    }

    suspend fun login(accessKey: String): Result<Unit> {
        return try {
            val response = api.login(LoginRequest(key = accessKey))
            if (response.isSuccessful) {
                // Extract Set-Cookie header and persist
                val cookie = response.headers()["Set-Cookie"]
                if (cookie != null) {
                    dataStore.edit { prefs ->
                        prefs[SESSION_COOKIE_KEY] = cookie.split(";").first()
                    }
                }
                Result.success(Unit)
            } else {
                Result.failure(Exception("Invalid access key"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout() {
        dataStore.edit { prefs ->
            prefs.remove(SESSION_COOKIE_KEY)
        }
    }
}
