package com.g2jackob.tuim.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "shopping_lists")
data class ShoppingListEntity(
    @PrimaryKey val id: String,
    val name: String,
    val description: String = "",
    val currency: String = "PLN",
    val isArchived: Boolean = false,
    val role: String = "owner",
    val itemsCount: Int = 0,
    val purchasedCount: Int = 0,
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "shopping_items")
data class ShoppingItemEntity(
    @PrimaryKey val id: String,
    val listId: String,
    val name: String,
    val quantity: Double,
    val unit: String,
    val category: String = "",
    val note: String = "",
    val purchased: Boolean = false,
    val reservedBy: String? = null,
    val estimatedPrice: Double? = null,
    val updatedAt: Long = System.currentTimeMillis()
)
