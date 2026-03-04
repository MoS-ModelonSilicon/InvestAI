package com.investai.app.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.investai.app.ui.theme.SurfaceContainer
import com.investai.app.ui.theme.SurfaceContainerHigh

/**
 * Shimmer skeleton placeholder — replaces spinners per UX strategy.
 * Shows the shape of data before it loads.
 */
@Composable
fun SkeletonLoader(
    modifier: Modifier = Modifier,
    width: Dp = 0.dp,
    height: Dp = 20.dp,
) {
    val shimmerColors = listOf(
        SurfaceContainer,
        SurfaceContainerHigh,
        SurfaceContainer,
    )

    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "shimmer_translate",
    )

    val brush = Brush.linearGradient(
        colors = shimmerColors,
        start = Offset.Zero,
        end = Offset(x = translateAnim.value, y = translateAnim.value),
    )

    val mod = modifier
        .clip(RoundedCornerShape(8.dp))
        .background(brush)
        .height(height)

    Box(modifier = if (width > 0.dp) mod.width(width) else mod.fillMaxWidth())
}

/**
 * Card-shaped skeleton for loading states.
 */
@Composable
fun SkeletonCard(
    modifier: Modifier = Modifier,
    height: Dp = 100.dp,
) {
    SkeletonLoader(
        modifier = modifier.fillMaxWidth(),
        height = height,
    )
}

/**
 * Stock list item skeleton.
 */
@Composable
fun StockItemSkeleton(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(SurfaceContainer)
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column {
            SkeletonLoader(width = 60.dp, height = 16.dp)
            Spacer(Modifier.height(6.dp))
            SkeletonLoader(width = 120.dp, height = 12.dp)
        }
        Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
            SkeletonLoader(width = 70.dp, height = 16.dp)
            Spacer(Modifier.height(6.dp))
            SkeletonLoader(width = 50.dp, height = 12.dp)
        }
    }
}
