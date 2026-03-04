package com.investai.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.investai.app.ui.theme.*

/**
 * Signal badge: Buy / Hold / Sell / Strong Buy pill with color.
 */
@Composable
fun SignalBadge(
    signal: String,
    modifier: Modifier = Modifier,
) {
    val (bg, fg) = when (signal.lowercase()) {
        "strong buy", "buy" -> GainBg to Gain
        "sell", "strong sell" -> LossBg to Loss
        "hold", "watch" -> Pair(
            androidx.compose.ui.graphics.Color(0x1AEAB308),
            Caution,
        )
        else -> BlueBg to BlueInfo
    }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bg)
            .padding(horizontal = 8.dp, vertical = 3.dp),
    ) {
        Text(
            text = signal,
            color = fg,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}
