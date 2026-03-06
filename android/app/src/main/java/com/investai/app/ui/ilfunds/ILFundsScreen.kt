package com.investai.app.ui.ilfunds

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
import com.investai.app.data.api.models.ILFund
import com.investai.app.ui.components.StockItemSkeleton
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ILFundsScreen(
    onBack: () -> Unit,
    viewModel: ILFundsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Israeli Funds", fontWeight = FontWeight.Bold)
                    if (state.total > 0) {
                        Spacer(Modifier.width(8.dp))
                        Text("${state.total} funds", style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
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

        // Filter chips
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Kosher toggle
            FilterChip(
                selected = state.kosherOnly == true,
                onClick = { viewModel.setKosherOnly(if (state.kosherOnly == true) null else true) },
                label = { Text("Kosher", fontSize = 12.sp) },
                leadingIcon = if (state.kosherOnly == true) {
                    { Icon(Icons.Filled.Check, null, Modifier.size(16.dp)) }
                } else null,
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Primary,
                    selectedLabelColor = OnPrimary,
                ),
            )

            // Fund type dropdown
            var typeExpanded by remember { mutableStateOf(false) }
            Box {
                FilterChip(
                    selected = state.fundType != null,
                    onClick = { typeExpanded = true },
                    label = { Text(state.fundType ?: "Fund Type", fontSize = 12.sp) },
                    trailingIcon = { Icon(Icons.Filled.ArrowDropDown, null, Modifier.size(16.dp)) },
                )
                DropdownMenu(expanded = typeExpanded, onDismissRequest = { typeExpanded = false }) {
                    DropdownMenuItem(text = { Text("All Types") }, onClick = {
                        viewModel.setFundType(null); typeExpanded = false
                    })
                    state.types.forEach { t ->
                        DropdownMenuItem(text = { Text(t) }, onClick = {
                            viewModel.setFundType(t); typeExpanded = false
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
                    listOf("fee" to "Fee", "annual_return" to "Annual Return", "size_m" to "Size").forEach { (v, l) ->
                        DropdownMenuItem(text = { Text(l) }, onClick = {
                            viewModel.setSortBy(v); sortExpanded = false
                        })
                    }
                }
            }
        }

        // Funds list
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
                items(state.funds) { fund ->
                    FundCard(fund = fund)
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
private fun FundCard(fund: ILFund) {
    Card(
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(fund.name, fontWeight = FontWeight.Medium, fontSize = 14.sp, color = OnSurface, maxLines = 2)
                    Text(fund.manager, fontSize = 11.sp, color = OnSurfaceVariant)
                }
                if (fund.kosher) {
                    Surface(
                        color = Gain.copy(alpha = 0.15f),
                        shape = MaterialTheme.shapes.extraSmall,
                    ) {
                        Text(
                            "Kosher",
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                            fontSize = 10.sp,
                            color = Gain,
                        )
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                FundMetric("Fee", "%.2f%%".format(fund.fee))
                FundMetric("Annual", fund.annualReturn?.let { "${if (it >= 0) "+" else ""}%.1f%%".format(it) } ?: "N/A",
                    color = fund.annualReturn?.let { if (it >= 0) Gain else Loss } ?: OnSurfaceVariant)
                FundMetric("YTD", fund.ytdReturn?.let { "${if (it >= 0) "+" else ""}%.1f%%".format(it) } ?: "N/A",
                    color = fund.ytdReturn?.let { if (it >= 0) Gain else Loss } ?: OnSurfaceVariant)
                FundMetric("Type", fund.fundType)
            }
        }
    }
}

@Composable
private fun FundMetric(
    label: String,
    value: String,
    color: androidx.compose.ui.graphics.Color = OnSurface,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, fontSize = 10.sp, color = OnSurfaceVariant)
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = color)
    }
}
