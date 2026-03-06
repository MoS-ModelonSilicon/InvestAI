package com.investai.app.ui.valuescanner

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
import com.investai.app.data.api.models.ValueStock
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ValueScannerScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: ValueScannerViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Value Scanner", fontWeight = FontWeight.Bold)
                    if (state.total > 0) {
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "${state.total} found",
                            style = MaterialTheme.typography.labelSmall,
                            color = OnSurfaceVariant,
                        )
                    }
                }
            },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // ── Filter chips row ───────────────────
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Signal filter chips
            val signals = listOf(null to "All", "Strong Buy" to "Strong Buy", "Buy" to "Buy", "Watch" to "Watch")
            signals.forEach { (value, label) ->
                FilterChip(
                    selected = state.selectedSignal == value,
                    onClick = { viewModel.setSignal(value) },
                    label = { Text(label, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Primary,
                        selectedLabelColor = OnPrimary,
                    ),
                )
            }

            // Sector dropdown
            var sectorExpanded by remember { mutableStateOf(false) }
            Box {
                FilterChip(
                    selected = state.selectedSector != null,
                    onClick = { sectorExpanded = true },
                    label = { Text(state.selectedSector ?: "Sector", fontSize = 12.sp) },
                    trailingIcon = { Icon(Icons.Filled.ArrowDropDown, null, Modifier.size(16.dp)) },
                )
                DropdownMenu(expanded = sectorExpanded, onDismissRequest = { sectorExpanded = false }) {
                    DropdownMenuItem(text = { Text("All Sectors") }, onClick = {
                        viewModel.setSector(null); sectorExpanded = false
                    })
                    state.sectors.forEach { sector ->
                        DropdownMenuItem(text = { Text(sector) }, onClick = {
                            viewModel.setSector(sector); sectorExpanded = false
                        })
                    }
                }
            }

            // Sort dropdown
            var sortExpanded by remember { mutableStateOf(false) }
            Box {
                AssistChip(
                    onClick = { sortExpanded = true },
                    label = { Text("Sort: ${state.sortBy}", fontSize = 12.sp) },
                    trailingIcon = { Icon(Icons.Filled.ArrowDropDown, null, Modifier.size(16.dp)) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = SurfaceContainer,
                        labelColor = OnSurfaceVariant,
                    ),
                )
                DropdownMenu(expanded = sortExpanded, onDismissRequest = { sortExpanded = false }) {
                    listOf("score" to "Score", "margin_of_safety" to "Margin of Safety", "pe" to "P/E").forEach { (v, l) ->
                        DropdownMenuItem(text = { Text(l) }, onClick = {
                            viewModel.setSortBy(v); sortExpanded = false
                        })
                    }
                }
            }
        }

        // ── Results list ───────────────────────
        LazyColumn(
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (state.isLoading) {
                items(8) { StockItemSkeleton() }
            } else {
                items(state.candidates) { stock ->
                    ValueStockCard(stock = stock, onClick = { onStockClick(stock.symbol) })
                }

                // Pagination
                if (state.totalPages > 1) {
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            TextButton(onClick = { viewModel.previousPage() }, enabled = state.page > 1) {
                                Text("← Prev")
                            }
                            Text(
                                "${state.page} / ${state.totalPages}",
                                color = OnSurfaceVariant,
                                modifier = Modifier.padding(horizontal = 16.dp),
                            )
                            TextButton(onClick = { viewModel.nextPage() }, enabled = state.page < state.totalPages) {
                                Text("Next →")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ValueStockCard(stock: ValueStock, onClick: () -> Unit) {
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
                Column {
                    Text(stock.symbol, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = OnSurface)
                    Text(stock.name, fontSize = 12.sp, color = OnSurfaceVariant, maxLines = 1)
                }
                SignalBadge(signal = stock.signal)
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                MetricColumn("Score", "%.0f".format(stock.score))
                MetricColumn("MoS", stock.marginOfSafety?.let { "%.1f%%".format(it) } ?: "N/A")
                MetricColumn("P/E", stock.pe?.let { "%.1f".format(it) } ?: "N/A")
                MetricColumn("Price", "$%.2f".format(stock.price))
            }
        }
    }
}

@Composable
private fun MetricColumn(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, fontSize = 10.sp, color = OnSurfaceVariant)
        Text(value, fontSize = 13.sp, fontWeight = FontWeight.Medium, color = OnSurface)
    }
}
