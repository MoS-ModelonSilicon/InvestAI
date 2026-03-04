package com.investai.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class LoginUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepo: AuthRepository,
) : ViewModel() {

    val isLoggedIn = authRepo.isLoggedIn

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = LoginUiState(isLoading = true)
            authRepo.login(email, password).fold(
                onSuccess = {
                    _uiState.value = LoginUiState()
                },
                onFailure = { e ->
                    _uiState.value = LoginUiState(error = e.message ?: "Login failed")
                },
            )
        }
    }

    fun register(email: String, password: String, name: String = "") {
        viewModelScope.launch {
            _uiState.value = LoginUiState(isLoading = true)
            authRepo.register(email, password, name).fold(
                onSuccess = {
                    _uiState.value = LoginUiState()
                },
                onFailure = { e ->
                    _uiState.value = LoginUiState(error = e.message ?: "Registration failed")
                },
            )
        }
    }

    fun forgotPassword(email: String, onCodeSent: (code: String?) -> Unit = {}) {
        viewModelScope.launch {
            _uiState.value = LoginUiState(isLoading = true)
            authRepo.forgotPassword(email).fold(
                onSuccess = { (msg, code) ->
                    _uiState.value = LoginUiState(successMessage = msg)
                    onCodeSent(code)
                },
                onFailure = { e ->
                    _uiState.value = LoginUiState(error = e.message ?: "Request failed")
                },
            )
        }
    }

    fun resetPassword(email: String, code: String, newPassword: String, onSuccess: () -> Unit = {}) {
        viewModelScope.launch {
            _uiState.value = LoginUiState(isLoading = true)
            authRepo.resetPassword(email, code, newPassword).fold(
                onSuccess = { msg ->
                    _uiState.value = LoginUiState(successMessage = msg)
                    onSuccess()
                },
                onFailure = { e ->
                    _uiState.value = LoginUiState(error = e.message ?: "Reset failed")
                },
            )
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null, successMessage = null)
    }

    fun logout() {
        viewModelScope.launch {
            authRepo.logout()
        }
    }
}
