package com.investai.app.ui.budgets

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.Budget
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BudgetsUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val budgets: List<Budget> = emptyList(),
)

@HiltViewModel
class BudgetsViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(BudgetsUiState())
    val uiState: StateFlow<BudgetsUiState> = _uiState.asStateFlow()

    init { load() }

    fun refresh() = load()

    private fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            repo.getBudgets().fold(
                onSuccess = { _uiState.value = BudgetsUiState(isLoading = false, budgets = it) },
                onFailure = { _uiState.value = BudgetsUiState(isLoading = false, error = it.message) },
            )
        }
    }
}
