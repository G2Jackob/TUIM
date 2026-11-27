package com.g2jackob.tuim.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.g2jackob.tuim.ui.TuimViewModel

@Composable
fun LoginScreen(
    viewModel: TuimViewModel,
    onAuthorize: () -> Unit,
    onLoggedIn: () -> Unit
) {
    val loggedIn by viewModel.isLoggedIn.collectAsState()
    val busy by viewModel.isBusy.collectAsState()
    val message by viewModel.message.collectAsState()

    LaunchedEffect(loggedIn) {
        if (loggedIn) onLoggedIn()
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("TUIM - Logowanie")
        Text(
            "Zaloguj się kontem Keycloak albo uruchom wersję demonstracyjną.",
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp)
        )
        if (message.isNotBlank()) {
            Text(message, modifier = Modifier.padding(bottom = 8.dp))
        }
        if (busy) {
            CircularProgressIndicator()
        } else {
            Button(
                onClick = onAuthorize,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Zaloguj przez Keycloak")
            }
            OutlinedButton(
                onClick = viewModel::loginDemo,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
            ) {
                Text("Tryb demo (bez backendu)")
            }
        }
    }
}
