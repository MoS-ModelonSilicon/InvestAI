package com.investai.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * InvestAI Material 3 theme with dark/light support.
 */
private val InvestAIDarkColorScheme = darkColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = PrimaryHover,
    secondary = BlueInfo,
    background = Surface,
    surface = Surface,
    surfaceVariant = SurfaceContainer,
    surfaceContainerLow = SurfaceContainerLowest,
    surfaceContainer = SurfaceContainer,
    surfaceContainerHigh = SurfaceContainerHigh,
    onBackground = OnSurface,
    onSurface = OnSurface,
    onSurfaceVariant = OnSurfaceVariant,
    outline = OutlineVariant,
    outlineVariant = OutlineVariant,
    error = Loss,
)

private val InvestAILightColorScheme = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    primaryContainer = Color(0xFFE8E8FF),
    secondary = BlueInfo,
    background = Color(0xFFF8F9FA),
    surface = Color(0xFFFFFFFF),
    surfaceVariant = Color(0xFFF1F3F5),
    surfaceContainerLow = Color(0xFFF8F9FA),
    surfaceContainer = Color(0xFFF1F3F5),
    surfaceContainerHigh = Color(0xFFE9ECEF),
    onBackground = Color(0xFF1A1A2E),
    onSurface = Color(0xFF1A1A2E),
    onSurfaceVariant = Color(0xFF6C757D),
    outline = Color(0xFFDEE2E6),
    outlineVariant = Color(0xFFDEE2E6),
    error = Loss,
)

@Composable
fun InvestAITheme(
    isDarkTheme: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = if (isDarkTheme) InvestAIDarkColorScheme else InvestAILightColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            window.navigationBarColor = colorScheme.surfaceContainerLow.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !isDarkTheme
                isAppearanceLightNavigationBars = !isDarkTheme
            }
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = InvestAITypography,
        content = content,
    )
}
