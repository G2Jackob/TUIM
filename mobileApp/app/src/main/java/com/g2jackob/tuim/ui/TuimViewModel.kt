package com.g2jackob.tuim.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.g2jackob.tuim.data.network.ExternalProductDto
import com.g2jackob.tuim.data.repository.ShoppingRepository
import com.g2jackob.tuim.domain.Validation
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class TuimViewModel(private val repository: ShoppingRepository) : ViewModel() {
    val isLoggedIn = MutableStateFlow(repository.isLoggedIn())
    val lists = repository.lists
    val message = MutableStateFlow("")
    val externalResults = MutableStateFlow<List<ExternalProductDto>>(emptyList())
    val isBusy = MutableStateFlow(false)

    fun items(listId: String) = repository.items(listId)

    fun login(username: String, password: String) {
        if (username.isBlank() || password.isBlank()) {
            message.value = "Podaj nazwę użytkownika i hasło"
            return
        }
        viewModelScope.launch {
            isBusy.value = true
            repository.login(username, password).onSuccess {
                isLoggedIn.value = true
                message.value = ""
            }.onFailure {
                message.value = it.message ?: "Nie udało się zalogować"
            }
            isBusy.value = false
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            isLoggedIn.value = false
        }
    }

    fun sync() {
        viewModelScope.launch {
            isBusy.value = true
            repository.syncLists().onSuccess {
                message.value = ""
            }.onFailure {
                message.value = it.message ?: "Nie udało się pobrać danych"
            }
            isBusy.value = false
        }
    }

    fun createList(name: String, description: String, currency: String) {
        Validation.validateName(name)?.let {
            message.value = it
            return
        }
        viewModelScope.launch {
            repository.createList(name.trim(), description.trim(), currency).onFailure {
                message.value = it.message ?: "Nie udało się utworzyć listy"
            }
        }
    }

    fun createItem(
        listId: String,
        name: String,
        quantityText: String,
        unit: String,
        category: String,
        note: String
    ) {
        Validation.validateName(name)?.let {
            message.value = it
            return
        }
        val quantity = quantityText.replace(',', '.').toDoubleOrNull()
        Validation.validateQuantity(quantity)?.let {
            message.value = it
            return
        }
        viewModelScope.launch {
            repository.createItem(
                listId,
                name.trim(),
                quantity ?: 1.0,
                unit,
                category,
                note,
                null
            ).onFailure {
                message.value = it.message ?: "Nie udało się dodać produktu"
            }
        }
    }

    fun setPurchased(listId: String, itemId: String, purchased: Boolean) {
        viewModelScope.launch {
            repository.setPurchased(listId, itemId, purchased).onFailure {
                message.value = it.message ?: "Nie udało się zmienić statusu"
            }
        }
    }

    fun deleteItem(listId: String, itemId: String) {
        viewModelScope.launch {
            repository.deleteItem(listId, itemId).onFailure {
                message.value = it.message ?: "Nie udało się usunąć produktu"
            }
        }
    }

    fun search(query: String) {
        viewModelScope.launch {
            repository.searchProducts(query).onSuccess {
                externalResults.value = it
            }.onFailure {
                message.value = it.message ?: "Zewnętrzne API jest niedostępne"
                externalResults.value = emptyList()
            }
        }
    }

    fun clearMessage() {
        message.value = ""
    }

    class Factory(private val repository: ShoppingRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            TuimViewModel(repository) as T
    }
}
