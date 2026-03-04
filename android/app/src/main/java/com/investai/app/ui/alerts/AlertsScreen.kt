package com.investai.app.ui.alerts

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.data.api.models.Alert
import com.investai.app.ui.components.*
import com.investai.app.ui.theme.*
import java.text.NumberFormat
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertsScreen(
    viewModel: AlertsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var showCreateDialog by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize()) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "Alerts",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = OnSurface,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = "${state.alerts.size}",
                style = MaterialTheme.typography.labelSmall,
                color = OnSurfaceVariant,
            )
            Spacer(Modifier.width(12.dp))
            FloatingActionButton(
                onClick = { showCreateDialog = true },
                containerColor = Primary,
                contentColor = OnPrimary,
                modifier = Modifier.size(40.dp),
            ) {
                Icon(Icons.Filled.Add, "New Alert")
            }
        }

        PullToRefreshBox(
            isRefreshing = state.isLoading,
            onRefresh = { viewModel.loadAlerts() },
        ) {
            LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (state.isLoading) {
                    items(4) { StockItemSkeleton() }
                } else if (state.alerts.isEmpty()) {
                    item {
                        Box(
                            modifier = Modifier.fillMaxWidth().padding(48.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(
                                    Icons.Filled.NotificationsNone,
                                    contentDescription = null,
                                    tint = OnSurfaceVariant,
                                    modifier = Modifier.size(48.dp),
                                )
                                Spacer(Modifier.height(12.dp))
                                Text("No alerts set", color = OnSurfaceVariant)
                                Text(
                                    "Tap + to create a price alert",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = OnSurfaceVariant,
                                )
                            }
                        }
                    }
                } else {
                    // Triggered alerts first
                    val triggered = state.alerts.filter { it.triggered }
                    val active = state.alerts.filter { !it.triggered && it.active }

                    if (triggered.isNotEmpty()) {
                        item {
                            Text(
                                "Triggered",
                                fontWeight = FontWeight.SemiBold,
                                color = Loss,
                                fontSize = 13.sp,
                            )
                        }
                        items(triggered) { alert -> AlertItem(alert, viewModel) }
                    }

                    if (active.isNotEmpty()) {
                        item {
                            Text(
                                "Active",
                                fontWeight = FontWeight.SemiBold,
                                color = Gain,
                                fontSize = 13.sp,
                            )
                        }
                        items(active) { alert -> AlertItem(alert, viewModel) }
                    }
                }
            }
        }
    }

    // ── Create Alert Dialog ─────────────────────
    if (showCreateDialog) {
        CreateAlertDialog(
            onDismiss = { showCreateDialog = false },
            onCreate = { symbol, condition, price ->
                viewModel.createAlert(symbol, condition, price)
                showCreateDialog = false
            },
        )
    }
}

@Composable
private fun AlertItem(alert: Alert, viewModel: AlertsViewModel) {
    val currencyFormat = NumberFormat.getCurrencyInstance(Locale.US)

    Card(
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        shape = RoundedCornerShape(12.dp),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = alert.symbol,
                    fontWeight = FontWeight.Bold,
                    color = OnSurface,
                )
                Text(
                    text = "${if (alert.condition == "above") "↑ Above" else "↓ Below"} ${currencyFormat.format(alert.targetPrice)}",
                    style = MaterialTheme.typography.labelSmall,
                    color = OnSurfaceVariant,
                )
                if (alert.currentPrice != null) {
                    Text(
                        text = "Current: ${currencyFormat.format(alert.currentPrice)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = OnSurfaceVariant,
                    )
                }
            }

            if (alert.triggered) {
                SignalBadge(signal = "Triggered")
            }

            IconButton(onClick = { viewModel.deleteAlert(alert.id) }) {
                Icon(Icons.Filled.Close, "Delete", tint = OnSurfaceVariant)
            }
        }
    }
}

@Composable
private fun CreateAlertDialog(
    onDismiss: () -> Unit,
    onCreate: (String, String, Double) -> Unit,
) {
    var symbol by remember { mutableStateOf("") }
    var condition by remember { mutableStateOf("above") }
    var price by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = SurfaceContainer,
        title = { Text("New Price Alert", color = OnSurface) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = symbol,
                    onValueChange = { symbol = it.uppercase() },
                    label = { Text("Symbol") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Primary,
                        unfocusedBorderColor = OutlineVariant,
                        focusedTextColor = OnSurface,
                        unfocusedTextColor = OnSurface,
                    ),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = condition == "above",
                        onClick = { condition = "above" },
                        label = { Text("Above") },
                    )
                    FilterChip(
                        selected = condition == "below",
                        onClick = { condition = "below" },
                        label = { Text("Below") },
                    )
                }
                OutlinedTextField(
                    value = price,
                    onValueChange = { price = it },
                    label = { Text("Target Price ($)") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = Primary,
                        unfocusedBorderColor = OutlineVariant,
                        focusedTextColor = OnSurface,
                        unfocusedTextColor = OnSurface,
                    ),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val p = price.toDoubleOrNull() ?: return@TextButton
                    if (symbol.isNotBlank()) onCreate(symbol, condition, p)
                },
            ) { Text("Create", color = Primary) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel", color = OnSurfaceVariant) }
        },
    )
}
