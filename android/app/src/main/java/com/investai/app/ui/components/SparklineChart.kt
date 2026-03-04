package com.investai.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.investai.app.ui.theme.Gain
import com.investai.app.ui.theme.Loss

/**
 * Tiny inline sparkline chart for list items.
 * Uses Canvas composable for high performance.
 */
@Composable
fun SparklineChart(
    data: List<Double>,
    modifier: Modifier = Modifier
        .width(60.dp)
        .height(24.dp),
    lineColor: Color? = null,
    strokeWidth: Float = 1.5f,
) {
    if (data.size < 2) return

    val color = lineColor ?: if (data.last() >= data.first()) Gain else Loss
    val min = data.min()
    val max = data.max()
    val range = (max - min).coerceAtLeast(0.001)

    Canvas(modifier = modifier) {
        val stepX = size.width / (data.size - 1)
        val path = Path()

        data.forEachIndexed { i, value ->
            val x = i * stepX
            val y = size.height - ((value - min) / range * size.height).toFloat()
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }

        drawPath(
            path = path,
            color = color,
            style = Stroke(width = strokeWidth),
        )
    }
}
