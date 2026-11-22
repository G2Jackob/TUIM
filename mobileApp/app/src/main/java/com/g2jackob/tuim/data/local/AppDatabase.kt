package com.g2jackob.tuim.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [ShoppingListEntity::class, ShoppingItemEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun shoppingDao(): ShoppingDao
}
