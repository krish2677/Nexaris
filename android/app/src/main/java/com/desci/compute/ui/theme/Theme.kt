package com.desci.compute.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFFCDFF00),
    onPrimary = Color(0xFF1A1A00),
    primaryContainer = Color(0xFF3D4D00),
    onPrimaryContainer = Color(0xFFE8FF80),
    secondary = Color(0xFF8B5CF6),
    onSecondary = Color(0xFF1E0A4D),
    secondaryContainer = Color(0xFF3B2570),
    onSecondaryContainer = Color(0xFFD5C4FF),
    tertiary = Color(0xFF34D399),
    onTertiary = Color(0xFF003824),
    tertiaryContainer = Color(0xFF005236),
    onTertiaryContainer = Color(0xFF96F7CB),
    background = Color(0xFF0A0A14),
    onBackground = Color(0xFFF0F0F0),
    surface = Color(0xFF12101E),
    onSurface = Color(0xFFF0F0F0),
    surfaceVariant = Color(0xFF2A2640),
    onSurfaceVariant = Color(0xFF9A95B0),
    error = Color(0xFFF87171),
    onError = Color(0xFF690005),
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF5A7300),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD5FF80),
    onPrimaryContainer = Color(0xFF1A2200),
    secondary = Color(0xFF6D42D1),
    onSecondary = Color.White,
    background = Color(0xFFF8F8F0),
    onBackground = Color(0xFF14141E),
    surface = Color.White,
    onSurface = Color(0xFF14141E),
)

@Composable
fun DeSciTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content,
    )
}
