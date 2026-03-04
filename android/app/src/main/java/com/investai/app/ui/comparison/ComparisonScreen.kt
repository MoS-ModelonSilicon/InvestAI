package com.investai.app.ui.comparison

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CompareArrows
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.components.SkeletonCard
import com.investai.app.ui.theme.*
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComparisonScreen(
    onStockClick: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: ComparisonViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Compare Stocks", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // Input
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = state.symbols,
                onValueChange = { viewModel.setSymbols(it) },
                label = { Text("Symbols (e.g. AAPL,MSFT,GOOG)") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = { viewModel.compare() },
                colors = ButtonDefaults.buttonColors(containerColor = Primary),
                enabled = state.symbols.isNotBlank() && !state.isLoading,
            ) {
                Icon(Icons.Default.CompareArrows, null, Modifier.size(18.dp))
            }
        }

        if (state.isLoading) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                repeat(3) { SkeletonCard(height = 100.dp) }
            }
            return
        }

        val result = state.result ?: return

        LazyColumn(
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(result.stocks) { stock ->
                Card(
                    onClick = { onStockClick(stock.symbol) },
                    colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(stock.symbol, fontWeight = FontWeight.Bold, color = OnSurface, fontSize = 16.sp)
                            Text(
                                "$${String.format(Locale.US, "%.2f", stock.price)}",
                                fontWeight = FontWeight.Bold,
                                color = OnSurface,
                            )
                        }
                        Spacer(Modifier.height(4.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                        ) {
                            stock.pe?.let {
                                CompactStat("P/E", String.format(Locale.US, "%.1f", it))
                            }
                            stock.marketCap?.let {
                                CompactStat("MCap", formatMCap(it))
                            }
                            stock.dividendYield?.let {
                                CompactStat("Div", String.format(Locale.US, "%.2f%%", it))
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CompactStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = OnSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodySmall, color = OnSurface)
    }
}

private fun formatMCap(value: Double): String = when {
    value >= 1e12 -> String.format(Locale.US, "%.1fT", value / 1e12)
    value >= 1e9 -> String.format(Locale.US, "%.1fB", value / 1e9)
    value >= 1e6 -> String.format(Locale.US, "%.1fM", value / 1e6)
    else -> String.format(Locale.US, "%.0f", value)
}
