package com.investai.app.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.investai.app.ui.theme.*

/**
 * Section header: Title + optional "See All" link + optional count badge.
 * Used on Home screen to separate content sections.
 */
@Composable
fun SectionHeader(
    title: String,
    modifier: Modifier = Modifier,
    count: Int? = null,
    actionText: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.headlineMedium,
            color = OnSurface,
            modifier = Modifier.weight(1f),
        )

        if (count != null) {
            Spacer(Modifier.width(8.dp))
            Text(
                text = "$count",
                style = MaterialTheme.typography.labelSmall,
                color = OnSurfaceVariant,
            )
        }

        if (actionText != null && onAction != null) {
            Spacer(Modifier.width(12.dp))
            TextButton(onClick = onAction) {
                Text(
                    text = actionText,
                    color = Primary,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
    }
}
