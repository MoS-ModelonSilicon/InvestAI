package com.investai.app.data.api.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Generic ──────────────────────────────────────────────

@Serializable
data class OkResponse(val ok: Boolean = true)

@Serializable
data class LoginRequest(val key: String)

@Serializable
data class LoginResponse(val ok: Boolean = false, val detail: String? = null)

// ── Dashboard ────────────────────────────────────────────

@Serializable
data class DashboardResponse(
    @SerialName("total_income") val totalIncome: Double = 0.0,
    @SerialName("total_expenses") val totalExpenses: Double = 0.0,
    @SerialName("net_balance") val netBalance: Double = 0.0,
    @SerialName("category_breakdown") val categoryBreakdown: List<CategoryBreakdown> = emptyList(),
    @SerialName("monthly_trend") val monthlyTrend: List<MonthlyTrend> = emptyList(),
    @SerialName("budget_status") val budgetStatus: List<BudgetStatusItem> = emptyList(),
)

@Serializable
data class CategoryBreakdown(
    val name: String = "",
    val total: Double = 0.0,
    val color: String = "",
)

@Serializable
data class MonthlyTrend(
    val month: String = "",
    val income: Double = 0.0,
    val expenses: Double = 0.0,
)

@Serializable
data class BudgetStatusItem(
    val category: String = "",
    val limit: Double = 0.0,
    val spent: Double = 0.0,
    val percent: Double = 0.0,
)

// ── Market ───────────────────────────────────────────────

@Serializable
data class MarketHomeResponse(
    val ticker: List<TickerItem> = emptyList(),
    val featured: List<FeaturedStock> = emptyList(),
)

@Serializable
data class TickerItem(
    val symbol: String = "",
    val price: Double = 0.0,
    val change: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
)

@Serializable
data class FeaturedStock(
    val symbol: String = "",
    val name: String = "",
    val price: Double = 0.0,
    val change: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
    @SerialName("market_cap") val marketCap: Double? = null,
    val sector: String? = null,
)

// ── Portfolio ────────────────────────────────────────────

@Serializable
data class PortfolioSummary(
    @SerialName("total_invested") val totalInvested: Double = 0.0,
    @SerialName("current_value") val currentValue: Double = 0.0,
    @SerialName("total_gain_loss") val totalGainLoss: Double = 0.0,
    @SerialName("total_gain_loss_pct") val totalGainLossPct: Double = 0.0,
    val holdings: List<HoldingSummary> = emptyList(),
    @SerialName("sector_allocation") val sectorAllocation: List<SectorAllocation> = emptyList(),
    @SerialName("best_performer") val bestPerformer: HoldingSummary? = null,
    @SerialName("worst_performer") val worstPerformer: HoldingSummary? = null,
)

@Serializable
data class HoldingSummary(
    val id: Int = 0,
    val symbol: String = "",
    val name: String = "",
    val quantity: Double = 0.0,
    @SerialName("buy_price") val buyPrice: Double = 0.0,
    @SerialName("current_price") val currentPrice: Double = 0.0,
    @SerialName("gain_loss") val gainLoss: Double = 0.0,
    @SerialName("gain_loss_pct") val gainLossPct: Double = 0.0,
    @SerialName("market_value") val marketValue: Double = 0.0,
    val weight: Double = 0.0,
)

@Serializable
data class SectorAllocation(
    val sector: String = "",
    val weight: Double = 0.0,
    val count: Int = 0,
)

@Serializable
data class PortfolioPerformance(
    val dates: List<String> = emptyList(),
    val portfolio: List<Double> = emptyList(),
    val benchmark: List<Double> = emptyList(),
)

@Serializable
data class Holding(
    val id: Int = 0,
    val symbol: String = "",
    val name: String? = null,
    val quantity: Double = 0.0,
    @SerialName("buy_price") val buyPrice: Double = 0.0,
    @SerialName("buy_date") val buyDate: String = "",
    val notes: String? = null,
)

@Serializable
data class HoldingCreate(
    val symbol: String,
    val name: String? = null,
    val quantity: Double,
    @SerialName("buy_price") val buyPrice: Double,
    @SerialName("buy_date") val buyDate: String,
    val notes: String? = null,
)

// ── Watchlist ────────────────────────────────────────────

@Serializable
data class WatchlistItem(
    val id: Int = 0,
    val symbol: String = "",
    val name: String? = null,
)

@Serializable
data class WatchlistItemLive(
    val id: Int = 0,
    val symbol: String = "",
    val name: String? = null,
    val price: Double? = null,
    val change: Double? = null,
    @SerialName("change_pct") val changePct: Double? = null,
    @SerialName("market_cap") val marketCap: Double? = null,
    val pe: Double? = null,
    val beta: Double? = null,
    val sector: String? = null,
)

