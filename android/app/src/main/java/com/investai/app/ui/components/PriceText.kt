package com.investai.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.investai.app.ui.theme.Gain
import com.investai.app.ui.theme.Loss
import com.investai.app.ui.theme.OnSurface
import java.text.NumberFormat
import java.util.Locale

/**
 * Formats a price with green/red coloring based on sign.
 * Core building block — used everywhere in the app.
 */
@Composable
fun PriceText(
    value: Double,
    modifier: Modifier = Modifier,
    showSign: Boolean = true,
    isPercent: Boolean = false,
    fontSize: Int = 16,
    fontWeight: FontWeight = FontWeight.Medium,
) {
    val color = when {
        value > 0 -> Gain
        value < 0 -> Loss
        else -> OnSurface
    }

    val formatted = buildString {
        if (showSign && value > 0) append("+")
        if (isPercent) {
            append(String.format(Locale.US, "%.2f%%", value))
        } else {
            append(NumberFormat.getCurrencyInstance(Locale.US).format(value))
        }
    }

    Text(
        text = formatted,
        color = color,
        fontSize = fontSize.sp,
        fontWeight = fontWeight,
        fontFamily = FontFamily.Monospace,
        modifier = modifier,
    )
}

/**
 * Large hero price for portfolio value display.
 */
@Composable
fun HeroPrice(
    value: Double,
    modifier: Modifier = Modifier,
) {
    Text(
        text = NumberFormat.getCurrencyInstance(Locale.US).format(value),
        style = MaterialTheme.typography.displayLarge,
        color = OnSurface,
        modifier = modifier,
    )
}

/**
 * Change percentage pill (e.g., ▲ +2.4%)
 */
@Composable
fun ChangeBadge(
    changePct: Double,
    modifier: Modifier = Modifier,
) {
    val isPositive = changePct >= 0
    val bgColor = if (isPositive) com.investai.app.ui.theme.GainBg else com.investai.app.ui.theme.LossBg
    val textColor = if (isPositive) Gain else Loss
    val arrow = if (isPositive) "▲" else "▼"

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            text = "$arrow ${String.format(Locale.US, "%.2f%%", changePct)}",
            color = textColor,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            fontFamily = FontFamily.Monospace,
        )
    }
}
