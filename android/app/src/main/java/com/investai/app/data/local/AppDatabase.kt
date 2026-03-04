package com.investai.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.investai.app.data.local.dao.HoldingDao
import com.investai.app.data.local.dao.WatchlistDao
import com.investai.app.data.local.entity.CachedHolding
import com.investai.app.data.local.entity.CachedWatchlistItem

@Database(
    entities = [CachedWatchlistItem::class, CachedHolding::class],
    version = 1,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun watchlistDao(): WatchlistDao
    abstract fun holdingDao(): HoldingDao

    companion object {
        fun create(context: Context): AppDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                "investai.db"
            )
                .fallbackToDestructiveMigration()
                .build()
        }
    }
}
