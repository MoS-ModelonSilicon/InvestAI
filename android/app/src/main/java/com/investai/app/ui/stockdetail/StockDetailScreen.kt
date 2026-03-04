package com.investai.app.ui.stockdetail

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockDetailScreen(
    symbol: String,
    onBack: () -> Unit,
    viewModel: StockDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val detail = state.detail
    val currFmt = NumberFormat.getCurrencyInstance(Locale.US)
    val numFmt = NumberFormat.getNumberInstance(Locale.US)

    Column(modifier = Modifier.fillMaxSize()) {
        // Top bar
        TopAppBar(
            title = { Text(symbol, fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        if (state.isLoading) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                SkeletonCard(height = 120.dp)
                SkeletonCard(height = 200.dp)
                SkeletonCard(height = 150.dp)
            }
            return
        }

        if (detail == null) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Failed to load stock data", color = OnSurfaceVariant)
            }
            return
        }

        LazyColumn(
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // ── Price Header ─────────────────────────
            item {
                Column {
                    Text(
                        text = detail.name,
                        style = MaterialTheme.typography.bodyMedium,
                        color = OnSurfaceVariant,
                    )
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.Bottom) {
                        Text(
                            text = currFmt.format(detail.price),
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            color = OnSurface,
                        )
                        Spacer(Modifier.width(12.dp))
                        ChangeBadge(changePct = detail.changePct)
                    }
                }
            }

            // ── Chart ────────────────────────────────
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        // Period selector
                        val periods = listOf("1d", "5d", "1mo", "3mo", "6mo", "1y")
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            modifier = Modifier.horizontalScroll(rememberScrollState()),
                        ) {
                            periods.forEach { period ->
                                FilterChip(
                                    selected = state.selectedPeriod == period,
                                    onClick = { viewModel.selectPeriod(period) },
                                    label = { Text(period.uppercase(), fontSize = 11.sp) },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = Primary,
                                        selectedLabelColor = OnPrimary,
                                    ),
                                )
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                        // Sparkline of history data
                        if (state.history != null && state.history!!.prices.isNotEmpty()) {
                            SparklineChart(
                                data = state.history!!.prices,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(150.dp),
                                strokeWidth = 2f,
                            )
                        }
                    }
                }
            }

            // ── Signal Badge ─────────────────────────
            if (detail.signal != null) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            SignalBadge(signal = detail.signal)
                            if (detail.signalReason != null) {
                                Spacer(Modifier.width(12.dp))
                                Text(
                                    text = detail.signalReason,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = OnSurfaceVariant,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                }
            }

            // ── Key Stats Grid ───────────────────────
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Key Statistics", fontWeight = FontWeight.SemiBold, color = OnSurface)
                        Spacer(Modifier.height(12.dp))

                        val stats = buildList {
                            detail.marketCap?.let { add("Market Cap" to formatLargeNumber(it)) }
                            detail.pe?.let { add("P/E Ratio" to String.format(Locale.US, "%.2f", it)) }
                            detail.beta?.let { add("Beta" to String.format(Locale.US, "%.2f", it)) }
                            detail.dividendYield?.let { add("Div Yield" to String.format(Locale.US, "%.2f%%", it)) }
                            detail.volume?.let { add("Volume" to numFmt.format(it)) }
                            detail.week52High?.let { add("52w High" to currFmt.format(it)) }
                            detail.week52Low?.let { add("52w Low" to currFmt.format(it)) }
                            detail.sector?.let { add("Sector" to it) }
                        }

                        stats.chunked(2).forEach { row ->
                            Row(modifier = Modifier.fillMaxWidth()) {
                                row.forEach { (label, value) ->
                                    Column(modifier = Modifier.weight(1f).padding(vertical = 4.dp)) {
                                        Text(label, style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                        Text(value, style = MaterialTheme.typography.bodyMedium, color = OnSurface)
                                    }
                                }
                                if (row.size == 1) Spacer(Modifier.weight(1f))
                            }
                        }
                    }
                }
            }

            // ── Analyst Targets ──────────────────────
            if (detail.analystTargets != null) {
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Analyst Targets", fontWeight = FontWeight.SemiBold, color = OnSurface)
                            Spacer(Modifier.height(8.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                detail.analystTargets.low?.let {
                                    Column {
                                        Text("Low", style = MaterialTheme.typography.labelSmall, color = Loss)
                                        Text(currFmt.format(it), color = OnSurface)
                                    }
                                }
                                detail.analystTargets.mean?.let {
                                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text("Mean", style = MaterialTheme.typography.labelSmall, color = BlueInfo)
                                        Text(currFmt.format(it), color = OnSurface, fontWeight = FontWeight.Bold)
                                    }
                                }
                                detail.analystTargets.high?.let {
                                    Column(horizontalAlignment = Alignment.End) {
                                        Text("High", style = MaterialTheme.typography.labelSmall, color = Gain)
                                        Text(currFmt.format(it), color = OnSurface)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── News for this stock ──────────────────
            if (state.news.isNotEmpty()) {
                item {
                    Text(
                        "Related News",
                        fontWeight = FontWeight.SemiBold,
                        color = OnSurface,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
                items(state.news.take(5)) { news ->
                    Card(
                        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                news.title,
                                style = MaterialTheme.typography.bodyMedium,
                                color = OnSurface,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Spacer(Modifier.height(4.dp))
                            Text(news.source, style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                        }
                    }
                }
            }

            // Bottom spacer
            item { Spacer(Modifier.height(16.dp)) }
        }
    }
}

private fun formatLargeNumber(value: Double): String {
    return when {
        value >= 1_000_000_000_000 -> String.format(Locale.US, "$%.2fT", value / 1_000_000_000_000)
        value >= 1_000_000_000 -> String.format(Locale.US, "$%.2fB", value / 1_000_000_000)
        value >= 1_000_000 -> String.format(Locale.US, "$%.2fM", value / 1_000_000)
        else -> String.format(Locale.US, "$%.0f", value)
    }
}
