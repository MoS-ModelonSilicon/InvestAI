package com.investai.app.data.local.dao

import androidx.room.*
import com.investai.app.data.local.entity.CachedHolding
import kotlinx.coroutines.flow.Flow

@Dao
interface HoldingDao {

    @Query("SELECT * FROM holdings ORDER BY buy_date DESC")
    fun getAll(): Flow<List<CachedHolding>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<CachedHolding>)

    @Query("DELETE FROM holdings")
    suspend fun deleteAll()

    @Transaction
    suspend fun replaceAll(items: List<CachedHolding>) {
        deleteAll()
        insertAll(items)
    }
}
