package com.g2jackob.tuim.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [ShoppingListEntity::class, ShoppingItemEntity::class],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun shoppingDao(): ShoppingDao

    companion object {
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "ALTER TABLE shopping_lists ADD COLUMN isArchived INTEGER NOT NULL DEFAULT 0"
                )
                db.execSQL(
                    "ALTER TABLE shopping_lists ADD COLUMN role TEXT NOT NULL DEFAULT 'owner'"
                )
                db.execSQL(
                    "ALTER TABLE shopping_lists ADD COLUMN itemsCount INTEGER NOT NULL DEFAULT 0"
                )
                db.execSQL(
                    "ALTER TABLE shopping_lists ADD COLUMN purchasedCount INTEGER NOT NULL DEFAULT 0"
                )
            }
        }
    }
}
