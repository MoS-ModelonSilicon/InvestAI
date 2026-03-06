package com.investai.app.ui.pickstracker

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
import com.investai.app.data.api.models.Pick
import com.investai.app.ui.components.StockItemSkeleton
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PicksTrackerScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: PicksTrackerViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Picks Tracker", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            actions = {
                IconButton(
                    onClick = { viewModel.seedWatchlist() },
                    enabled = !state.seedingWatchlist,
                ) {
                    if (state.seedingWatchlist) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Filled.PlaylistAdd, "Seed Watchlist")
                    }
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // Seed result banner
        state.seedResult?.let { msg ->
            Card(
                colors = CardDefaults.cardColors(containerColor = Primary.copy(alpha = 0.1f)),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Text(msg, modifier = Modifier.padding(12.dp), fontSize = 12.sp, color = Primary)
            }
        }

        // Type filter chips
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            listOf(null to "All", "swing" to "Swing", "day" to "Day", "scalp" to "Scalp", "long" to "Long").forEach { (v, l) ->
                FilterChip(
                    selected = state.selectedType == v,
                    onClick = { viewModel.setType(v) },
                    label = { Text(l, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Primary,
                        selectedLabelColor = OnPrimary,
                    ),
                )
            }
        }

        // Stats card
        state.stats?.let { stats ->
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            ) {
                Row(
                    modifier = Modifier.padding(12.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                ) {
                    StatColumn("Total", "${stats.total}")
                    StatColumn("Wins", "${stats.wins}", Gain)
                    StatColumn("Losses", "${stats.losses}", Loss)
                    StatColumn("Win Rate", "%.0f%%".format(stats.winRate), if (stats.winRate >= 50) Gain else Loss)
                    StatColumn("Avg Gain", "%.1f%%".format(stats.avgGain), if (stats.avgGain >= 0) Gain else Loss)
                }
            }
        }

        // Picks list
        LazyColumn(
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (state.isLoading) {
                items(8) { StockItemSkeleton() }
            } else if (state.error != null) {
                item {
                    Text("Error: ${state.error}", color = Loss, modifier = Modifier.padding(16.dp))
                }
            } else {
                items(state.picks) { pick ->
                    PickCard(pick = pick, onClick = { onStockClick(pick.symbol) })
                }
            }
        }
    }
}

@Composable
private fun StatColumn(label: String, value: String, color: androidx.compose.ui.graphics.Color = OnSurface) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = color)
        Text(label, fontSize = 10.sp, color = OnSurfaceVariant)
    }
}

@Composable
private fun PickCard(pick: Pick, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(pick.symbol, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = OnSurface)
                    Spacer(Modifier.width(8.dp))
                    Surface(
                        color = Primary.copy(alpha = 0.15f),
                        shape = MaterialTheme.shapes.extraSmall,
                    ) {
                        Text(
                            pick.type,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            fontSize = 10.sp,
                            color = Primary,
                        )
                    }
                }
                Text(
                    "Entry: $%.2f".format(pick.entry) +
                        (pick.target?.let { " → $%.2f".format(it) } ?: "") +
                        (pick.stop?.let { " | Stop: $%.2f".format(it) } ?: ""),
                    fontSize = 11.sp,
                    color = OnSurfaceVariant,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    pick.status,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                    color = when (pick.status.lowercase()) {
                        "win" -> Gain
                        "loss" -> Loss
                        else -> Caution
                    },
                )
                pick.pnlPct?.let {
                    Text(
                        "${if (it >= 0) "+" else ""}%.1f%%".format(it),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (it >= 0) Gain else Loss,
                    )
                }
            }
        }
    }
}
