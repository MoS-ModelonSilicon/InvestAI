package com.investai.app.ui.transactions

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.Transaction
import com.investai.app.data.api.models.TransactionCreate
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class TransactionsUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val transactions: List<Transaction> = emptyList(),
    val showAddDialog: Boolean = false,
)

@HiltViewModel
class TransactionsViewModel @Inject constructor(
    private val api: InvestAIApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(TransactionsUiState())
    val uiState: StateFlow<TransactionsUiState> = _uiState.asStateFlow()

    init { load() }

    fun toggleAddDialog(show: Boolean) {
        _uiState.value = _uiState.value.copy(showAddDialog = show)
    }

    fun addTransaction(description: String, amount: Double, type: String, categoryId: Int) {
        viewModelScope.launch {
            try {
                api.createTransaction(
                    TransactionCreate(
                        description = description,
                        amount = amount,
                        type = type,
                        categoryId = categoryId,
                        date = java.time.LocalDate.now().toString(),
                    )
                )
                _uiState.value = _uiState.value.copy(showAddDialog = false)
                load()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }

    fun deleteTransaction(id: Int) {
        viewModelScope.launch {
            try {
                api.deleteTransaction(id)
                load()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }

    private fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val txns = api.getTransactions()
                _uiState.value = TransactionsUiState(isLoading = false, transactions = txns)
            } catch (e: Exception) {
                _uiState.value = TransactionsUiState(isLoading = false, error = e.message)
            }
        }
    }
}