// ── Stock Detail ─────────────────────────────────────────

@Serializable
data class StockDetail(
    val symbol: String = "",
    val name: String = "",
    val price: Double = 0.0,
    val change: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
    @SerialName("market_cap") val marketCap: Double? = null,
    val pe: Double? = null,
    val beta: Double? = null,
    @SerialName("dividend_yield") val dividendYield: Double? = null,
    val sector: String? = null,
    val industry: String? = null,
    val signal: String? = null,
    @SerialName("signal_reason") val signalReason: String? = null,
    @SerialName("risk_analysis") val riskAnalysis: String? = null,
    @SerialName("analyst_targets") val analystTargets: AnalystTargets? = null,
    @SerialName("week_52_high") val week52High: Double? = null,
    @SerialName("week_52_low") val week52Low: Double? = null,
    val volume: Long? = null,
    @SerialName("avg_volume") val avgVolume: Long? = null,
    val description: String? = null,
)

@Serializable
data class AnalystTargets(
    val low: Double? = null,
    val mean: Double? = null,
    val high: Double? = null,
    val recommendation: String? = null,
)

@Serializable
data class StockHistory(
    val dates: List<String> = emptyList(),
    val prices: List<Double> = emptyList(),
    val volumes: List<Long> = emptyList(),
)

// ── News ─────────────────────────────────────────────────

@Serializable
data class NewsItem(
    val title: String = "",
    val url: String = "",
    val source: String = "",
    @SerialName("published") val published: String = "",
    val image: String? = null,
    val summary: String? = null,
    val symbols: List<String> = emptyList(),
)

// ── Screener ─────────────────────────────────────────────

@Serializable
data class ScreenerResponse(
    val stocks: List<ScreenerStock> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @SerialName("per_page") val perPage: Int = 20,
    val pages: Int = 1,
)

@Serializable
data class ScreenerStock(
    val symbol: String = "",
    val name: String = "",
    val price: Double = 0.0,
    val change: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
    @SerialName("market_cap") val marketCap: Double? = null,
    val pe: Double? = null,
    @SerialName("dividend_yield") val dividendYield: Double? = null,
    val beta: Double? = null,
    val sector: String? = null,
    val region: String? = null,
    @SerialName("asset_type") val assetType: String? = null,
    @SerialName("in_watchlist") val inWatchlist: Boolean = false,
)

@Serializable
data class ScreenerSectors(
    val sectors: List<String> = emptyList(),
    val regions: List<String> = emptyList(),
)

// ── Value Scanner ────────────────────────────────────────

@Serializable
data class ValueScannerResponse(
    val candidates: List<ValueStock> = emptyList(),
    val rejected: List<ValueStock> = emptyList(),
    val stats: ValueStats? = null,
    val total: Int = 0,
    val page: Int = 1,
    val pages: Int = 1,
)

@Serializable
data class ValueStock(
    val symbol: String = "",
    val name: String = "",
    val price: Double = 0.0,
    val sector: String? = null,
    val signal: String = "",
    val score: Double = 0.0,
    @SerialName("margin_of_safety") val marginOfSafety: Double? = null,
    val pe: Double? = null,
    val roe: Double? = null,
    @SerialName("debt_to_equity") val debtToEquity: Double? = null,
    @SerialName("fcf_yield") val fcfYield: Double? = null,
)

@Serializable
data class ValueStats(
    @SerialName("total_scanned") val totalScanned: Int = 0,
    @SerialName("total_passed") val totalPassed: Int = 0,
    @SerialName("avg_score") val avgScore: Double = 0.0,
)

// ── Alerts ───────────────────────────────────────────────

