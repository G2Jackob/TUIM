package com.g2jackob.tuim.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.ListWebSocket
import com.g2jackob.tuim.ui.TuimViewModel

@Composable
fun DetailScreen(
    viewModel: TuimViewModel,
    listId: String,
    tokenStore: TokenStore,
    onBack: () -> Unit
) {
    val items by viewModel.items(listId).collectAsState(initial = emptyList())
    val message by viewModel.message.collectAsState()
    val externalResults by viewModel.externalResults.collectAsState()
    var showCreate by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("1") }
    var unit by remember { mutableStateOf("szt.") }
    var searchQuery by remember { mutableStateOf("") }

    LaunchedEffect(listId) {
        viewModel.sync()
    }

    DisposableEffect(listId) {
        val socket = ListWebSocket(tokenStore) { viewModel.sync() }
        socket.connect(listId)
        onDispose { socket.disconnect() }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Wstecz")
            }
            Text("Lista zakupów", modifier = Modifier.weight(1f))
            TextButton(onClick = { showCreate = true }) { Text("Dodaj") }
        }
        if (message.isNotBlank()) Text(message)

        Row(modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                label = { Text("Szukaj Open Food Facts") },
                modifier = Modifier.weight(1f)
            )
            TextButton(onClick = { viewModel.search(searchQuery) }) { Text("Szukaj") }
        }
        externalResults.forEach {
            TextButton(onClick = {
                name = it.name
                showCreate = true
            }) { Text(it.name) }
        }

        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(items, key = { it.id }) { item ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(
                            checked = item.purchased,
                            onCheckedChange = {
                                viewModel.setPurchased(listId, item.id, it)
                            }
                        )
                        Column(modifier = Modifier.weight(1f)) {
                            Text(item.name)
                            Text("${item.quantity} ${item.unit}")
                            item.reservedBy?.let { Text("Zarezerwowane: $it") }
                        }
                        IconButton(onClick = { viewModel.deleteItem(listId, item.id) }) {
                            Icon(Icons.Default.Delete, contentDescription = "Usuń")
                        }
                    }
                }
            }
        }
    }

    if (showCreate) {
        AlertDialog(
            onDismissRequest = { showCreate = false },
            title = { Text("Nowy produkt") },
            text = {
                Column {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nazwa") })
                    OutlinedTextField(value = quantity, onValueChange = { quantity = it }, label = { Text("Ilość") })
                    OutlinedTextField(value = unit, onValueChange = { unit = it }, label = { Text("Jednostka") })
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.createItem(listId, name, quantity, unit, "", "")
                    showCreate = false
                    name = ""
                    quantity = "1"
                }) { Text("Dodaj") }
            },
            dismissButton = {
                TextButton(onClick = { showCreate = false }) { Text("Anuluj") }
            }
        )
    }
}
