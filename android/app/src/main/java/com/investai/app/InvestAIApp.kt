package com.investai.app

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.investai.app.navigation.InvestAINavGraph
import com.investai.app.navigation.Screen
import com.investai.app.navigation.bottomNavItems
import com.investai.app.ui.auth.AuthViewModel
import com.investai.app.ui.theme.*

/**
 * Root composable: bottom navigation + NavHost.
 * Hides bottom bar on login, stock detail, and nested feature screens.
 */
@Composable
fun InvestAIApp(
    authViewModel: AuthViewModel = hiltViewModel(),
) {
    val isLoggedIn by authViewModel.isLoggedIn.collectAsStateWithLifecycle(initialValue = null)

    // Wait for auth state to resolve
    if (isLoggedIn == null) return

    val navController = rememberNavController()
    val startDestination = if (isLoggedIn == true) Screen.Home.route else Screen.Login.route

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    // Show bottom bar only on the 5 main tabs
    val showBottomBar = currentRoute in listOf(
        Screen.Home.route,
        Screen.Invest.route,
        Screen.Portfolio.route,
        Screen.Alerts.route,
        Screen.More.route,
    )

    Scaffold(
        containerColor = Surface,
        bottomBar = {
            AnimatedVisibility(
                visible = showBottomBar,
                enter = slideInVertically(initialOffsetY = { it }),
                exit = slideOutVertically(targetOffsetY = { it }),
            ) {
                NavigationBar(
                    containerColor = SurfaceContainerLowest,
                    contentColor = OnSurface,
                    tonalElevation = androidx.compose.ui.unit.dp.times(0),
                ) {
                    bottomNavItems.forEach { item ->
                        val selected = navBackStackEntry?.destination?.hierarchy?.any {
                            it.route == item.screen.route
                        } == true

                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(item.screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                Icon(
                                    imageVector = if (selected) item.selectedIcon else item.unselectedIcon,
                                    contentDescription = item.label,
                                )
                            },
                            label = { Text(item.label) },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = Primary,
                                selectedTextColor = Primary,
                                unselectedIconColor = OnSurfaceVariant,
                                unselectedTextColor = OnSurfaceVariant,
                                indicatorColor = SurfaceContainer,
                            ),
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding)) {
            InvestAINavGraph(
                navController = navController,
                startDestination = startDestination,
            )
        }
    }
}
