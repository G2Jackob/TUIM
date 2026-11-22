package com.g2jackob.tuim.data.repository

import com.g2jackob.tuim.data.local.AppDatabase
import com.g2jackob.tuim.data.local.ShoppingItemEntity
import com.g2jackob.tuim.data.local.ShoppingListEntity
import com.g2jackob.tuim.data.local.TokenStore
import com.g2jackob.tuim.data.network.ApiService
import com.g2jackob.tuim.data.network.ExternalProductDto
import com.g2jackob.tuim.data.network.LoginRequest
import com.g2jackob.tuim.data.network.RefreshRequest
import com.g2jackob.tuim.data.network.ShoppingItemRequest
import com.g2jackob.tuim.data.network.ShoppingListRequest
import com.g2jackob.tuim.data.network.PurchasedRequest
import kotlinx.coroutines.flow.Flow

class ShoppingRepositoryImpl(
    private val database: AppDatabase,
    private val api: ApiService,
    private val tokenStore: TokenStore
) : ShoppingRepository {
    private val dao = database.shoppingDao()
    override val lists: Flow<List<ShoppingListEntity>> = dao.observeLists()
    override fun items(listId: String): Flow<List<ShoppingItemEntity>> =
        dao.observeItems(listId)

    override fun isLoggedIn(): Boolean = !tokenStore.accessTokenSnapshot().isNullOrBlank()

    override suspend fun login(username: String, password: String): Result<Unit> = runCatching {
        if (username.trim().equals("demo", ignoreCase = true) && password == "demo") {
            tokenStore.save("demo-access-token", "demo-refresh-token")
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
            dao.upsertItems(
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
            return@runCatching
        }

        val response = api.login(LoginRequest(username, password))
        val access = response.access()
        val refresh = response.refresh()
        require(access.isNotBlank()) { "Serwer nie zwrócił access tokenu" }
        tokenStore.save(access, refresh)
        syncLists().getOrThrow()
    }

    override suspend fun logout() = tokenStore.clear()

    override suspend fun refreshSession(): Result<Unit> = runCatching {
        val refresh = tokenStore.refreshTokenSnapshot()
        require(!refresh.isNullOrBlank()) { "Brak refresh tokenu" }
        val response = api.refresh(RefreshRequest(refresh))
        val access = response.access()
        require(access.isNotBlank()) { "Serwer nie zwrócił access tokenu" }
        tokenStore.save(access, response.refresh().ifBlank { refresh })
    }

    override suspend fun syncLists(): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            return@runCatching
        }
        val remoteLists = api.getLists()
        dao.upsertLists(remoteLists.map {
            ShoppingListEntity(
                id = it.id,
                name = it.name,
                description = it.description.orEmpty(),
                currency = it.currency ?: "PLN"
            )
        })
        remoteLists.forEach { list -> syncList(list.id).getOrThrow() }
    }

    override suspend fun syncList(listId: String): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            return@runCatching
        }
        val remote = api.getList(listId)
        dao.upsertList(
            ShoppingListEntity(
                id = remote.id,
                name = remote.name,
                description = remote.description.orEmpty(),
                currency = remote.currency ?: "PLN"
            )
        )
        dao.upsertItems((remote.items ?: emptyList()).map {
            ShoppingItemEntity(
                id = it.id,
                listId = remote.id,
                name = it.name,
                quantity = it.quantity,
                unit = it.unit,
                category = it.category.orEmpty(),
                note = it.note.orEmpty(),
                purchased = it.purchased,
                reservedBy = it.reservedBy,
                estimatedPrice = it.estimatedPrice
            )
        })
    }

    override suspend fun createList(
        name: String,
        description: String,
        currency: String
    ): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
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
        val created = api.createList(ShoppingListRequest(name, description, currency))
        dao.upsertList(
            ShoppingListEntity(created.id, created.name, created.description.orEmpty(), created.currency ?: "PLN")
        )
    }

    override suspend fun deleteList(listId: String): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            dao.deleteList(listId)
            return@runCatching
        }
        api.deleteList(listId)
        dao.deleteList(listId)
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
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            dao.upsertItem(
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
            )
            return@runCatching
        }
        val created = api.createItem(
            listId,
            ShoppingItemRequest(name, quantity, unit, category, note, estimatedPrice)
        )
        dao.upsertItem(
            ShoppingItemEntity(
                id = created.id,
                listId = listId,
                name = created.name,
                quantity = created.quantity,
                unit = created.unit,
                category = created.category.orEmpty(),
                note = created.note.orEmpty(),
                purchased = created.purchased,
                reservedBy = created.reservedBy,
                estimatedPrice = created.estimatedPrice
            )
        )
    }

    override suspend fun setPurchased(
        listId: String,
        itemId: String,
        purchased: Boolean
    ): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            val item = requireNotNull(dao.getItem(itemId)) { "Produkt nie istnieje" }
            dao.upsertItem(item.copy(purchased = purchased))
            return@runCatching
        }
        val updated = api.updateItem(listId, itemId, PurchasedRequest(purchased))
        dao.upsertItem(
            ShoppingItemEntity(
                id = updated.id,
                listId = listId,
                name = updated.name,
                quantity = updated.quantity,
                unit = updated.unit,
                category = updated.category.orEmpty(),
                note = updated.note.orEmpty(),
                purchased = updated.purchased,
                reservedBy = updated.reservedBy,
                estimatedPrice = updated.estimatedPrice
            )
        )
    }

    override suspend fun deleteItem(listId: String, itemId: String): Result<Unit> = runCatching {
        if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
            dao.deleteItem(itemId)
            return@runCatching
        }
        api.deleteItem(listId, itemId)
        dao.deleteItem(itemId)
    }

    override suspend fun searchProducts(query: String): Result<List<ExternalProductDto>> =
        runCatching {
            if (tokenStore.accessTokenSnapshot() == "demo-access-token") {
                val normalized = query.trim().lowercase()
                listOf(
                    ExternalProductDto("Mleko", "Napoje"),
                    ExternalProductDto("Chleb", "Pieczywo"),
                    ExternalProductDto("Jabłko", "Owoce")
                ).filter {
                    normalized.isBlank() || it.name.lowercase().contains(normalized)
                }
            } else {
                api.searchProducts(query).products.orEmpty()
            }
        }
}
