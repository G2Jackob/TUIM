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
import androidx.compose.material.icons.filled.Archive
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Unarchive
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import com.g2jackob.tuim.data.local.ShoppingListEntity
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.UserWebSocket
import com.g2jackob.tuim.ui.TuimViewModel

@Composable
fun ListsScreen(
    viewModel: TuimViewModel,
    tokenStore: TokenStore,
    onOpenList: (String) -> Unit,
    onLogout: () -> Unit
) {
    val lists by viewModel.lists.collectAsState(initial = emptyList())
    val message by viewModel.message.collectAsState()
    val currentUser by viewModel.currentUser.collectAsState()
    var showListEditor by remember { mutableStateOf(false) }
    var editingList by remember { mutableStateOf<ShoppingListEntity?>(null) }
    var listName by remember { mutableStateOf("") }
    var listDescription by remember { mutableStateOf("") }
    var listCurrency by remember { mutableStateOf("PLN") }
    var showAcceptInvite by remember { mutableStateOf(false) }
    var inviteCode by remember { mutableStateOf("") }
    var pendingDelete by remember { mutableStateOf<ShoppingListEntity?>(null) }

    LaunchedEffect(Unit) { viewModel.sync() }

    DisposableEffect(tokenStore) {
        val socket = UserWebSocket(tokenStore) { viewModel.sync() }
        socket.connect()
        onDispose { socket.disconnect() }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f).padding(top = 8.dp)) {
                    Text("Moje listy zakupów")
                    currentUser?.let { user ->
                        Text(user.displayName?.takeIf(String::isNotBlank) ?: user.username)
                    }
                }
                TextButton(onClick = onLogout) { Text("Wyloguj") }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = viewModel::sync) {
                    Icon(Icons.Default.Refresh, contentDescription = "Odśwież listy")
                }
                TextButton(onClick = { showAcceptInvite = true }) { Text("Dołącz kodem") }
                TextButton(onClick = {
                    editingList = null
                    listName = ""
                    listDescription = ""
                    listCurrency = "PLN"
                    showListEditor = true
                }) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Text("Nowa lista")
                }
            }
        }
        if (message.isNotBlank()) Text(message)
        LazyColumn(modifier = Modifier.fillMaxSize()) {
            items(lists, key = { it.id }) { list ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Row(modifier = Modifier.padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp)) {
                        Column(
                            modifier = Modifier
                                .weight(1f)
                                .clickable { onOpenList(list.id) }
                                .padding(vertical = 8.dp)
                        ) {
                            Text(list.name)
                            if (list.description.isNotBlank()) Text(list.description)
                            Text(
                                "${list.currency} · ${if (list.role == "owner") "Właściciel" else "Członek"}" +
                                    if (list.isArchived) " · Zarchiwizowana" else ""
                            )
                            Text("${list.purchasedCount}/${list.itemsCount} kupionych")
                        }
                        if (list.role == "owner") {
                            IconButton(onClick = {
                                editingList = list
                                listName = list.name
                                listDescription = list.description
                                listCurrency = list.currency
                                showListEditor = true
                            }) {
                                Icon(Icons.Default.Edit, contentDescription = "Edytuj listę")
                            }
                            IconButton(onClick = {
                                viewModel.setListArchived(list.id, !list.isArchived)
                            }) {
                                Icon(
                                    if (list.isArchived) Icons.Default.Unarchive else Icons.Default.Archive,
                                    contentDescription = if (list.isArchived) "Przywróć listę" else "Archiwizuj listę"
                                )
                            }
                            IconButton(onClick = { pendingDelete = list }) {
                                Icon(Icons.Default.Delete, contentDescription = "Usuń listę")
                            }
                        }
                    }
                }
            }
        }
    }

    if (showListEditor) {
        AlertDialog(
            onDismissRequest = { showListEditor = false },
            title = { Text(if (editingList == null) "Nowa lista" else "Edytuj listę") },
            text = {
                Column {
                    OutlinedTextField(
                        value = listName,
                        onValueChange = { listName = it },
                        label = { Text("Nazwa") }
                    )
                    OutlinedTextField(
                        value = listDescription,
                        onValueChange = { listDescription = it },
                        label = { Text("Opis") }
                    )
                    OutlinedTextField(
                        value = listCurrency,
                        onValueChange = { listCurrency = it.uppercase() },
                        label = { Text("Waluta (np. PLN)") }
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val list = editingList
                    if (list == null) {
                        viewModel.createList(listName, listDescription, listCurrency)
                    } else {
                        viewModel.updateList(list.id, listName, listDescription, listCurrency)
                    }
                    showListEditor = false
                }) {
                    Text(if (editingList == null) "Utwórz" else "Zapisz")
                }
            },
            dismissButton = {
                TextButton(onClick = { showListEditor = false }) { Text("Anuluj") }
            }
        )
    }

    if (showAcceptInvite) {
        AlertDialog(
            onDismissRequest = { showAcceptInvite = false },
            title = { Text("Dołącz do listy") },
            text = {
                OutlinedTextField(
                    value = inviteCode,
                    onValueChange = { inviteCode = it },
                    label = { Text("Kod zaproszenia") }
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.acceptInvite(inviteCode)
                    showAcceptInvite = false
                    inviteCode = ""
                }) { Text("Dołącz") }
            },
            dismissButton = {
                TextButton(onClick = { showAcceptInvite = false }) { Text("Anuluj") }
            }
        )
    }

    pendingDelete?.let { list ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text("Usunąć listę?") },
            text = { Text("Lista „${list.name}” i jej produkty zostaną usunięte.") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteList(list.id)
                    pendingDelete = null
                }) { Text("Usuń") }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) { Text("Anuluj") }
            }
        )
    }
}
