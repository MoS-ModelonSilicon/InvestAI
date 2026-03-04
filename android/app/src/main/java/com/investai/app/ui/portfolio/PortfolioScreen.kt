package com.investai.app.ui.portfolio

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PortfolioScreen(
    onStockClick: (String) -> Unit,
    viewModel: PortfolioViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "Portfolio",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = OnSurface,
                modifier = Modifier.weight(1f),
            )
            FloatingActionButton(
                onClick = { /* TODO: open add holding bottom sheet */ },
                containerColor = Primary,
                contentColor = OnPrimary,
                modifier = Modifier.size(40.dp),
            ) {
                Icon(Icons.Filled.Add, contentDescription = "Add Holding")
            }
        }

        // Tabs: Holdings | Watchlist
        TabRow(
            selectedTabIndex = state.selectedTab,
            containerColor = Surface,
            contentColor = OnSurface,
            indicator = {
                TabRowDefaults.SecondaryIndicator(
                    color = Primary,
                )
            },
        ) {
            Tab(
                selected = state.selectedTab == 0,
                onClick = { viewModel.selectTab(0) },
                text = { Text("Holdings") },
                selectedContentColor = Primary,
                unselectedContentColor = OnSurfaceVariant,
            )
            Tab(
                selected = state.selectedTab == 1,
                onClick = { viewModel.selectTab(1) },
                text = { Text("Watchlist") },
                selectedContentColor = Primary,
                unselectedContentColor = OnSurfaceVariant,
            )
        }

        PullToRefreshBox(
            isRefreshing = state.isLoading,
            onRefresh = { viewModel.refresh() },
        ) {
            when (state.selectedTab) {
                0 -> HoldingsList(state = state, onStockClick = onStockClick)
                1 -> WatchlistList(state = state, onStockClick = onStockClick)
            }
        }
    }
}

@Composable
private fun HoldingsList(
    state: PortfolioUiState,
    onStockClick: (String) -> Unit,
) {
    val summary = state.summary

    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // Portfolio summary card
        if (summary != null) {
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Column {
                                Text("Invested", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                PriceText(value = summary.totalInvested, showSign = false, fontSize = 15)
                            }
                            Column(horizontalAlignment = Alignment.End) {
                                Text("Current", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                PriceText(value = summary.currentValue, showSign = false, fontSize = 15)
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("P&L: ", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                            PriceText(value = summary.totalGainLoss, fontSize = 14)
                            Spacer(Modifier.width(8.dp))
                            ChangeBadge(changePct = summary.totalGainLossPct)
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
            }
        }

        // Holdings list
        if (state.isLoading) {
            items(5) {
                StockItemSkeleton(modifier = Modifier.padding(vertical = 2.dp))
            }
        } else if (summary?.holdings.isNullOrEmpty()) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(32.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("No holdings yet. Tap + to add.", color = OnSurfaceVariant)
                }
            }
        } else {
            items(summary!!.holdings) { holding ->
                StockListItem(
                    symbol = holding.symbol,
                    name = holding.name,
                    price = holding.currentPrice,
                    changePct = holding.gainLossPct,
                    onClick = { onStockClick(holding.symbol) },
                )
            }
        }
    }
}

@Composable
private fun WatchlistList(
    state: PortfolioUiState,
    onStockClick: (String) -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (state.isLoading) {
            items(5) {
                StockItemSkeleton(modifier = Modifier.padding(vertical = 2.dp))
            }
        } else if (state.watchlistItems.isEmpty()) {
            item {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(32.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text("Watchlist empty. Add stocks from the Screener.", color = OnSurfaceVariant)
                }
            }
        } else {
            items(state.watchlistItems) { item ->
                StockListItem(
                    symbol = item.symbol,
                    name = item.name ?: "",
                    price = item.price,
                    changePct = item.changePct,
                    onClick = { onStockClick(item.symbol) },
                )
            }
        }
    }
}