@Serializable
data class Alert(
    val id: Int = 0,
    val symbol: String = "",
    val name: String? = null,
    val condition: String = "",
    @SerialName("target_price") val targetPrice: Double = 0.0,
    @SerialName("current_price") val currentPrice: Double? = null,
    val triggered: Boolean = false,
    val active: Boolean = true,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class AlertCreate(
    val symbol: String,
    val name: String? = null,
    val condition: String,
    @SerialName("target_price") val targetPrice: Double,
)

// ── Recommendations ──────────────────────────────────────

@Serializable
data class RecommendationsResponse(
    @SerialName("profile_label") val profileLabel: String = "",
    @SerialName("risk_score") val riskScore: Int = 0,
    val allocation: AllocationResponse? = null,
    val recommendations: List<Recommendation> = emptyList(),
)

@Serializable
data class Recommendation(
    val symbol: String = "",
    val name: String = "",
    @SerialName("match_score") val matchScore: Double = 0.0,
    @SerialName("risk_level") val riskLevel: String = "",
    val reason: String = "",
    val price: Double? = null,
    val pe: Double? = null,
    @SerialName("dividend_yield") val dividendYield: Double? = null,
    val sector: String? = null,
)

// ── AutoPilot ────────────────────────────────────────────

@Serializable
data class AutopilotProfile(
    val id: String = "",
    val name: String = "",
    val description: String = "",
    @SerialName("risk_level") val riskLevel: String = "",
    val icon: String = "",
)

@Serializable
data class AutopilotSimulation(
    val profile: String = "",
    @SerialName("initial_amount") val initialAmount: Double = 0.0,
    @SerialName("final_value") val finalValue: Double = 0.0,
    @SerialName("total_return") val totalReturn: Double = 0.0,
    @SerialName("total_return_pct") val totalReturnPct: Double = 0.0,
    @SerialName("benchmark_return_pct") val benchmarkReturnPct: Double = 0.0,
    @SerialName("max_drawdown") val maxDrawdown: Double = 0.0,
    @SerialName("sharpe_ratio") val sharpeRatio: Double? = null,
    val holdings: List<AutopilotHolding> = emptyList(),
    val history: AutopilotHistory? = null,
    val sleeves: List<AutopilotSleeve> = emptyList(),
)

@Serializable
data class AutopilotHolding(
    val symbol: String = "",
    val sleeve: String = "",
    val shares: Double = 0.0,
    @SerialName("buy_price") val buyPrice: Double = 0.0,
    @SerialName("current_price") val currentPrice: Double = 0.0,
    @SerialName("gain_loss") val gainLoss: Double = 0.0,
    @SerialName("gain_loss_pct") val gainLossPct: Double = 0.0,
)

@Serializable
data class AutopilotHistory(
    val dates: List<String> = emptyList(),
    val portfolio: List<Double> = emptyList(),
    val benchmark: List<Double> = emptyList(),
)

@Serializable
data class AutopilotSleeve(
    val name: String = "",
    val weight: Double = 0.0,
    val symbols: List<String> = emptyList(),
)

// ── Advisor ──────────────────────────────────────────────

@Serializable
data class AdvisorAnalysis(
    val rankings: List<AdvisorRanking> = emptyList(),
    val portfolio: AdvisorPortfolio? = null,
    @SerialName("report_card") val reportCard: AdvisorReport? = null,
)

@Serializable
data class AdvisorRanking(
    val rank: Int = 0,
    val symbol: String = "",
    val name: String = "",
    val score: Double = 0.0,
    val signal: String = "",
    val price: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
)

@Serializable
data class AdvisorPortfolio(
    val holdings: List<AdvisorHolding> = emptyList(),
    @SerialName("total_return_pct") val totalReturnPct: Double = 0.0,
)

@Serializable
data class AdvisorHolding(
    val symbol: String = "",
    val weight: Double = 0.0,
    val shares: Double = 0.0,
    val signal: String = "",
)

@Serializable
data class AdvisorReport(
    @SerialName("market_mood") val marketMood: String = "",
    @SerialName("total_scanned") val totalScanned: Int = 0,
    val summary: String = "",
)

@Serializable
data class StockAnalysis(
    val symbol: String = "",
    val signal: String = "",
    val score: Double = 0.0,
    val indicators: Map<String, Double> = emptyMap(),
)

// ── Trading Advisor ──────────────────────────────────────

@Serializable
data class TradingDashboard(
    @SerialName("market_mood") val marketMood: String = "",
    val packages: List<TradingPackage> = emptyList(),
    val picks: List<TradingPick> = emptyList(),
)

@Serializable
data class TradingPackage(
    val name: String = "",
    val description: String = "",
    val picks: List<TradingPick> = emptyList(),
)

@Serializable
data class TradingPick(
    val symbol: String = "",
    val score: Double = 0.0,
    val signal: String = "",
    val rsi: Double? = null,
    val macd: String? = null,
    val entry: Double? = null,
    val target: Double? = null,
    val stop: Double? = null,
    @SerialName("risk_reward") val riskReward: Double? = null,
)

// ── Transactions ─────────────────────────────────────────

@Serializable
data class Transaction(
    val id: Int = 0,
    val amount: Double = 0.0,
    val type: String = "",
    val description: String? = null,
    val date: String = "",
    @SerialName("category_id") val categoryId: Int = 0,
    @SerialName("category_name") val categoryName: String? = null,
    @SerialName("category_color") val categoryColor: String? = null,
)

@Serializable
data class TransactionCreate(
    val amount: Double,
    val type: String,
    val description: String? = null,
    val date: String,
    @SerialName("category_id") val categoryId: Int,
)

// ── Budgets ──────────────────────────────────────────────

@Serializable
data class Budget(
    val id: Int = 0,
    @SerialName("category_id") val categoryId: Int = 0,
    @SerialName("category_name") val categoryName: String = "",
    @SerialName("monthly_limit") val monthlyLimit: Double = 0.0,
    val spent: Double = 0.0,
    val percent: Double = 0.0,
)

@Serializable
data class BudgetCreate(
    @SerialName("category_id") val categoryId: Int,
    @SerialName("monthly_limit") val monthlyLimit: Double,
)

// ── Categories ───────────────────────────────────────────

@Serializable
data class Category(
    val id: Int = 0,
    val name: String = "",
    val color: String? = null,
    val type: String = "expense",
)

// ── Risk Profile ─────────────────────────────────────────

@Serializable
data class ProfileAnswers(
    val goal: String,
    val timeline: String,
    @SerialName("investment_style") val investmentStyle: String,
    @SerialName("initial_investment") val initialInvestment: String,
    @SerialName("monthly_investment") val monthlyInvestment: String,
    val experience: String,
    @SerialName("risk_reaction") val riskReaction: String,
    @SerialName("income_stability") val incomeStability: String,
)

@Serializable
data class ProfileResponse(
    @SerialName("risk_score") val riskScore: Int = 0,
    @SerialName("profile_label") val profileLabel: String = "",
    val goal: String = "",
    val timeline: String = "",
)

@Serializable
data class AllocationResponse(
    val stocks: Double = 0.0,
    val bonds: Double = 0.0,
    val cash: Double = 0.0,
)

// ── Education ────────────────────────────────────────────

@Serializable
data class EducationResponse(
    val categories: List<EducationCategory> = emptyList(),
    val articles: List<EducationArticle> = emptyList(),
)

@Serializable
data class EducationCategory(
    val id: String = "",
    val name: String = "",
    val icon: String = "",
)

@Serializable
data class EducationArticle(
    val id: String = "",
    val title: String = "",
    val category: String = "",
    val content: String = "",
    val difficulty: String = "",
)

// ── Calendar ─────────────────────────────────────────────

@Serializable
data class EarningsEvent(
    val symbol: String = "",
    val name: String = "",
    val date: String = "",
    @SerialName("estimate_eps") val estimateEps: Double? = null,
)

@Serializable
data class EconomicEvent(
    val event: String = "",
    val date: String = "",
    val country: String = "",
    val impact: String = "",
)

// ── Comparison ───────────────────────────────────────────

@Serializable
data class ComparisonResponse(
    val stocks: List<ComparisonStock> = emptyList(),
    val histories: Map<String, List<Double>> = emptyMap(),
)

@Serializable
data class ComparisonStock(
    val symbol: String = "",
    val name: String = "",
    val price: Double = 0.0,
    @SerialName("change_pct") val changePct: Double = 0.0,
    @SerialName("market_cap") val marketCap: Double? = null,
    val pe: Double? = null,
    @SerialName("dividend_yield") val dividendYield: Double? = null,
    val beta: Double? = null,
    val sector: String? = null,
)

// ── Israeli Funds ────────────────────────────────────────

@Serializable
data class ILFundsResponse(
    val funds: List<ILFund> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val pages: Int = 1,
)

@Serializable
data class ILFund(
    val id: String = "",
    val name: String = "",
    val manager: String = "",
    @SerialName("fund_type") val fundType: String = "",
    val fee: Double = 0.0,
    @SerialName("annual_return") val annualReturn: Double? = null,
    @SerialName("ytd_return") val ytdReturn: Double? = null,
    @SerialName("size_m") val sizeM: Double? = null,
    val kosher: Boolean = false,
)

@Serializable
data class ILFundsMeta(
    val types: List<String> = emptyList(),
    val managers: List<String> = emptyList(),
)

// ── Picks Tracker ────────────────────────────────────────

@Serializable
data class PicksResponse(
    val picks: List<Pick> = emptyList(),
    val stats: PickStats? = null,
)

@Serializable
data class Pick(
    val symbol: String = "",
    val type: String = "",
    val entry: Double = 0.0,
    val target: Double? = null,
    val stop: Double? = null,
    @SerialName("current_price") val currentPrice: Double? = null,
    val status: String = "",
    @SerialName("pnl_pct") val pnlPct: Double? = null,
    val date: String = "",
)

@Serializable
data class PickStats(
    val total: Int = 0,
    val wins: Int = 0,
    val losses: Int = 0,
    val pending: Int = 0,
    @SerialName("win_rate") val winRate: Double = 0.0,
    @SerialName("avg_gain") val avgGain: Double = 0.0,
)
