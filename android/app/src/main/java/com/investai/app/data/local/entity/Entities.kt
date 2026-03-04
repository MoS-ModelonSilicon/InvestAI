package com.investai.app.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "watchlist")
data class CachedWatchlistItem(
    @PrimaryKey val id: Int,
    val symbol: String,
    val name: String?,
    val price: Double?,
    @ColumnInfo(name = "change_pct") val changePct: Double?,
    @ColumnInfo(name = "updated_at") val updatedAt: Long = System.currentTimeMillis(),
)

@Entity(tableName = "holdings")
data class CachedHolding(
    @PrimaryKey val id: Int,
    val symbol: String,
    val name: String?,
    val quantity: Double,
    @ColumnInfo(name = "buy_price") val buyPrice: Double,
    @ColumnInfo(name = "buy_date") val buyDate: String,
    @ColumnInfo(name = "updated_at") val updatedAt: Long = System.currentTimeMillis(),
)
