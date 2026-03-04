package com.investai.app.data.api

import com.investai.app.data.api.models.*
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit interface mapping ALL InvestAI backend endpoints.
 * Organized by feature area matching the FastAPI routers.
 */
interface InvestAIApi {

    // ── Auth ──────────────────────────────────────────────

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): Response<LoginResponse>

    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): Response<LoginResponse>

    // ── Dashboard ─────────────────────────────────────────

    @GET("api/dashboard")
    suspend fun getDashboard(
        @Query("date_from") dateFrom: String? = null,
        @Query("date_to") dateTo: String? = null,
    ): DashboardResponse

    // ── Market ────────────────────────────────────────────

    @GET("api/market/home")
    suspend fun getMarketHome(): MarketHomeResponse

    @GET("api/market/ticker")
    suspend fun getMarketTicker(): List<TickerItem>

    @GET("api/market/featured")
    suspend fun getMarketFeatured(): List<FeaturedStock>

    // ── Portfolio ─────────────────────────────────────────

    @GET("api/portfolio/summary")
    suspend fun getPortfolioSummary(): PortfolioSummary

    @GET("api/portfolio/performance")
    suspend fun getPortfolioPerformance(): PortfolioPerformance

    @GET("api/portfolio/holdings")
    suspend fun getHoldings(): List<Holding>

    @POST("api/portfolio/holdings")
    suspend fun addHolding(@Body holding: HoldingCreate): Holding

    @DELETE("api/portfolio/holdings/{id}")
    suspend fun deleteHolding(@Path("id") id: Int): OkResponse

    // ── Watchlist ─────────────────────────────────────────

    @GET("api/screener/watchlist/live")
    suspend fun getWatchlistLive(): List<WatchlistItemLive>

    @GET("api/screener/watchlist")
    suspend fun getWatchlist(): List<WatchlistItem>

    @POST("api/screener/watchlist")
    suspend fun addToWatchlist(
        @Query("symbol") symbol: String,
        @Query("name") name: String? = null,
    ): WatchlistItem

    @DELETE("api/screener/watchlist/{id}")
    suspend fun removeFromWatchlist(@Path("id") id: Int): OkResponse

    // ── Stock Detail ──────────────────────────────────────

    @GET("api/stock/{symbol}")
    suspend fun getStockDetail(@Path("symbol") symbol: String): StockDetail

    @GET("api/stock/{symbol}/history")
    suspend fun getStockHistory(
        @Path("symbol") symbol: String,
        @Query("period") period: String = "1y",
        @Query("interval") interval: String = "1d",
    ): StockHistory

    @GET("api/stock/{symbol}/news")
    suspend fun getStockNews(@Path("symbol") symbol: String): List<NewsItem>

    // ── Screener ──────────────────────────────────────────

    @GET("api/screener")
    suspend fun getScreener(
        @Query("asset_type") assetType: String? = null,
        @Query("sector") sector: String? = null,
        @Query("region") region: String? = null,
        @Query("market_cap_min") marketCapMin: Double? = null,
        @Query("market_cap_max") marketCapMax: Double? = null,
        @Query("pe_min") peMin: Double? = null,
        @Query("pe_max") peMax: Double? = null,
        @Query("dividend_yield_min") dividendYieldMin: Double? = null,
        @Query("beta_min") betaMin: Double? = null,
        @Query("beta_max") betaMax: Double? = null,
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): ScreenerResponse

    @GET("api/screener/sectors")
    suspend fun getScreenerSectors(): ScreenerSectors

    // ── Value Scanner ─────────────────────────────────────

    @GET("api/value-scanner")
    suspend fun getValueScanner(
        @Query("sector") sector: String? = null,
        @Query("signal") signal: String? = null,
        @Query("sort_by") sortBy: String = "score",
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): ValueScannerResponse

    // ── Recommendations ───────────────────────────────────

    @GET("api/recommendations")
    suspend fun getRecommendations(): RecommendationsResponse

    // ── AutoPilot ─────────────────────────────────────────

    @GET("api/autopilot/profiles")
    suspend fun getAutopilotProfiles(): List<AutopilotProfile>

    @GET("api/autopilot/simulate")
    suspend fun simulateAutopilot(
        @Query("profile") profile: String,
        @Query("amount") amount: Double = 10000.0,
        @Query("period") period: String = "1y",
    ): AutopilotSimulation

    // ── Smart Advisor ─────────────────────────────────────

    @GET("api/advisor/analyze")
    suspend fun runAdvisorAnalysis(
        @Query("amount") amount: Double = 10000.0,
        @Query("risk") risk: String = "balanced",
        @Query("period") period: String = "1y",
    ): AdvisorAnalysis

    @GET("api/advisor/stock/{symbol}")
    suspend fun getAdvisorStockAnalysis(@Path("symbol") symbol: String): StockAnalysis

    // ── Trading Advisor ───────────────────────────────────

    @GET("api/trading")
    suspend fun getTradingDashboard(): TradingDashboard

    // ── Alerts ────────────────────────────────────────────

    @GET("api/alerts")
    suspend fun getAlerts(): List<Alert>

    @GET("api/alerts/triggered")
    suspend fun getTriggeredAlerts(): List<Alert>

    @POST("api/alerts")
    suspend fun createAlert(@Body alert: AlertCreate): Alert

    @DELETE("api/alerts/{id}")
    suspend fun deleteAlert(@Path("id") id: Int): OkResponse

    @POST("api/alerts/{id}/dismiss")
    suspend fun dismissAlert(@Path("id") id: Int): OkResponse

    // ── News ──────────────────────────────────────────────

    @GET("api/news")
    suspend fun getNews(): List<NewsItem>

    @GET("api/news/{symbol}")
    suspend fun getNewsForSymbol(@Path("symbol") symbol: String): List<NewsItem>

    // ── Calendar ──────────────────────────────────────────

    @GET("api/calendar/earnings")
    suspend fun getEarningsCalendar(): List<EarningsEvent>

    @GET("api/calendar/economic")
    suspend fun getEconomicCalendar(): List<EconomicEvent>

    // ── Transactions ──────────────────────────────────────

    @GET("api/transactions")
    suspend fun getTransactions(
        @Query("type") type: String? = null,
        @Query("category_id") categoryId: Int? = null,
        @Query("date_from") dateFrom: String? = null,
        @Query("date_to") dateTo: String? = null,
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
    ): List<Transaction>

    @POST("api/transactions")
    suspend fun createTransaction(@Body tx: TransactionCreate): Transaction

    @DELETE("api/transactions/{id}")
    suspend fun deleteTransaction(@Path("id") id: Int): OkResponse

    // ── Budgets ───────────────────────────────────────────

    @GET("api/budgets")
    suspend fun getBudgets(): List<Budget>

    @POST("api/budgets")
    suspend fun createBudget(@Body budget: BudgetCreate): Budget

    @DELETE("api/budgets/{id}")
    suspend fun deleteBudget(@Path("id") id: Int): OkResponse

    // ── Categories ────────────────────────────────────────

    @GET("api/categories")
    suspend fun getCategories(): List<Category>

    // ── Risk Profile ──────────────────────────────────────

    @GET("api/profile")
    suspend fun getProfile(): ProfileResponse?

    @POST("api/profile")
    suspend fun submitProfile(@Body answers: ProfileAnswers): ProfileResponse

    @GET("api/profile/allocation")
    suspend fun getProfileAllocation(): AllocationResponse

    // ── Education ─────────────────────────────────────────

    @GET("api/education")
    suspend fun getEducation(): EducationResponse

    // ── Comparison ────────────────────────────────────────

    @GET("api/compare")
    suspend fun compareStocks(@Query("symbols") symbols: String): ComparisonResponse

    // ── Israeli Funds ─────────────────────────────────────

    @GET("api/il-funds")
    suspend fun getILFunds(
        @Query("fund_type") fundType: String? = null,
        @Query("manager") manager: String? = null,
        @Query("kosher_only") kosherOnly: Boolean? = null,
        @Query("sort_by") sortBy: String = "fee",
        @Query("max_fee") maxFee: Double? = null,
        @Query("min_return") minReturn: Double? = null,
        @Query("min_size") minSize: Double? = null,
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): ILFundsResponse

    @GET("api/il-funds/best")
    suspend fun getILFundsBest(
        @Query("category") category: String? = null,
        @Query("top_n") topN: Int = 5,
    ): List<ILFund>

    @GET("api/il-funds/meta")
    suspend fun getILFundsMeta(): ILFundsMeta

    // ── Picks Tracker ─────────────────────────────────────

    @GET("api/picks")
    suspend fun getPicks(@Query("type") type: String? = null): PicksResponse
}
