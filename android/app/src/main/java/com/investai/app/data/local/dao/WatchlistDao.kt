package com.investai.app.data.local.dao

import androidx.room.*
import com.investai.app.data.local.entity.CachedWatchlistItem
import kotlinx.coroutines.flow.Flow

@Dao
interface WatchlistDao {

    @Query("SELECT * FROM watchlist ORDER BY symbol ASC")
    fun getAll(): Flow<List<CachedWatchlistItem>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<CachedWatchlistItem>)

    @Query("DELETE FROM watchlist")
    suspend fun deleteAll()

    @Transaction
    suspend fun replaceAll(items: List<CachedWatchlistItem>) {
        deleteAll()
        insertAll(items)
    }
}
