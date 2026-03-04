package com.investai.app.ui.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.Alert
import com.investai.app.data.api.models.AlertCreate
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AlertsUiState(
    val isLoading: Boolean = true,
    val alerts: List<Alert> = emptyList(),
    val error: String? = null,
)

@HiltViewModel
class AlertsViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AlertsUiState())
    val uiState: StateFlow<AlertsUiState> = _uiState.asStateFlow()

    init {
        loadAlerts()
    }

    fun loadAlerts() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            repo.getAlerts().fold(
                onSuccess = { alerts ->
                    _uiState.value = AlertsUiState(isLoading = false, alerts = alerts)
                },
                onFailure = { e ->
                    _uiState.value = AlertsUiState(isLoading = false, error = e.message)
                },
            )
        }
    }

    fun createAlert(symbol: String, condition: String, targetPrice: Double) {
        viewModelScope.launch {
            repo.createAlert(AlertCreate(symbol = symbol, condition = condition, targetPrice = targetPrice))
            loadAlerts()
        }
    }

    fun deleteAlert(id: Int) {
        viewModelScope.launch {
            repo.deleteAlert(id)
            loadAlerts()
        }
    }

    fun dismissAlert(id: Int) {
        viewModelScope.launch {
            repo.dismissAlert(id)
            loadAlerts()
        }
    }
}
