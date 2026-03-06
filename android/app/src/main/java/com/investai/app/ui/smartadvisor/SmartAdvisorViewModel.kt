package com.investai.app.ui.smartadvisor

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.AdvisorAnalysis
import com.investai.app.data.api.models.AdvisorRanking
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SmartAdvisorUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val analysis: AdvisorAnalysis? = null,
    val amount: Double = 10000.0,
    val risk: String = "balanced",
    val period: String = "1y",
)

@HiltViewModel
class SmartAdvisorViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SmartAdvisorUiState())
    val uiState: StateFlow<SmartAdvisorUiState> = _uiState.asStateFlow()

    init {
        analyze()
    }

    fun setRisk(risk: String) {
        _uiState.value = _uiState.value.copy(risk = risk)
        analyze()
    }

    fun setPeriod(period: String) {
        _uiState.value = _uiState.value.copy(period = period)
        analyze()
    }

    fun analyze() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val s = _uiState.value
            repo.runAdvisorAnalysis(amount = s.amount, risk = s.risk, period = s.period).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(isLoading = false, analysis = result)
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
                },
            )
        }
    }
}
