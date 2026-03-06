package com.investai.app.ui.smartadvisor

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.data.api.models.AdvisorRanking
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SmartAdvisorScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: SmartAdvisorViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Smart Advisor", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // ── Risk filter chips ───────────────────
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            listOf("conservative" to "Conservative", "balanced" to "Balanced", "aggressive" to "Aggressive").forEach { (v, l) ->
                FilterChip(
                    selected = state.risk == v,
                    onClick = { viewModel.setRisk(v) },
                    label = { Text(l, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Primary,
                        selectedLabelColor = OnPrimary,
                    ),
                )
            }
        }

        LazyColumn(
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (state.isLoading) {
                items(6) { StockItemSkeleton() }
            } else if (state.error != null) {
                item {
                    Text("Error: ${state.error}", color = Loss, modifier = Modifier.padding(16.dp))
                }
            } else {
                val analysis = state.analysis ?: return@LazyColumn

                // Report Card
                analysis.reportCard?.let { report ->
                    item {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("Market Report", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                                Spacer(Modifier.height(4.dp))
                                Text("Mood: ${report.marketMood}", fontSize = 13.sp, color = Primary)
                                Text("Scanned: ${report.totalScanned} stocks", fontSize = 12.sp, color = OnSurfaceVariant)
                                Spacer(Modifier.height(4.dp))
                                Text(report.summary, fontSize = 12.sp, color = OnSurfaceVariant)
                            }
                        }
                    }
                }

                // Portfolio allocation
                analysis.portfolio?.let { portfolio ->
                    item {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("Suggested Portfolio", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "Return: %.1f%%".format(portfolio.totalReturnPct),
                                    fontSize = 13.sp,
                                    color = if (portfolio.totalReturnPct >= 0) Gain else Loss,
                                )
                            }
                        }
                    }
                }

                // Rankings
                item {
                    Text("Top Ranked Stocks", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                }
                items(analysis.rankings) { ranking ->
                    RankingCard(ranking = ranking, onClick = { onStockClick(ranking.symbol) })
                }
            }
        }
    }
}

@Composable
private fun RankingCard(ranking: AdvisorRanking, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Rank badge
            Surface(
                color = Primary.copy(alpha = 0.15f),
                shape = MaterialTheme.shapes.small,
            ) {
                Text(
                    "#${ranking.rank}",
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    color = Primary,
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(ranking.symbol, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = OnSurface)
                Text(ranking.name, fontSize = 11.sp, color = OnSurfaceVariant, maxLines = 1)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("$%.2f".format(ranking.price), fontSize = 13.sp, color = OnSurface)
                Text(
                    "${if (ranking.changePct >= 0) "+" else ""}%.2f%%".format(ranking.changePct),
                    fontSize = 11.sp,
                    color = if (ranking.changePct >= 0) Gain else Loss,
                )
            }
            Spacer(Modifier.width(8.dp))
            SignalBadge(signal = ranking.signal)
        }
    }
}
