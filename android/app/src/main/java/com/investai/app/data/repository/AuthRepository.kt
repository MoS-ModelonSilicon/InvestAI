package com.investai.app.data.repository

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import com.investai.app.data.api.AuthInterceptor.Companion.SESSION_COOKIE_KEY
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.ForgotPasswordRequest
import com.investai.app.data.api.models.LoginRequest
import com.investai.app.data.api.models.RegisterRequest
import com.investai.app.data.api.models.ResetPasswordRequest
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

    /**
     * Returns a Pair(message, code?) — code is non-null when the server returns it directly
     * (i.e. no email service configured).
     */
    suspend fun forgotPassword(email: String): Result<Pair<String, String?>> {
        return try {
            val response = api.forgotPassword(ForgotPasswordRequest(email = email))
            if (response.isSuccessful) {
                val body = response.body()
                val msg = body?.message ?: "Reset code sent"
                val code = body?.code  // non-null when no email service configured
                Result.success(Pair(msg, code))
            } else {
                val detail = response.errorBody()?.string() ?: "Request failed"
                Result.failure(Exception(detail))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun resetPassword(email: String, code: String, newPassword: String): Result<String> {
        return try {
            val response = api.resetPassword(ResetPasswordRequest(email = email, code = code, newPassword = newPassword))
            if (response.isSuccessful) {
                val msg = response.body()?.message ?: "Password reset successfully"
                Result.success(msg)
            } else {
                val detail = response.errorBody()?.string() ?: "Reset failed"
                Result.failure(Exception(detail))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
