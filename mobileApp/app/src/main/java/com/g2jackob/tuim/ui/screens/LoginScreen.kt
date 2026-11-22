package com.g2jackob.tuim.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.g2jackob.tuim.ui.TuimViewModel

@Composable
fun LoginScreen(viewModel: TuimViewModel, onLoggedIn: () -> Unit) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
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
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("Nazwa użytkownika") },
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp)
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Hasło") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
        )
        if (message.isNotBlank()) {
            Text(message, modifier = Modifier.padding(top = 8.dp))
        }
        if (busy) {
            CircularProgressIndicator(modifier = Modifier.padding(top = 16.dp))
        } else {
            Button(
                onClick = { viewModel.login(username, password) },
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp)
            ) {
                Text("Zaloguj")
            }
        }
    }
}
