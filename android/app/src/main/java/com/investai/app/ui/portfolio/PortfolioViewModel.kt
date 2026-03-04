package com.investai.app.ui.portfolio

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.*
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PortfolioUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val selectedTab: Int = 0, // 0 = Holdings, 1 = Watchlist
    val summary: PortfolioSummary? = null,
    val watchlistItems: List<WatchlistItemLive> = emptyList(),
)

@HiltViewModel
class PortfolioViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PortfolioUiState())
    val uiState: StateFlow<PortfolioUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun selectTab(index: Int) {
        _uiState.value = _uiState.value.copy(selectedTab = index)
    }

    fun refresh() {
        loadAll()
    }

    private fun loadAll() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val summaryDef = async { repo.getPortfolioSummary() }
                val watchlistDef = async { repo.refreshWatchlist() }

                val summary = summaryDef.await().getOrNull()
                val watchlist = watchlistDef.await().getOrNull() ?: emptyList()

                _uiState.value = PortfolioUiState(
                    isLoading = false,
                    summary = summary,
                    watchlistItems = watchlist,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
