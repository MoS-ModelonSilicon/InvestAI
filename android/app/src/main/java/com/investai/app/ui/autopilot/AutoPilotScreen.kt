package com.investai.app.ui.autopilot

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AutoPilotScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: AutoPilotViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("AutoPilot", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        if (state.isLoading) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                SkeletonCard(height = 60.dp)
                repeat(4) { StockItemSkeleton() }
            }
            return
        }

        LazyColumn(
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Profile selector chips
            item {
                Text("Strategy Profile", fontWeight = FontWeight.SemiBold, color = OnSurface)
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    state.profiles.forEach { profile ->
                        FilterChip(
                            selected = state.selectedProfile == profile.id,
                            onClick = { viewModel.selectProfile(profile.id) },
                            label = { Text(profile.name) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Primary,
                                selectedLabelColor = OnPrimary,
                            ),
                        )
                    }
                }
            }

            // Simulation results
            val sim = state.simulation
            if (state.isSimulating) {
                item { SkeletonCard(height = 120.dp) }
                items(4) { StockItemSkeleton() }
            } else if (sim != null) {
                // Summary card
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("Simulation Result", fontWeight = FontWeight.SemiBold, color = OnSurface)
                            Spacer(Modifier.height(8.dp))
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Column {
                                    Text("Final Value", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                    Text(
                                        "$${String.format(Locale.US, "%,.0f", sim.finalValue)}",
                                        fontFamily = FontFamily.Monospace,
                                        fontWeight = FontWeight.Bold,
                                        color = OnSurface,
                                    )
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("Return", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                    Text(
                                        "${String.format(Locale.US, "%+.1f", sim.totalReturnPct)}%",
                                        fontFamily = FontFamily.Monospace,
                                        fontWeight = FontWeight.Bold,
                                        color = if (sim.totalReturnPct >= 0) Gain else Loss,
                                    )
                                }
                            }
                            Spacer(Modifier.height(8.dp))
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Column {
                                    Text("Benchmark", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                    Text(
                                        "${String.format(Locale.US, "%+.1f", sim.benchmarkReturnPct)}%",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = OnSurfaceVariant,
                                    )
                                }
                                sim.sharpeRatio?.let { sr ->
                                    Column(horizontalAlignment = Alignment.End) {
                                        Text("Sharpe", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
                                        Text(
                                            String.format(Locale.US, "%.2f", sr),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = OnSurface,
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                // Holdings
                if (sim.holdings.isNotEmpty()) {
                    item { SectionHeader(title = "Holdings", count = sim.holdings.size) }
                    items(sim.holdings) { holding ->
                        StockListItem(
                            symbol = holding.symbol,
                            name = "${holding.sleeve} · ${String.format(Locale.US, "%.1f", holding.shares)} shares",
                            price = holding.currentPrice,
                            changePct = holding.gainLossPct,
                            onClick = { onStockClick(holding.symbol) },
                        )
                    }
                }
            }
        }
    }
}
