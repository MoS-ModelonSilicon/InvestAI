package com.investai.app.data.repository

import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.*
import com.investai.app.data.local.dao.WatchlistDao
import com.investai.app.data.local.dao.HoldingDao
import com.investai.app.data.local.entity.CachedWatchlistItem
import com.investai.app.data.local.entity.CachedHolding
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Central repository covering Market, Portfolio, Watchlist, and Dashboard data.
 * Orchestrates API calls + local cache via Room.
 */
@Singleton
class MarketRepository @Inject constructor(
    private val api: InvestAIApi,
    private val watchlistDao: WatchlistDao,
    private val holdingDao: HoldingDao,
) {
    // ── Market ─────────────────────────────────────────

    suspend fun getMarketHome(): Result<MarketHomeResponse> = runCatching { api.getMarketHome() }

    suspend fun getMarketTicker(): Result<List<TickerItem>> = runCatching { api.getMarketTicker() }

    // ── Dashboard ──────────────────────────────────────

    suspend fun getDashboard(): Result<DashboardResponse> = runCatching { api.getDashboard() }

    // ── Portfolio ──────────────────────────────────────

    suspend fun getPortfolioSummary(): Result<PortfolioSummary> = runCatching {
        val summary = api.getPortfolioSummary()
        // Cache holdings locally
        val cached = summary.holdings.map { h ->
            CachedHolding(
                id = h.id,
                symbol = h.symbol,
                name = h.name,
                quantity = h.quantity,
                buyPrice = h.buyPrice,
                buyDate = "",
            )
        }
        holdingDao.replaceAll(cached)
        summary
    }

    suspend fun getPortfolioPerformance(): Result<PortfolioPerformance> =
        runCatching { api.getPortfolioPerformance() }

    suspend fun addHolding(holding: HoldingCreate): Result<Holding> =
        runCatching { api.addHolding(holding) }

    suspend fun deleteHolding(id: Int): Result<OkResponse> =
        runCatching { api.deleteHolding(id) }

    // ── Watchlist ──────────────────────────────────────

    fun getCachedWatchlist(): Flow<List<CachedWatchlistItem>> = watchlistDao.getAll()

    suspend fun refreshWatchlist(): Result<List<WatchlistItemLive>> = runCatching {
        val items = api.getWatchlistLive()
        val cached = items.map { w ->
            CachedWatchlistItem(
                id = w.id,
                symbol = w.symbol,
                name = w.name,
                price = w.price,
                changePct = w.changePct,
            )
        }
        watchlistDao.replaceAll(cached)
        items
    }

    suspend fun addToWatchlist(symbol: String, name: String? = null): Result<WatchlistItem> =
        runCatching { api.addToWatchlist(symbol, name) }

    suspend fun removeFromWatchlist(id: Int): Result<OkResponse> =
        runCatching { api.removeFromWatchlist(id) }

    // ── Stock Detail ───────────────────────────────────

    suspend fun getStockDetail(symbol: String): Result<StockDetail> =
        runCatching { api.getStockDetail(symbol) }

    suspend fun getStockHistory(symbol: String, period: String = "1y"): Result<StockHistory> =
        runCatching { api.getStockHistory(symbol, period) }

    // ── News ───────────────────────────────────────────

    suspend fun getNews(): Result<List<NewsItem>> = runCatching { api.getNews() }

    suspend fun getNewsForSymbol(symbol: String): Result<List<NewsItem>> =
        runCatching { api.getNewsForSymbol(symbol) }

    // ── Alerts ─────────────────────────────────────────

    suspend fun getAlerts(): Result<List<Alert>> = runCatching { api.getAlerts() }

    suspend fun createAlert(alert: AlertCreate): Result<Alert> =
        runCatching { api.createAlert(alert) }

    suspend fun deleteAlert(id: Int): Result<OkResponse> = runCatching { api.deleteAlert(id) }

    suspend fun dismissAlert(id: Int): Result<OkResponse> = runCatching { api.dismissAlert(id) }

    // ── Screener ───────────────────────────────────────

    suspend fun getScreener(
        assetType: String? = null,
        sector: String? = null,
        region: String? = null,
        page: Int = 1,
    ): Result<ScreenerResponse> = runCatching {
        api.getScreener(assetType = assetType, sector = sector, region = region, page = page)
    }

    suspend fun getScreenerSectors(): Result<ScreenerSectors> =
        runCatching { api.getScreenerSectors() }

    // ── Budgets ────────────────────────────────────────

    suspend fun getBudgets(): Result<List<Budget>> = runCatching { api.getBudgets() }
}
