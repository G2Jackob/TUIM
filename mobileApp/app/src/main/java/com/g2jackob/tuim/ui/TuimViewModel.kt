package com.g2jackob.tuim.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import retrofit2.HttpException
import com.g2jackob.tuim.data.repository.ShoppingRepository
import com.g2jackob.tuim.data.network.CurrentUserDto
import com.g2jackob.tuim.data.network.ExchangeRateDto
import com.g2jackob.tuim.data.network.ListMemberDto
import com.g2jackob.tuim.data.network.ListTotalDto
import com.g2jackob.tuim.domain.Validation
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

class TuimViewModel(private val repository: ShoppingRepository) : ViewModel() {
    val isLoggedIn = MutableStateFlow(repository.isLoggedIn())
    val lists = repository.lists
    val message = MutableStateFlow("")
    val listTotal = MutableStateFlow<ListTotalDto?>(null)
    val exchangeRate = MutableStateFlow<ExchangeRateDto?>(null)
    val currentUser = MutableStateFlow<CurrentUserDto?>(null)
    val members = MutableStateFlow<List<ListMemberDto>>(emptyList())
    val inviteCode = MutableStateFlow<String?>(null)
    val isBusy = MutableStateFlow(false)

    fun items(listId: String) = repository.items(listId)

    fun loginDemo() {
        viewModelScope.launch {
            isBusy.value = true
            repository.loginDemo().onSuccess {
                isLoggedIn.value = true
                message.value = ""
            }.onFailure {
                showFailure(it, "Nie udało się uruchomić trybu demo")
            }
            isBusy.value = false
        }
    }

    fun completeLogin(accessToken: String, refreshToken: String?) {
        viewModelScope.launch {
            isBusy.value = true
            repository.completeLogin(accessToken, refreshToken).onSuccess {
                isLoggedIn.value = true
                message.value = ""
            }.onFailure {
                showFailure(it, "Nie udało się zalogować")
            }
            isBusy.value = false
        }
    }

    fun authFailed(reason: String) {
        isBusy.value = false
        message.value = reason
    }

