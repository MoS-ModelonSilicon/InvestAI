package com.investai.app.data.api

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val dataStore: DataStore<Preferences>,
) : Interceptor {

    companion object {
        val SESSION_COOKIE_KEY = stringPreferencesKey("session_cookie")
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()

        // Read session cookie from DataStore (blocking — runs on OkHttp dispatcher)
        val cookie = runBlocking {
            dataStore.data.map { prefs ->
                prefs[SESSION_COOKIE_KEY]
            }.first()
        }

        val request = if (cookie != null) {
            original.newBuilder()
                .header("Cookie", cookie)
                .build()
        } else {
            original
        }

        return chain.proceed(request)
    }
}
