package com.g2jackob.tuim.data.repository

import com.g2jackob.tuim.data.local.AppDatabase
import com.g2jackob.tuim.data.local.ShoppingItemEntity
import com.g2jackob.tuim.data.local.ShoppingListEntity
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.AcceptInviteRequest
import com.g2jackob.tuim.data.network.AddMemberRequest
import com.g2jackob.tuim.data.network.ApiService
import com.g2jackob.tuim.data.network.CurrentUserDto
import com.g2jackob.tuim.data.network.ExchangeRateDto
import com.g2jackob.tuim.data.network.InviteDto
import com.g2jackob.tuim.data.network.ListTotalDto
import com.g2jackob.tuim.data.network.ListMemberDto
import com.g2jackob.tuim.data.network.ShoppingItemDto
import com.g2jackob.tuim.data.network.ShoppingItemRequest
import com.g2jackob.tuim.data.network.ShoppingListDto
import com.g2jackob.tuim.data.network.ShoppingListRequest
import kotlinx.coroutines.flow.Flow

class ShoppingRepositoryImpl(
    private val database: AppDatabase,
    private val api: ApiService,
    private val tokenStore: TokenStore
) : ShoppingRepository {
    private val dao = database.shoppingDao()
    override val lists: Flow<List<ShoppingListEntity>> = dao.observeLists()
    override fun items(listId: String): Flow<List<ShoppingItemEntity>> = dao.observeItems(listId)

    override fun isLoggedIn(): Boolean = !tokenStore.accessTokenSnapshot().isNullOrBlank()

    override suspend fun loginDemo(): Result<Unit> = runCatching {
        tokenStore.save(DEMO_ACCESS_TOKEN, DEMO_REFRESH_TOKEN)
        dao.upsertLists(
            listOf(
                ShoppingListEntity(
                    id = "demo-list",
                    name = "Zakupy na weekend",
                    description = "Lista demonstracyjna",
                    currency = "PLN"
                )
            )
        )
        dao.replaceItemsForList(
            "demo-list",
            listOf(
                ShoppingItemEntity(
                    id = "demo-milk",
                    listId = "demo-list",
                    name = "Mleko",
                    quantity = 2.0,
                    unit = "l",
                    category = "Napoje"
                ),
                ShoppingItemEntity(
                    id = "demo-bread",
                    listId = "demo-list",
                    name = "Chleb",
                    quantity = 1.0,
                    unit = "szt.",
                    category = "Pieczywo"
                )
            )
        )
    }

    override suspend fun completeLogin(
        accessToken: String,
        refreshToken: String?
    ): Result<Unit> = runCatching {
        require(accessToken.isNotBlank()) { "Keycloak nie zwrócił access tokenu" }
        tokenStore.save(accessToken, refreshToken)
    }

    override suspend fun logout() {
        tokenStore.clear()
        dao.clearAll()
    }

    override suspend fun getCurrentUser(): Result<CurrentUserDto> = runCatching {
        if (isDemoSession()) {
            CurrentUserDto(id = "demo", username = "demo", displayName = "Użytkownik demo")
        } else {
            api.getCurrentUser()
        }
    }

    override suspend fun syncLists(): Result<Unit> = runCatching {
        if (isDemoSession()) return@runCatching
        val remoteLists = api.getLists()
        val localLists = remoteLists.map { it.toEntity() }
        val localItems = remoteLists.flatMap { list ->
            api.getItems(list.id).map { it.toEntity(list.id) }
        }
        dao.replaceAll(localLists, localItems)
    }

    override suspend fun syncList(listId: String): Result<Unit> = runCatching {
        if (isDemoSession()) return@runCatching
        val remoteList = api.getList(listId)
        val remoteItems = api.getItems(listId)
        dao.upsertList(remoteList.toEntity())
        dao.replaceItemsForList(listId, remoteItems.map { it.toEntity(listId) })
    }

    override suspend fun createList(
        name: String,
        description: String,
        currency: String
    ): Result<Unit> = runCatching {
        if (isDemoSession()) {
            dao.upsertList(
                ShoppingListEntity(
                    id = "demo-${System.currentTimeMillis()}",
                    name = name,
                    description = description,
                    currency = currency
                )
            )
            return@runCatching
        }
        dao.upsertList(api.createList(ShoppingListRequest(name, description, currency)).toEntity())
    }

    override suspend fun updateList(
        listId: String,
        name: String,
        description: String,
        currency: String
    ): Result<Unit> = runCatching {
        val updated = if (isDemoSession()) {
            val current = requireNotNull(dao.getList(listId)) { "Lista nie istnieje" }
            current.copy(name = name, description = description, currency = currency)
        } else {
            api.updateList(
                listId,
                ShoppingListRequest(name, description, currency)
            ).toEntity()
        }
        dao.upsertList(updated)
    }

    override suspend fun setListArchived(listId: String, archived: Boolean): Result<Unit> =
        runCatching {
            val updated = if (isDemoSession()) {
                val current = requireNotNull(dao.getList(listId)) { "Lista nie istnieje" }
                current.copy(isArchived = archived)
            } else if (archived) {
                api.archiveList(listId).toEntity()
            } else {
                api.unarchiveList(listId).toEntity()
            }
            dao.upsertList(updated)
        }

    override suspend fun deleteList(listId: String): Result<Unit> = runCatching {
        if (!isDemoSession()) api.deleteList(listId)
        dao.deleteListAndItems(listId)
    }

    override suspend fun getMembers(listId: String): Result<List<ListMemberDto>> = runCatching {
        if (isDemoSession()) emptyList() else api.getMembers(listId)
    }

    override suspend fun addMember(listId: String, identifier: String): Result<Unit> = runCatching {
        check(!isDemoSession()) { "Udostępnianie wymaga zalogowania do serwera." }
        api.addMember(listId, AddMemberRequest(identifier.trim()))
    }

    override suspend fun removeMember(listId: String, userId: String): Result<Unit> = runCatching {
        check(!isDemoSession()) { "Zarządzanie członkami wymaga zalogowania do serwera." }
        api.removeMember(listId, userId)
    }

    override suspend fun createInvite(listId: String): Result<InviteDto> = runCatching {
        check(!isDemoSession()) { "Zaproszenia wymagają zalogowania do serwera." }
        api.createInvite(listId)
    }

    override suspend fun acceptInvite(code: String): Result<Unit> = runCatching {
        check(!isDemoSession()) { "Dołączanie do list wymaga zalogowania do serwera." }
        api.acceptInvite(AcceptInviteRequest(code.trim()))
    }

    override suspend fun createItem(
        listId: String,
        name: String,
        quantity: Double,
        unit: String,
        category: String,
        note: String,
        estimatedPrice: Double?
    ): Result<Unit> = runCatching {
        val item = if (isDemoSession()) {
            ShoppingItemEntity(
                id = "demo-${System.currentTimeMillis()}",
                listId = listId,
                name = name,
                quantity = quantity,
                unit = unit,
                category = category,
                note = note,
                estimatedPrice = estimatedPrice
            )
        } else {
            api.createItem(
                listId,
                ShoppingItemRequest(name, quantity, unit, category, note, estimatedPrice)
            ).toEntity(listId)
        }
        dao.upsertItem(item)
    }

    override suspend fun updateItem(
        listId: String,
        itemId: String,
        name: String,
        quantity: Double,
        unit: String,
        category: String,
        note: String,
        estimatedPrice: Double?
    ): Result<Unit> = runCatching {
        if (isDemoSession()) {
            val item = requireNotNull(dao.getItem(itemId)) { "Produkt nie istnieje" }
            dao.upsertItem(
                item.copy(
                    name = name,
                    quantity = quantity,
                    unit = unit,
                    category = category,
                    note = note,
                    estimatedPrice = estimatedPrice
                )
            )
        } else {
            val updated = api.updateItem(
                listId,
                itemId,
                ShoppingItemRequest(name, quantity, unit, category, note, estimatedPrice)
            )
            dao.upsertItem(updated.toEntity(listId))
        }
    }

    override suspend fun setPurchased(
        listId: String,
        itemId: String,
        purchased: Boolean
    ): Result<Unit> = runCatching {
        if (isDemoSession()) {
            val item = requireNotNull(dao.getItem(itemId)) { "Produkt nie istnieje" }
            dao.upsertItem(item.copy(purchased = purchased))
            return@runCatching
        }
        val updated = if (purchased) {
            api.purchaseItem(listId, itemId)
        } else {
            api.unpurchaseItem(listId, itemId)
        }
        dao.upsertItem(updated.toEntity(listId))
    }

    override suspend fun setReserved(
        listId: String,
        itemId: String,
        reserved: Boolean
    ): Result<Unit> = runCatching {
        if (isDemoSession()) {
            val item = requireNotNull(dao.getItem(itemId)) { "Produkt nie istnieje" }
            dao.upsertItem(item.copy(reservedBy = if (reserved) "Ja" else null))
            return@runCatching
        }
        val updated = if (reserved) {
            api.reserveItem(listId, itemId)
        } else {
            api.releaseItem(listId, itemId)
        }
        dao.upsertItem(updated.toEntity(listId))
    }

    override suspend fun deleteItem(listId: String, itemId: String): Result<Unit> = runCatching {
        if (!isDemoSession()) api.deleteItem(listId, itemId)
        dao.deleteItem(itemId)
    }

    override suspend fun getListTotal(
        listId: String,
        currency: String
    ): Result<ListTotalDto> = runCatching {
        if (isDemoSession()) {
            ListTotalDto(currency = "PLN", total = "0.00", itemsPriced = 0, itemsWithoutPrice = 2)
        } else {
            api.getListTotal(listId, currency.trim().uppercase())
        }
    }

    override suspend fun getExchangeRate(
        fromCurrency: String,
        toCurrency: String
    ): Result<ExchangeRateDto> = runCatching {
        check(!isDemoSession()) { "Kursy walut wymagają połączenia z backendem." }
        api.getExchangeRate(fromCurrency.trim().uppercase(), toCurrency.trim().uppercase())
    }

    private fun isDemoSession(): Boolean =
        tokenStore.accessTokenSnapshot() == DEMO_ACCESS_TOKEN

    private fun ShoppingListDto.toEntity() = ShoppingListEntity(
        id = id,
        name = name,
        description = description.orEmpty(),
        currency = currency ?: "PLN",
        isArchived = isArchived,
        role = role ?: "owner",
        itemsCount = itemsCount,
        purchasedCount = purchasedCount
    )

    private fun ShoppingItemDto.toEntity(listId: String) = ShoppingItemEntity(
        id = id,
        listId = listId,
        name = name,
        quantity = quantity,
        unit = unit,
        category = category.orEmpty(),
        note = note.orEmpty(),
        purchased = purchased,
        reservedBy = reservedBy?.label()?.takeIf(String::isNotBlank),
        estimatedPrice = estimatedPrice
    )

    private companion object {
        const val DEMO_ACCESS_TOKEN = "demo-access-token"
        const val DEMO_REFRESH_TOKEN = "demo-refresh-token"
    }
}
