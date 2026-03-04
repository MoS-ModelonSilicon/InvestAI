package com.investai.app.ui.invest

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.investai.app.navigation.Screen
import com.investai.app.ui.theme.*

/**
 * Invest Hub: 2-column grid of feature cards.
 * Each card links to a discovery/research tool.
 */

private data class InvestFeature(
    val screen: Screen,
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
)

private val investFeatures = listOf(
    InvestFeature(Screen.Screener, "Screener", "280+ stocks & ETFs", Icons.Filled.ManageSearch),
    InvestFeature(Screen.Recommendations, "For You", "Personal picks", Icons.Filled.AutoAwesome),
    InvestFeature(Screen.AutoPilot, "AutoPilot", "AI portfolios", Icons.Filled.SmartToy),
    InvestFeature(Screen.ValueScanner, "Value Scanner", "Graham method", Icons.Filled.QueryStats),
    InvestFeature(Screen.SmartAdvisor, "Smart Advisor", "Long-term picks", Icons.Filled.Psychology),
    InvestFeature(Screen.TradingAdvisor, "Trading Advisor", "Short-term signals", Icons.Filled.TrendingUp),
    InvestFeature(Screen.ILFunds, "IL Funds", "481 funds", Icons.Filled.AccountBalance),
    InvestFeature(Screen.Comparison, "Compare", "Side by side", Icons.Filled.CompareArrows),
)

@Composable
fun InvestScreen(
    onNavigate: (Screen) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        // Header
        Text(
            text = "Invest",
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = OnSurface,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp),
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(investFeatures) { feature ->
                InvestFeatureCard(
                    feature = feature,
                    onClick = { onNavigate(feature.screen) },
                )
            }
        }
    }
}

@Composable
private fun InvestFeatureCard(
    feature: InvestFeature,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1.1f)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(
                imageVector = feature.icon,
                contentDescription = null,
                tint = Primary,
                modifier = Modifier.size(32.dp),
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = feature.title,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                color = OnSurface,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = feature.subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = OnSurfaceVariant,
            )
        }
    }
}
