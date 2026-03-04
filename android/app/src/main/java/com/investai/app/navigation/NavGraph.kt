package com.investai.app.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.investai.app.ui.alerts.AlertsScreen
import com.investai.app.ui.auth.ForgotPasswordScreen
import com.investai.app.ui.auth.LoginScreen
import com.investai.app.ui.autopilot.AutoPilotScreen
import com.investai.app.ui.budgets.BudgetsScreen
import com.investai.app.ui.comparison.ComparisonScreen
import com.investai.app.ui.home.HomeScreen
import com.investai.app.ui.invest.InvestScreen
import com.investai.app.ui.more.MoreScreen
import com.investai.app.ui.news.NewsScreen
import com.investai.app.ui.portfolio.PortfolioScreen
import com.investai.app.ui.recommendations.RecommendationsScreen
import com.investai.app.ui.screener.ScreenerScreen
import com.investai.app.ui.stockdetail.StockDetailScreen
import com.investai.app.ui.transactions.TransactionsScreen

@Composable
fun InvestAINavGraph(
    navController: NavHostController,
    startDestination: String,
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
    ) {
        // ── Auth ──────────────────────────────────────
        composable(Screen.Login.route) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Screen.Home.route) {
                        popUpTo(Screen.Login.route) { inclusive = true }
                    }
                },
                onForgotPassword = {
                    navController.navigate(Screen.ForgotPassword.route)
                },
            )
        }

        composable(Screen.ForgotPassword.route) {
            ForgotPasswordScreen(
                onBack = { navController.popBackStack() },
                onPasswordReset = {
                    navController.navigate(Screen.Login.route) {
                        popUpTo(Screen.ForgotPassword.route) { inclusive = true }
                    }
                },
            )
        }

        // ── Bottom Tabs ───────────────────────────────
        composable(Screen.Home.route) {
            HomeScreen(
                onStockClick = { symbol ->
                    navController.navigate(Screen.StockDetail.createRoute(symbol))
                },
                onSeeAllWatchlist = {
                    navController.navigate(Screen.Portfolio.route)
                },
                onSeeAllNews = {
                    navController.navigate(Screen.News.route)
                },
            )
        }

        composable(Screen.Invest.route) {
            InvestScreen(
                onNavigate = { screen ->
                    navController.navigate(screen.route)
                }
            )
        }

        composable(Screen.Portfolio.route) {
            PortfolioScreen(
                onStockClick = { symbol ->
                    navController.navigate(Screen.StockDetail.createRoute(symbol))
                }
            )
        }

        composable(Screen.Alerts.route) {
            AlertsScreen()
        }

        composable(Screen.More.route) {
            MoreScreen(
                onNavigate = { screen ->
                    navController.navigate(screen.route)
                },
                onLogout = {
                    navController.navigate(Screen.Login.route) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        // ── Feature Screens ───────────────────────────
        composable(
            route = Screen.StockDetail.route,
            arguments = listOf(navArgument("symbol") { type = NavType.StringType }),
        ) { backStack ->
            val symbol = backStack.arguments?.getString("symbol") ?: return@composable
            StockDetailScreen(
                symbol = symbol,
                onBack = { navController.popBackStack() },
            )
        }

        composable(Screen.Screener.route) {
            ScreenerScreen(
                onStockClick = { symbol ->
                    navController.navigate(Screen.StockDetail.createRoute(symbol))
                },
                onBack = { navController.popBackStack() },
            )
        }

        // Placeholder composables for other screens will be added in later phases
        composable(Screen.Recommendations.route) {
            RecommendationsScreen(
                onStockClick = { symbol -> navController.navigate(Screen.StockDetail.createRoute(symbol)) },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Screen.AutoPilot.route) {
            AutoPilotScreen(
                onStockClick = { symbol -> navController.navigate(Screen.StockDetail.createRoute(symbol)) },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Screen.ValueScanner.route) { PlaceholderScreen("Value Scanner") }
        composable(Screen.SmartAdvisor.route) { PlaceholderScreen("Smart Advisor") }
        composable(Screen.TradingAdvisor.route) { PlaceholderScreen("Trading Advisor") }
        composable(Screen.Comparison.route) {
            ComparisonScreen(
                onStockClick = { symbol -> navController.navigate(Screen.StockDetail.createRoute(symbol)) },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Screen.ILFunds.route) { PlaceholderScreen("IL Funds") }
        composable(Screen.News.route) {
            NewsScreen(onBack = { navController.popBackStack() })
        }
        composable(Screen.Calendar.route) { PlaceholderScreen("Calendar") }
        composable(Screen.PicksTracker.route) { PlaceholderScreen("Picks Tracker") }
        composable(Screen.Education.route) { PlaceholderScreen("Education") }
        composable(Screen.RiskProfile.route) { PlaceholderScreen("Risk Profile") }
        composable(Screen.Transactions.route) {
            TransactionsScreen(onBack = { navController.popBackStack() })
        }
        composable(Screen.Budgets.route) {
            BudgetsScreen(onBack = { navController.popBackStack() })
        }
    }
}

@Composable
private fun PlaceholderScreen(title: String) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = "$title — Coming Soon",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
