package com.g2jackob.tuim.data.local

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface ShoppingDao {
    @Query("SELECT * FROM shopping_lists ORDER BY name")
    fun observeLists(): Flow<List<ShoppingListEntity>>

    @Query("SELECT * FROM shopping_items WHERE listId = :listId ORDER BY name")
    fun observeItems(listId: String): Flow<List<ShoppingItemEntity>>

    @Upsert
    suspend fun upsertLists(lists: List<ShoppingListEntity>)

    @Upsert
    suspend fun upsertItems(items: List<ShoppingItemEntity>)

    @Upsert
    suspend fun upsertList(list: ShoppingListEntity)

    @Upsert
    suspend fun upsertItem(item: ShoppingItemEntity)

    @Query("SELECT * FROM shopping_items WHERE id = :itemId")
    suspend fun getItem(itemId: String): ShoppingItemEntity?

    @Query("DELETE FROM shopping_items WHERE id = :itemId")
    suspend fun deleteItem(itemId: String)

    @Query("DELETE FROM shopping_lists WHERE id = :listId")
    suspend fun deleteList(listId: String)
}