    fun authStarted() {
        isBusy.value = true
        message.value = ""
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
                repository.getCurrentUser().onSuccess {
                    currentUser.value = it
                }.onFailure {
                    showFailure(it, "Nie udało się pobrać profilu")
                }
            }.onFailure {
                showFailure(it, "Nie udało się pobrać danych")
            }
            isBusy.value = false
        }
    }

    fun syncList(listId: String) {
        viewModelScope.launch {
            repository.syncList(listId).onFailure {
                showFailure(it, "Nie udało się odświeżyć listy")
            }
        }
    }

    fun createList(name: String, description: String, currency: String) {
        Validation.validateName(name)?.let {
            message.value = it
            return
        }
        val normalizedCurrency = currency.trim().uppercase()
        if (normalizedCurrency.length != 3 || normalizedCurrency.any { !it.isLetter() }) {
            message.value = "Podaj trzyliterowy kod waluty, np. PLN"
            return
        }
        viewModelScope.launch {
            repository.createList(name.trim(), description.trim(), normalizedCurrency).onFailure {
                showFailure(it, "Nie udało się utworzyć listy")
            }
        }
    }

    fun updateList(listId: String, name: String, description: String, currency: String) {
        Validation.validateName(name)?.let {
            message.value = it
            return
        }
        val normalizedCurrency = currency.trim().uppercase()
        if (normalizedCurrency.length != 3 || normalizedCurrency.any { !it.isLetter() }) {
            message.value = "Podaj trzyliterowy kod waluty, np. PLN"
            return
        }
        viewModelScope.launch {
            repository.updateList(listId, name.trim(), description.trim(), normalizedCurrency)
                .onFailure {
                    showFailure(it, "Nie udało się zmienić listy")
                }
        }
    }

    fun setListArchived(listId: String, archived: Boolean) {
        viewModelScope.launch {
            repository.setListArchived(listId, archived).onFailure {
                showFailure(it, "Nie udało się zmienić archiwizacji listy")
            }
        }
    }

    fun deleteList(listId: String) {
        viewModelScope.launch {
            repository.deleteList(listId).onFailure {
                showFailure(it, "Nie udało się usunąć listy")
            }
        }
    }

    fun loadMembers(listId: String) {
        inviteCode.value = null
        viewModelScope.launch {
            repository.getMembers(listId).onSuccess {
                members.value = it
            }.onFailure {
                showFailure(it, "Nie udało się pobrać członków listy")
            }
        }
    }

    fun addMember(listId: String, identifier: String) {
        if (identifier.isBlank()) {
            message.value = "Podaj e-mail lub nazwę użytkownika"
            return
        }
        viewModelScope.launch {
            repository.addMember(listId, identifier).onSuccess {
                loadMembers(listId)
                message.value = "Dodano członka do listy"
            }.onFailure {
                showFailure(it, "Nie udało się dodać członka")
            }
        }
    }

    fun removeMember(listId: String, userId: String) {
        viewModelScope.launch {
            repository.removeMember(listId, userId).onSuccess {
                loadMembers(listId)
                message.value = "Usunięto członka z listy"
            }.onFailure {
                showFailure(it, "Nie udało się usunąć członka")
            }
        }
    }

    fun createInvite(listId: String) {
        inviteCode.value = null
        viewModelScope.launch {
            repository.createInvite(listId).onSuccess {
                inviteCode.value = it.code
            }.onFailure {
                showFailure(it, "Nie udało się utworzyć zaproszenia")
            }
        }
    }

    fun acceptInvite(code: String) {
        if (code.isBlank()) {
            message.value = "Wpisz kod zaproszenia"
            return
        }
        viewModelScope.launch {
            repository.acceptInvite(code).onSuccess {
                repository.syncLists().onSuccess {
                    message.value = "Dołączono do listy"
                }.onFailure {
                    showFailure(it, "Dołączono do listy, ale nie udało się odświeżyć danych")
                }
            }.onFailure {
                showFailure(it, "Nie udało się zaakceptować zaproszenia")
            }
        }
    }

    fun createItem(
        listId: String,
        name: String,
        quantityText: String,
        unit: String,
        category: String = "",
        note: String = "",
        estimatedPriceText: String = ""
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
        val estimatedPrice = estimatedPriceText.toPriceOrNull()
        if (estimatedPriceText.isNotBlank() && estimatedPrice == null) {
            message.value = "Cena musi być liczbą"
            return
        }
        Validation.validatePrice(estimatedPrice)?.let {
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
                estimatedPrice
            ).onFailure {
                showFailure(it, "Nie udało się dodać produktu")
            }
        }
    }

    fun updateItem(
        listId: String,
        itemId: String,
        name: String,
        quantityText: String,
        unit: String,
        category: String,
        note: String,
        estimatedPriceText: String
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
        val estimatedPrice = estimatedPriceText.toPriceOrNull()
        if (estimatedPriceText.isNotBlank() && estimatedPrice == null) {
            message.value = "Cena musi być liczbą"
            return
        }
        Validation.validatePrice(estimatedPrice)?.let {
            message.value = it
            return
        }
        viewModelScope.launch {
            repository.updateItem(
                listId,
                itemId,
                name.trim(),
                quantity ?: 1.0,
                unit,
                category.trim(),
                note.trim(),
                estimatedPrice
            ).onFailure {
                showFailure(it, "Nie udało się zmienić produktu")
            }
        }
    }

    fun setPurchased(listId: String, itemId: String, purchased: Boolean) {
        viewModelScope.launch {
            repository.setPurchased(listId, itemId, purchased).onFailure {
                showFailure(it, "Nie udało się zmienić statusu")
            }
        }
    }

    fun setReserved(listId: String, itemId: String, reserved: Boolean) {
        viewModelScope.launch {
            repository.setReserved(listId, itemId, reserved).onFailure {
                showFailure(it, "Nie udało się zmienić rezerwacji")
            }
        }
    }

    fun deleteItem(listId: String, itemId: String) {
        viewModelScope.launch {
            repository.deleteItem(listId, itemId).onFailure {
                showFailure(it, "Nie udało się usunąć produktu")
            }
        }
    }

    fun loadListTotal(listId: String, currency: String) {
        val normalizedCurrency = currency.trim().uppercase()
        if (normalizedCurrency.length != 3 || normalizedCurrency.any { !it.isLetter() }) {
            message.value = "Podaj trzyliterowy kod waluty, np. EUR"
            return
        }
        listTotal.value = null
        viewModelScope.launch {
            repository.getListTotal(listId, normalizedCurrency).onSuccess {
                listTotal.value = it
                message.value = ""
            }.onFailure {
                showFailure(it, "Nie udało się pobrać sumy listy")
            }
        }
    }

    fun loadExchangeRate(fromCurrency: String, toCurrency: String) {
        val from = fromCurrency.trim().uppercase()
        val to = toCurrency.trim().uppercase()
        if (from.length != 3 || from.any { !it.isLetter() } ||
            to.length != 3 || to.any { !it.isLetter() }
        ) {
            message.value = "Podaj prawidłowe trzyliterowe kody walut"
            return
        }
        exchangeRate.value = null
        viewModelScope.launch {
            repository.getExchangeRate(from, to).onSuccess {
                exchangeRate.value = it
                message.value = ""
            }.onFailure {
                showFailure(it, "Nie udało się pobrać kursu")
            }
        }
    }

    fun clearMessage() {
        message.value = ""
    }

    private suspend fun showFailure(error: Throwable, fallback: String) {
        if ((error as? HttpException)?.code() == 401) {
            repository.logout()
            isLoggedIn.value = false
            message.value = "Sesja wygasła. Zaloguj się ponownie."
        } else {
            val responseBody = (error as? HttpException)
                ?.response()
                ?.errorBody()
                ?.string()
                ?.takeIf(String::isNotBlank)
            message.value = responseBody ?: error.message ?: fallback
        }
    }

    private fun String.toPriceOrNull(): Double? =
        trim().replace(',', '.').takeIf(String::isNotEmpty)?.toDoubleOrNull()

    class Factory(private val repository: ShoppingRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            TuimViewModel(repository) as T
    }
}
