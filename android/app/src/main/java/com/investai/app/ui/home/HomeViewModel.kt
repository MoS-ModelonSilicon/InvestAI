package com.investai.app.ui.home

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

data class HomeUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,

    // Portfolio hero
    val portfolioValue: Double = 0.0,
    val portfolioChange: Double = 0.0,
    val portfolioChangePct: Double = 0.0,

    // Market ticker
    val tickerItems: List<TickerItem> = emptyList(),

    // Watchlist (top 6)
    val watchlistItems: List<WatchlistItemLive> = emptyList(),

    // Budget status
    val budgetStatus: List<BudgetStatusItem> = emptyList(),

    // News (top 5)
    val newsItems: List<NewsItem> = emptyList(),

    // Dashboard financials
    val totalIncome: Double = 0.0,
    val totalExpenses: Double = 0.0,
    val netBalance: Double = 0.0,
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun refresh() {
        _uiState.value = _uiState.value.copy(isRefreshing = true)
        loadAll()
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                // Load all data in parallel
                val portfolioDeferred = async { repo.getPortfolioSummary() }
                val marketDeferred = async { repo.getMarketHome() }
                val watchlistDeferred = async { repo.refreshWatchlist() }
                val dashboardDeferred = async { repo.getDashboard() }
                val newsDeferred = async { repo.getNews() }

                val portfolio = portfolioDeferred.await().getOrNull()
                val market = marketDeferred.await().getOrNull()
                val watchlist = watchlistDeferred.await().getOrNull()
                val dashboard = dashboardDeferred.await().getOrNull()
                val news = newsDeferred.await().getOrNull()

                _uiState.value = HomeUiState(
                    isLoading = false,
                    isRefreshing = false,
                    portfolioValue = portfolio?.currentValue ?: 0.0,
                    portfolioChange = portfolio?.totalGainLoss ?: 0.0,
                    portfolioChangePct = portfolio?.totalGainLossPct ?: 0.0,
                    tickerItems = market?.ticker ?: emptyList(),
                    watchlistItems = (watchlist ?: emptyList()).take(6),
                    budgetStatus = dashboard?.budgetStatus ?: emptyList(),
                    newsItems = (news ?: emptyList()).take(5),
                    totalIncome = dashboard?.totalIncome ?: 0.0,
                    totalExpenses = dashboard?.totalExpenses ?: 0.0,
                    netBalance = dashboard?.netBalance ?: 0.0,
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isRefreshing = false,
                    error = e.message,
                )
            }
        }
    }
}
