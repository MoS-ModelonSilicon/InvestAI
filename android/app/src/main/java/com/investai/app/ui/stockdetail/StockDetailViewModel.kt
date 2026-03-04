package com.investai.app.ui.stockdetail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.NewsItem
import com.investai.app.data.api.models.StockDetail
import com.investai.app.data.api.models.StockHistory
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class StockDetailUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val detail: StockDetail? = null,
    val history: StockHistory? = null,
    val news: List<NewsItem> = emptyList(),
    val selectedPeriod: String = "1y",
)

@HiltViewModel
class StockDetailViewModel @Inject constructor(
    private val repo: MarketRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {

    private val symbol: String = savedStateHandle["symbol"] ?: ""

    private val _uiState = MutableStateFlow(StockDetailUiState())
    val uiState: StateFlow<StockDetailUiState> = _uiState.asStateFlow()

    init {
        if (symbol.isNotBlank()) loadAll()
    }

    fun selectPeriod(period: String) {
        _uiState.value = _uiState.value.copy(selectedPeriod = period)
        viewModelScope.launch {
            repo.getStockHistory(symbol, period).onSuccess { history ->
                _uiState.value = _uiState.value.copy(history = history)
            }
        }
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                val detailDef = async { repo.getStockDetail(symbol) }
                val historyDef = async { repo.getStockHistory(symbol) }
                val newsDef = async { repo.getNewsForSymbol(symbol) }

                val detail = detailDef.await().getOrNull()
                val history = historyDef.await().getOrNull()
                val news = newsDef.await().getOrNull() ?: emptyList()

                _uiState.value = StockDetailUiState(
                    isLoading = false,
                    detail = detail,
                    history = history,
                    news = news,
                )
            } catch (e: Exception) {
                _uiState.value = StockDetailUiState(isLoading = false, error = e.message)
            }
        }
    }
}
