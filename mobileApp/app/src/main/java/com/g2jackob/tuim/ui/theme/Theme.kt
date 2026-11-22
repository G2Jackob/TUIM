package com.g2jackob.tuim.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val colors = lightColorScheme(
    primary = Color(0xFF6750A4),
    secondary = Color(0xFF625B71),
    tertiary = Color(0xFF7D5260)
)

@Composable
fun TuimTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = colors,
        content = content
    )
}
