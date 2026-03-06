package com.investai.app.ui.tradingadvisor

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.data.api.models.TradingPackage
import com.investai.app.data.api.models.TradingPick
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TradingAdvisorScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: TradingAdvisorViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Trading Advisor", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

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
                val dash = state.dashboard ?: return@LazyColumn

                // Market mood banner
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Market Mood", fontSize = 12.sp, color = OnSurfaceVariant)
                            Spacer(Modifier.height(4.dp))
                            Text(
                                dash.marketMood,
                                fontWeight = FontWeight.Bold,
                                fontSize = 20.sp,
                                color = when {
                                    dash.marketMood.contains("Bull", true) -> Gain
                                    dash.marketMood.contains("Bear", true) -> Loss
                                    else -> Caution
                                },
                            )
                        }
                    }
                }

                // Packages
                dash.packages.forEach { pkg ->
                    item {
                        Text(pkg.name, fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                        if (pkg.description.isNotEmpty()) {
                            Text(pkg.description, fontSize = 12.sp, color = OnSurfaceVariant)
                        }
                    }
                    items(pkg.picks) { pick ->
                        TradingPickCard(pick = pick, onClick = { onStockClick(pick.symbol) })
                    }
                }

                // Top picks if any not in packages
                if (dash.picks.isNotEmpty()) {
                    item {
                        Text("Top Picks", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                    }
                    items(dash.picks) { pick ->
                        TradingPickCard(pick = pick, onClick = { onStockClick(pick.symbol) })
                    }
                }
            }
        }
    }
}

@Composable
private fun TradingPickCard(pick: TradingPick, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(pick.symbol, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = OnSurface)
                SignalBadge(signal = pick.signal)
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                LabelValue("Score", "%.0f".format(pick.score))
                LabelValue("Entry", pick.entry?.let { "$%.2f".format(it) } ?: "-")
                LabelValue("Target", pick.target?.let { "$%.2f".format(it) } ?: "-")
                LabelValue("Stop", pick.stop?.let { "$%.2f".format(it) } ?: "-")
                LabelValue("R:R", pick.riskReward?.let { "%.1f".format(it) } ?: "-")
            }
        }
    }
}

@Composable
private fun LabelValue(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, fontSize = 10.sp, color = OnSurfaceVariant)
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = OnSurface)
    }
}
