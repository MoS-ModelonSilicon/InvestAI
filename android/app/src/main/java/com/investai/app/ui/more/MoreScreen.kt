package com.investai.app.ui.more

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.investai.app.navigation.Screen
import com.investai.app.ui.auth.AuthViewModel
import com.investai.app.ui.theme.*

private data class MoreItem(
    val screen: Screen,
    val title: String,
    val icon: ImageVector,
    val subtitle: String? = null,
)

private val moreItems = listOf(
    MoreItem(Screen.RiskProfile, "Risk Profile", Icons.Filled.PersonSearch, "Your investment style"),
    MoreItem(Screen.Transactions, "Transactions", Icons.Filled.Receipt, "Income & expenses"),
    MoreItem(Screen.Budgets, "Budgets", Icons.Filled.PieChart, "Monthly limits"),
    MoreItem(Screen.News, "Market News", Icons.Filled.Newspaper, "Latest headlines"),
    MoreItem(Screen.Calendar, "Calendar", Icons.Filled.Event, "Earnings & events"),
    MoreItem(Screen.PicksTracker, "Picks Tracker", Icons.Filled.CheckBox, "Discord backtests"),
    MoreItem(Screen.Education, "Learn to Invest", Icons.Filled.School, "Courses & guides"),
)

@Composable
fun MoreScreen(
    onNavigate: (Screen) -> Unit,
    onLogout: () -> Unit,
    authViewModel: AuthViewModel = hiltViewModel(),
    moreViewModel: MoreViewModel = hiltViewModel(),
) {
    val isDarkMode by moreViewModel.isDarkMode.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 12.dp),
    ) {
        item {
            Text(
                text = "More",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = OnSurface,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
            )
        }

        // Theme toggle
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    imageVector = if (isDarkMode) Icons.Filled.DarkMode else Icons.Filled.LightMode,
                    contentDescription = null,
                    tint = OnSurfaceVariant,
                    modifier = Modifier.size(24.dp),
                )
                Spacer(Modifier.width(16.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "Dark Mode",
                        fontWeight = FontWeight.Medium,
                        fontSize = 15.sp,
                        color = OnSurface,
                    )
                    Text(
                        if (isDarkMode) "Dark theme active" else "Light theme active",
                        style = MaterialTheme.typography.labelSmall,
                        color = OnSurfaceVariant,
                    )
                }
                Switch(
                    checked = isDarkMode,
                    onCheckedChange = { moreViewModel.toggleDarkMode() },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Primary,
                        checkedTrackColor = Primary.copy(alpha = 0.3f),
                    ),
                )
            }
            HorizontalDivider(color = OutlineVariant, modifier = Modifier.padding(horizontal = 16.dp))
        }

        items(moreItems) { item ->
            MoreListItem(
                item = item,
                onClick = { onNavigate(item.screen) },
            )
        }

        // Logout at bottom
        item {
            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = OutlineVariant, modifier = Modifier.padding(horizontal = 16.dp))
            Spacer(Modifier.height(8.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable {
                        authViewModel.logout()
                        onLogout()
                    }
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Logout,
                    contentDescription = "Logout",
                    tint = Loss,
                    modifier = Modifier.size(24.dp),
                )
                Spacer(Modifier.width(16.dp))
                Text(
                    "Logout",
                    color = Loss,
                    fontWeight = FontWeight.Medium,
                    fontSize = 15.sp,
                )
            }
        }

        // Disclaimer
        item {
            Spacer(Modifier.height(24.dp))
            Text(
                text = "InvestAI v1.0.0\nFor educational purposes only. Not financial advice.",
                style = MaterialTheme.typography.labelSmall,
                color = OnSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        }
    }
}

@Composable
private fun MoreListItem(item: MoreItem, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = item.icon,
            contentDescription = null,
            tint = OnSurfaceVariant,
            modifier = Modifier.size(24.dp),
        )
        Spacer(Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = item.title,
                fontWeight = FontWeight.Medium,
                fontSize = 15.sp,
                color = OnSurface,
            )
            if (item.subtitle != null) {
                Text(
                    text = item.subtitle,
                    style = MaterialTheme.typography.labelSmall,
                    color = OnSurfaceVariant,
                )
            }
        }
        Icon(
            Icons.Filled.ChevronRight,
            contentDescription = null,
            tint = OnSurfaceVariant,
            modifier = Modifier.size(20.dp),
        )
    }
}
