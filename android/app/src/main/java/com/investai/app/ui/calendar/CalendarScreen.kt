package com.investai.app.ui.calendar

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
import com.investai.app.data.api.models.EarningsEvent
import com.investai.app.data.api.models.EconomicEvent
import com.investai.app.ui.components.StockItemSkeleton
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: CalendarViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Calendar", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // Tabs
        TabRow(
            selectedTabIndex = state.selectedTab,
            containerColor = Surface,
            contentColor = Primary,
        ) {
            Tab(
                selected = state.selectedTab == 0,
                onClick = { viewModel.selectTab(0) },
                text = { Text("Earnings") },
            )
            Tab(
                selected = state.selectedTab == 1,
                onClick = { viewModel.selectTab(1) },
                text = { Text("Economic") },
            )
        }

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
            } else if (state.selectedTab == 0) {
                if (state.earnings.isEmpty()) {
                    item {
                        Text("No upcoming earnings", color = OnSurfaceVariant, modifier = Modifier.padding(16.dp))
                    }
                }
                items(state.earnings) { event ->
                    EarningsCard(event = event, onClick = { onStockClick(event.symbol) })
                }
            } else {
                if (state.economic.isEmpty()) {
                    item {
                        Text("No upcoming events", color = OnSurfaceVariant, modifier = Modifier.padding(16.dp))
                    }
                }
                items(state.economic) { event ->
                    EconomicCard(event = event)
                }
            }
        }
    }
}

@Composable
private fun EarningsCard(event: EarningsEvent, onClick: () -> Unit) {
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
                Text(event.symbol, fontWeight = FontWeight.Bold, fontSize = 15.sp, color = OnSurface)
                Text(event.name, fontSize = 12.sp, color = OnSurfaceVariant, maxLines = 1)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(event.date, fontSize = 12.sp, color = Primary)
                event.estimateEps?.let {
                    Text("EPS est: $%.2f".format(it), fontSize = 11.sp, color = OnSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun EconomicCard(event: EconomicEvent) {
    Card(
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(event.event, fontWeight = FontWeight.Medium, fontSize = 14.sp, color = OnSurface)
                Text("${event.country} · ${event.date}", fontSize = 11.sp, color = OnSurfaceVariant)
            }
            Surface(
                color = when (event.impact.lowercase()) {
                    "high" -> Loss.copy(alpha = 0.15f)
                    "medium" -> Caution.copy(alpha = 0.15f)
                    else -> Gain.copy(alpha = 0.15f)
                },
                shape = MaterialTheme.shapes.small,
            ) {
                Text(
                    event.impact,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = when (event.impact.lowercase()) {
                        "high" -> Loss
                        "medium" -> Caution
                        else -> Gain
                    },
                )
            }
        }
    }
}
