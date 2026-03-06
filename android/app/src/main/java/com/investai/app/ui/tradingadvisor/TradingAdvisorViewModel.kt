package com.investai.app.ui.tradingadvisor

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.TradingDashboard
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TradingAdvisorUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val dashboard: TradingDashboard? = null,
)

@HiltViewModel
class TradingAdvisorViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(TradingAdvisorUiState())
    val uiState: StateFlow<TradingAdvisorUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            repo.getTradingDashboard().fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(isLoading = false, dashboard = result)
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
                },
            )
        }
    }
}
