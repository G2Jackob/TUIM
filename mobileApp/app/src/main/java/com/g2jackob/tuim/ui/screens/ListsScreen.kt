package com.g2jackob.tuim.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.g2jackob.tuim.ui.TuimViewModel

@Composable
fun ListsScreen(
    viewModel: TuimViewModel,
    onOpenList: (String) -> Unit,
    onLogout: () -> Unit
) {
    val lists by viewModel.lists.collectAsState(initial = emptyList())
    var showCreate by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    val message by viewModel.message.collectAsState()

    LaunchedEffect(Unit) { viewModel.sync() }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(modifier = Modifier.fillMaxWidth()) {
            Text("Moje listy zakupów", modifier = Modifier.weight(1f).padding(top = 12.dp))
            IconButton(onClick = { showCreate = true }) {
                Icon(Icons.Default.Add, contentDescription = "Dodaj listę")
            }
            TextButton(onClick = onLogout) { Text("Wyloguj") }
        }
        if (message.isNotBlank()) Text(message)
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(lists, key = { it.id }) { list ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 6.dp)
                        .clickable { onOpenList(list.id) }
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(list.name)
                        if (list.description.isNotBlank()) Text(list.description)
                        Text(list.currency)
                    }
                }
            }
        }
    }

    if (showCreate) {
        AlertDialog(
            onDismissRequest = { showCreate = false },
            title = { Text("Nowa lista") },
            text = {
                Column {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nazwa") })
                    OutlinedTextField(
                        value = description,
                        onValueChange = { description = it },
                        label = { Text("Opis") }
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.createList(name, description, "PLN")
                    showCreate = false
                    name = ""
                    description = ""
                }) { Text("Utwórz") }
            },
            dismissButton = {
                TextButton(onClick = { showCreate = false }) { Text("Anuluj") }
            }
        )
    }
}
