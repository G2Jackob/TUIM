package com.g2jackob.tuim.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import com.g2jackob.tuim.data.local.ShoppingItemEntity
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.ListWebSocket
import com.g2jackob.tuim.ui.TuimViewModel

private val itemUnits = listOf(
    "szt" to "szt.",
    "kg" to "kg",
    "g" to "g",
    "l" to "l",
    "ml" to "ml",
    "opak" to "opak."
)

@Composable
fun DetailScreen(
    viewModel: TuimViewModel,
    listId: String,
    tokenStore: TokenStore,
    onBack: () -> Unit
) {
    val items by viewModel.items(listId).collectAsState(initial = emptyList())
    val lists by viewModel.lists.collectAsState(initial = emptyList())
    val message by viewModel.message.collectAsState()
    val listTotal by viewModel.listTotal.collectAsState()
    val exchangeRate by viewModel.exchangeRate.collectAsState()
    val currentUser by viewModel.currentUser.collectAsState()
    val members by viewModel.members.collectAsState()
    val inviteCode by viewModel.inviteCode.collectAsState()
    val list = lists.firstOrNull { it.id == listId }
    val isArchived = list?.isArchived == true
    val isOwner = list?.role == "owner"

    var showProductEditor by remember { mutableStateOf(false) }
    var editingItem by remember { mutableStateOf<ShoppingItemEntity?>(null) }
    var name by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("1") }
    var unit by remember { mutableStateOf("szt") }
    var category by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var estimatedPrice by remember { mutableStateOf("") }
    var unitMenuExpanded by remember { mutableStateOf(false) }
    var currency by remember { mutableStateOf("EUR") }
    var showMembers by remember { mutableStateOf(false) }
    var memberIdentifier by remember { mutableStateOf("") }

    LaunchedEffect(listId) {
        viewModel.syncList(listId)
    }

    DisposableEffect(listId) {
        val socket = ListWebSocket(tokenStore) { viewModel.syncList(listId) }
        socket.connect(listId)
        onDispose { socket.disconnect() }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Wstecz")
            }
            Text(list?.name ?: "Lista zakupów", modifier = Modifier.weight(1f))
            TextButton(onClick = {
                viewModel.loadMembers(listId)
                showMembers = true
            }) {
                Text("Członkowie")
            }
            if (!isArchived) {
                TextButton(onClick = {
                    editingItem = null
                    name = ""
                    quantity = "1"
                    unit = "szt"
                    category = ""
                    note = ""
                    estimatedPrice = ""
                    showProductEditor = true
                }) { Text("Dodaj") }
            }
        }
        if (isArchived) Text("Lista zarchiwizowana — tylko do odczytu")
        if (message.isNotBlank()) Text(message)

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = currency,
                onValueChange = { currency = it.uppercase() },
                label = { Text("Waluta") },
                modifier = Modifier.weight(1f)
            )
            TextButton(onClick = { viewModel.loadListTotal(listId, currency) }) {
                Text("Suma")
            }
            TextButton(onClick = { viewModel.loadExchangeRate("PLN", currency) }) {
                Text("Kurs")
            }
        }
        listTotal?.let { total ->
            val converted = total.converted
            Text(
                if (converted != null) {
                    "Suma: ${converted.total} ${converted.currency}" +
                        if (converted.stale) " (kurs z pamięci podręcznej)" else ""
                } else {
                    "Suma: ${total.total} ${total.currency}"
                },
                modifier = Modifier.padding(vertical = 4.dp)
            )
            converted?.let {
                Text("Kurs: 1 ${total.currency} = ${it.rate} ${it.currency}")
            }
        }
        exchangeRate?.let { rate ->
            Text(
                "1 ${rate.fromCurrency} = ${rate.rate} ${rate.toCurrency}" +
                    (rate.rateDate?.let { " · $it" } ?: "") +
                    if (rate.stale) " (kurs z pamięci podręcznej)" else ""
            )
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
                            enabled = !isArchived,
                            onCheckedChange = {
                                viewModel.setPurchased(listId, item.id, it)
                            }
                        )
                        Column(modifier = Modifier.weight(1f)) {
                            Text(item.name)
                            Text("${item.quantity} ${item.unit}")
                            item.estimatedPrice?.let { Text("Cena: $it") }
                            item.reservedBy?.let { Text("Zarezerwowane: $it") }
                        }
                        if (!isArchived) {
                            TextButton(
                                onClick = {
                                    viewModel.setReserved(listId, item.id, item.reservedBy == null)
                                }
                            ) {
                                Text(if (item.reservedBy == null) "Rezerwuj" else "Zwolnij")
                            }
                            IconButton(onClick = {
                                editingItem = item
                                name = item.name
                                quantity = item.quantity.toString()
                                unit = itemUnits.firstOrNull {
                                    it.first == item.unit || it.second == item.unit
                                }?.first ?: "szt"
                                category = item.category
                                note = item.note
                                estimatedPrice = item.estimatedPrice?.toString().orEmpty()
                                showProductEditor = true
                            }) {
                                Icon(Icons.Default.Edit, contentDescription = "Edytuj produkt")
                            }
                            IconButton(onClick = { viewModel.deleteItem(listId, item.id) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Usuń produkt")
                            }
                        }
                    }
                }
            }
        }
    }

    if (showProductEditor) {
        AlertDialog(
            onDismissRequest = { showProductEditor = false },
            title = { Text(if (editingItem == null) "Nowy produkt" else "Edytuj produkt") },
            text = {
                Column {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Nazwa") }
                    )
                    OutlinedTextField(
                        value = quantity,
                        onValueChange = { quantity = it },
                        label = { Text("Ilość") }
                    )
                    UnitSelector(
                        value = unit,
                        expanded = unitMenuExpanded,
                        onExpandedChange = { unitMenuExpanded = it },
                        onSelect = { unit = it }
                    )
                    OutlinedTextField(
                        value = category,
                        onValueChange = { category = it },
                        label = { Text("Kategoria") }
                    )
                    OutlinedTextField(
                        value = estimatedPrice,
                        onValueChange = { estimatedPrice = it },
                        label = { Text("Cena za jednostkę (opcjonalnie)") }
                    )
                    OutlinedTextField(
                        value = note,
                        onValueChange = { note = it },
                        label = { Text("Notatka") }
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val item = editingItem
                    if (item == null) {
                        viewModel.createItem(
                            listId,
                            name,
                            quantity,
                            unit,
                            category,
                            note,
                            estimatedPrice
                        )
                    } else {
                        viewModel.updateItem(
                            listId,
                            item.id,
                            name,
                            quantity,
                            unit,
                            category,
                            note,
                            estimatedPrice
                        )
                    }
                    showProductEditor = false
                }) {
                    Text(if (editingItem == null) "Dodaj" else "Zapisz")
                }
            },
            dismissButton = {
                TextButton(onClick = { showProductEditor = false }) { Text("Anuluj") }
            }
        )
    }

    if (showMembers) {
        AlertDialog(
            onDismissRequest = { showMembers = false },
            title = { Text("Członkowie listy") },
            text = {
                Column(modifier = Modifier.heightIn(max = 360.dp)) {
                    LazyColumn(modifier = Modifier.weight(1f, fill = false)) {
                        items(members, key = { it.user.id.orEmpty() }) { member ->
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Text(
                                    "${member.user.label()} · " +
                                        if (member.role == "owner") "Właściciel" else "Członek",
                                    modifier = Modifier.weight(1f)
                                )
                                if (isOwner && member.role != "owner") {
                                    IconButton(onClick = {
                                        member.user.id?.let {
                                            viewModel.removeMember(listId, it)
                                        }
                                    }) {
                                        Icon(
                                            Icons.Default.Delete,
                                            contentDescription = "Usuń członka"
                                        )
                                    }
                                } else if (
                                    !isOwner &&
                                    member.role == "member" &&
                                    member.user.id == currentUser?.id
                                ) {
                                    TextButton(onClick = {
                                        member.user.id?.let {
                                            viewModel.removeMember(listId, it)
                                        }
                                        showMembers = false
                                        onBack()
                                    }) {
                                        Text("Opuść")
                                    }
                                }
                            }
                        }
                    }
                    if (isOwner) {
                        OutlinedTextField(
                            value = memberIdentifier,
                            onValueChange = { memberIdentifier = it },
                            label = { Text("E-mail lub nazwa użytkownika") }
                        )
                        TextButton(onClick = {
                            viewModel.addMember(listId, memberIdentifier)
                            memberIdentifier = ""
                        }) { Text("Dodaj członka") }
                        TextButton(onClick = { viewModel.createInvite(listId) }) {
                            Text("Utwórz kod zaproszenia")
                        }
                        inviteCode?.let { Text("Kod zaproszenia: $it") }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showMembers = false }) { Text("Gotowe") }
            }
        )
    }
}

@Composable
private fun UnitSelector(
    value: String,
    expanded: Boolean,
    onExpandedChange: (Boolean) -> Unit,
    onSelect: (String) -> Unit
) {
    Box(modifier = Modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = itemUnits.first { it.first == value }.second,
            onValueChange = {},
            readOnly = true,
            label = { Text("Jednostka") },
            modifier = Modifier.fillMaxWidth().clickable { onExpandedChange(true) }
        )
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { onExpandedChange(false) }
        ) {
            itemUnits.forEach { (unit, label) ->
                DropdownMenuItem(
                    text = { Text(label) },
                    onClick = {
                        onSelect(unit)
                        onExpandedChange(false)
                    }
                )
            }
        }
    }
}
