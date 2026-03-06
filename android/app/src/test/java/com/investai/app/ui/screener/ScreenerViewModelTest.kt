package com.investai.app.ui.screener

import com.investai.app.data.api.models.ScreenerResponse
import com.investai.app.data.api.models.ScreenerSectors
import com.investai.app.data.api.models.ScreenerStock
import com.investai.app.data.repository.MarketRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ScreenerViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repo: MarketRepository
    private lateinit var viewModel: ScreenerViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repo = mockk()

        coEvery { repo.getScreenerSectors() } returns Result.success(
            ScreenerSectors(sectors = listOf("Technology", "Healthcare"), regions = listOf("US", "EU"))
        )
        coEvery { repo.getScreener(any(), any(), any(), any()) } returns Result.success(
            ScreenerResponse(
                stocks = listOf(
                    ScreenerStock(symbol = "AAPL", name = "Apple Inc.", price = 150.0, changePct = 1.5),
                    ScreenerStock(symbol = "MSFT", name = "Microsoft Corp.", price = 300.0, changePct = -0.5),
                ),
                total = 2,
                page = 1,
                pages = 1,
            )
        )

        viewModel = ScreenerViewModel(repo)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `init loads sectors and stocks`() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertEquals(listOf("Technology", "Healthcare"), state.sectors)
        assertEquals(2, state.stocks.size)
        assertEquals("AAPL", state.stocks[0].symbol)
        assertFalse(state.isLoading)
    }

    @Test
    fun `setSector triggers new search`() = runTest {
        advanceUntilIdle()
        viewModel.setSector("Technology")
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertEquals("Technology", state.selectedSector)
        assertEquals(1, state.page)
    }

    @Test
    fun `setAssetType triggers new search`() = runTest {
        advanceUntilIdle()
        viewModel.setAssetType("ETF")
        advanceUntilIdle()
        assertEquals("ETF", viewModel.uiState.value.assetType)
    }

    @Test
    fun `error state on API failure`() = runTest {
        coEvery { repo.getScreener(any(), any(), any(), any()) } returns Result.failure(
            RuntimeException("Network error")
        )
        viewModel = ScreenerViewModel(repo)
        advanceUntilIdle()
        assertEquals("Network error", viewModel.uiState.value.error)
    }
}
