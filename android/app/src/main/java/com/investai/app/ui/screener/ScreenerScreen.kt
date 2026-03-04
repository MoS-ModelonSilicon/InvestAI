package com.investai.app.ui.screener

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
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*

/**
 * Stock Screener with filter chips (mobile-adapted from web sidebar).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScreenerScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: ScreenerViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Screener", fontWeight = FontWeight.Bold)
                    if (state.total > 0) {
                        Spacer(Modifier.width(8.dp))
                        Text(
                            "${state.total} results",
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
            // Asset Type chips
            val assetTypes = listOf(null to "All", "Stock" to "Stocks", "ETF" to "ETFs")
            assetTypes.forEach { (value, label) ->
                FilterChip(
                    selected = state.assetType == value,
                    onClick = { viewModel.setAssetType(value) },
                    label = { Text(label, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Primary,
                        selectedLabelColor = OnPrimary,
                    ),
                )
            }

            // Sector dropdown chip
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
        }

        // ── Quick presets ──────────────────────
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            listOf("Value" to "Value", "Growth" to "Growth", "High Div" to "Dividend").forEach { (label, _) ->
                AssistChip(
                    onClick = { /* apply preset */ },
                    label = { Text(label, fontSize = 11.sp) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = SurfaceContainer,
                        labelColor = OnSurfaceVariant,
                    ),
                )
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
                items(state.stocks) { stock ->
                    StockListItem(
                        symbol = stock.symbol,
                        name = stock.name,
                        price = stock.price,
                        changePct = stock.changePct,
                        onClick = { onStockClick(stock.symbol) },
                    )
                }

                // Pagination
                if (state.totalPages > 1) {
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            TextButton(
                                onClick = { viewModel.previousPage() },
                                enabled = state.page > 1,
                            ) { Text("← Prev") }
                            Text(
                                "${state.page} / ${state.totalPages}",
                                color = OnSurfaceVariant,
                                modifier = Modifier.padding(horizontal = 16.dp),
                            )
                            TextButton(
                                onClick = { viewModel.nextPage() },
                                enabled = state.page < state.totalPages,
                            ) { Text("Next →") }
                        }
                    }
                }
            }
        }
    }
}
