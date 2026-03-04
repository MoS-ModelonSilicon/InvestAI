package com.investai.app.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.data.api.models.*
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onStockClick: (String) -> Unit,
    onSeeAllWatchlist: () -> Unit,
    onSeeAllNews: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    PullToRefreshBox(
        isRefreshing = state.isRefreshing,
        onRefresh = { viewModel.refresh() },
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(bottom = 16.dp),
        ) {
            // ── App Bar ────────────────────────────────
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "InvestAI",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        color = Primary,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { /* navigate to alerts */ }) {
                        Icon(
                            Icons.Filled.Notifications,
                            contentDescription = "Alerts",
                            tint = OnSurfaceVariant,
                        )
                    }
                }
            }

            // ── Portfolio Hero Card ────────────────────
            item {
                if (state.isLoading) {
                    SkeletonCard(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        height = 120.dp,
                    )
                } else {
                    PortfolioHeroCard(
                        value = state.portfolioValue,
                        change = state.portfolioChange,
                        changePct = state.portfolioChangePct,
                        modifier = Modifier.padding(horizontal = 16.dp),
                    )
                }
            }

            // ── Live Markets Ticker ────────────────────
            item {
                SectionHeader(title = "Live Markets")
            }
            item {
                if (state.isLoading) {
                    Row(
                        modifier = Modifier
                            .padding(horizontal = 16.dp)
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        repeat(4) {
                            SkeletonLoader(width = 100.dp, height = 40.dp)
                        }
                    }
                } else {
                    MarketTickerRow(
                        items = state.tickerItems,
                        onClick = { onStockClick(it.symbol) },
                    )
                }
            }

            // ── Watchlist Carousel ─────────────────────
            item {
                SectionHeader(
                    title = "Your Watchlist",
                    count = state.watchlistItems.size,
                    actionText = "See All",
                    onAction = onSeeAllWatchlist,
                )
            }
            item {
                if (state.isLoading) {
                    LazyRow(
                        contentPadding = PaddingValues(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        items(3) { SkeletonCard(modifier = Modifier.width(140.dp), height = 90.dp) }
                    }
                } else if (state.watchlistItems.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text("No watchlist items yet", color = OnSurfaceVariant)
                    }
                } else {
                    WatchlistCarousel(
                        items = state.watchlistItems,
                        onClick = { onStockClick(it.symbol) },
                    )
                }
            }

            // ── Budget Status ──────────────────────────
            if (state.budgetStatus.isNotEmpty()) {
                item { SectionHeader(title = "Budget Status") }
                item {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        state.budgetStatus.forEach { budget ->
                            ProgressRing(
                                percent = budget.percent,
                                label = budget.category,
                            )
                        }
                    }
                }
            }

            // ── Market News ────────────────────────────
            item {
                SectionHeader(
                    title = "Market News",
                    actionText = "See All",
                    onAction = onSeeAllNews,
                )
            }
            if (state.isLoading) {
                items(3) {
                    SkeletonCard(
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                        height = 76.dp,
                    )
                }
            } else {
                items(state.newsItems) { news ->
                    NewsCard(
                        news = news,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                    )
                }
            }
        }
    }
}

// ── Sub-Composables ──────────────────────────────────────

@Composable
private fun PortfolioHeroCard(
    value: Double,
    change: Double,
    changePct: Double,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Text(
                text = "Total Portfolio Value",
                style = MaterialTheme.typography.labelMedium,
                color = OnSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            HeroPrice(value = value)
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (change >= 0) Icons.Filled.TrendingUp else Icons.Filled.TrendingDown,
                    contentDescription = null,
                    tint = if (change >= 0) Gain else Loss,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(6.dp))
                PriceText(value = change, fontSize = 14)
                Spacer(Modifier.width(8.dp))
                ChangeBadge(changePct = changePct)
            }
        }
    }
}

@Composable
private fun MarketTickerRow(
    items: List<TickerItem>,
    onClick: (TickerItem) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items.forEach { item ->
            val isPositive = item.changePct >= 0
            val bgColor = if (isPositive) GainBg else LossBg
            val textColor = if (isPositive) Gain else Loss

            Surface(
                modifier = Modifier.clickable { onClick(item) },
                shape = RoundedCornerShape(10.dp),
                color = bgColor,
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = item.symbol,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = OnSurface,
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "${if (isPositive) "+" else ""}${String.format(Locale.US, "%.1f%%", item.changePct)}",
                        color = textColor,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        fontFamily = FontFamily.Monospace,
                    )
                }
            }
        }
    }
}

@Composable
private fun WatchlistCarousel(
    items: List<WatchlistItemLive>,
    onClick: (WatchlistItemLive) -> Unit,
) {
    LazyRow(
        contentPadding = PaddingValues(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        items(items) { item ->
            WatchlistCard(item = item, onClick = { onClick(item) })
        }
    }
}

@Composable
private fun WatchlistCard(
    item: WatchlistItemLive,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .width(140.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = item.symbol,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                color = OnSurface,
            )
            Spacer(Modifier.height(4.dp))
            if (item.price != null) {
                Text(
                    text = NumberFormat.getCurrencyInstance(Locale.US).format(item.price),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                    color = OnSurface,
                )
            }
            if (item.changePct != null) {
                Spacer(Modifier.height(4.dp))
                ChangeBadge(changePct = item.changePct)
            }
        }
    }
}

@Composable
private fun NewsCard(
    news: NewsItem,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = news.title,
                style = MaterialTheme.typography.bodyMedium,
                color = OnSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                fontWeight = FontWeight.Medium,
            )
            Spacer(Modifier.height(6.dp))
            Row {
                Text(
                    text = news.source,
                    style = MaterialTheme.typography.labelSmall,
                    color = OnSurfaceVariant,
                )
                if (news.symbols.isNotEmpty()) {
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = news.symbols.take(3).joinToString(", "),
                        style = MaterialTheme.typography.labelSmall,
                        color = Primary,
                    )
                }
            }
        }
    }
}
