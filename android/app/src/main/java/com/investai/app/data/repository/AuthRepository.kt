package com.investai.app.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import com.investai.app.data.api.AuthInterceptor.Companion.SESSION_COOKIE_KEY
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.LoginRequest
import com.investai.app.data.api.models.RegisterRequest
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

    suspend fun login(email: String, password: String): Result<Unit> {
        return try {
            val response = api.login(LoginRequest(email = email, password = password))
            if (response.isSuccessful) {
                val cookie = response.headers()["Set-Cookie"]
                if (cookie != null) {
                    dataStore.edit { prefs ->
                        prefs[SESSION_COOKIE_KEY] = cookie.split(";").first()
                    }
                }
                Result.success(Unit)
            } else {
                val detail = response.errorBody()?.string() ?: "Invalid email or password"
                Result.failure(Exception(detail))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun register(email: String, password: String, name: String = ""): Result<Unit> {
        return try {
            val response = api.register(RegisterRequest(email = email, password = password, name = name))
            if (response.isSuccessful) {
                val cookie = response.headers()["Set-Cookie"]
                if (cookie != null) {
                    dataStore.edit { prefs ->
                        prefs[SESSION_COOKIE_KEY] = cookie.split(";").first()
                    }
                }
                Result.success(Unit)
            } else {
                val detail = response.errorBody()?.string() ?: "Registration failed"
                Result.failure(Exception(detail))
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
