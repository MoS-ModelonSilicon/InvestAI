package com.investai.app.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * All navigation routes in the app.
 */
sealed class Screen(val route: String) {
    // Auth
    data object Login : Screen("login")
    data object ForgotPassword : Screen("forgot_password")

    // Bottom tabs
    data object Home : Screen("home")
    data object Invest : Screen("invest")
    data object Portfolio : Screen("portfolio")
    data object Alerts : Screen("alerts")
    data object More : Screen("more")

    // Feature screens (navigated from hubs)
    data object StockDetail : Screen("stock/{symbol}") {
        fun createRoute(symbol: String) = "stock/$symbol"
    }
    data object Screener : Screen("screener")
    data object Recommendations : Screen("recommendations")
    data object AutoPilot : Screen("autopilot")
    data object ValueScanner : Screen("value_scanner")
    data object SmartAdvisor : Screen("smart_advisor")
    data object TradingAdvisor : Screen("trading_advisor")
    data object Comparison : Screen("comparison")
    data object ILFunds : Screen("il_funds")
    data object News : Screen("news")
    data object Calendar : Screen("calendar")
    data object PicksTracker : Screen("picks_tracker")
    data object Education : Screen("education")
    data object RiskProfile : Screen("risk_profile")
    data object Transactions : Screen("transactions")
    data object Budgets : Screen("budgets")
}

/**
 * Bottom navigation tab definition.
 */
data class BottomNavItem(
    val screen: Screen,
    val label: String,
    val selectedIcon: ImageVector,
    val unselectedIcon: ImageVector,
)

val bottomNavItems = listOf(
    BottomNavItem(
        screen = Screen.Home,
        label = "Home",
        selectedIcon = Icons.Filled.Home,
        unselectedIcon = Icons.Outlined.Home,
    ),
    BottomNavItem(
        screen = Screen.Invest,
        label = "Invest",
        selectedIcon = Icons.Filled.TrendingUp,
        unselectedIcon = Icons.Outlined.TrendingUp,
    ),
    BottomNavItem(
        screen = Screen.Portfolio,
        label = "Portfolio",
        selectedIcon = Icons.Filled.AccountBalanceWallet,
        unselectedIcon = Icons.Outlined.AccountBalanceWallet,
    ),
    BottomNavItem(
        screen = Screen.Alerts,
        label = "Alerts",
        selectedIcon = Icons.Filled.Notifications,
        unselectedIcon = Icons.Outlined.Notifications,
    ),
    BottomNavItem(
        screen = Screen.More,
        label = "More",
        selectedIcon = Icons.Filled.MoreHoriz,
        unselectedIcon = Icons.Outlined.MoreHoriz,
    ),
)
