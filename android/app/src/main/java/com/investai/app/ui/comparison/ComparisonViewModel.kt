package com.investai.app.ui.comparison

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.ComparisonResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ComparisonUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val symbols: String = "",
    val result: ComparisonResponse? = null,
)

@HiltViewModel
class ComparisonViewModel @Inject constructor(
    private val api: InvestAIApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ComparisonUiState())
    val uiState: StateFlow<ComparisonUiState> = _uiState.asStateFlow()

    fun setSymbols(symbols: String) {
        _uiState.value = _uiState.value.copy(symbols = symbols)
    }

    fun compare() {
        val syms = _uiState.value.symbols
        if (syms.isBlank()) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val result = api.compareStocks(syms)
                _uiState.value = _uiState.value.copy(isLoading = false, result = result)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
