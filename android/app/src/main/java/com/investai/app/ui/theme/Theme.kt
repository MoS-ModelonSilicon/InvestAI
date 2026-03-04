package com.investai.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * InvestAI dark-first Material 3 theme.
 * Matches the web app's dark color palette.
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

@Composable
fun InvestAITheme(
    content: @Composable () -> Unit,
) {
    val colorScheme = InvestAIDarkColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            window.navigationBarColor = colorScheme.surfaceContainerLow.toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = false
                isAppearanceLightNavigationBars = false
            }
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = InvestAITypography,
        content = content,
    )
}
