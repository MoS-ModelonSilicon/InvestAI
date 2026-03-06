package com.investai.app.ui.valuescanner

import com.investai.app.data.api.models.ValueScannerResponse
import com.investai.app.data.api.models.ValueScannerSectors
import com.investai.app.data.api.models.ValueStock
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
class ValueScannerViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repo: MarketRepository
    private lateinit var viewModel: ValueScannerViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repo = mockk()

        coEvery { repo.getValueScannerSectors() } returns Result.success(
            ValueScannerSectors(sectors = listOf("Technology", "Healthcare"), excluded = listOf("Energy"))
        )
        coEvery { repo.getValueScanner(any(), any(), any(), any()) } returns Result.success(
            ValueScannerResponse(
                candidates = listOf(
                    ValueStock(symbol = "INTC", name = "Intel", price = 25.0, score = 85.0, signal = "Buy"),
                ),
                total = 1,
                page = 1,
                pages = 1,
            )
        )

        viewModel = ValueScannerViewModel(repo)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `init loads sectors and candidates`() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertEquals(listOf("Technology", "Healthcare"), state.sectors)
        assertEquals(1, state.candidates.size)
        assertEquals("INTC", state.candidates[0].symbol)
    }

    @Test
    fun `setSignal filters candidates`() = runTest {
        advanceUntilIdle()
        viewModel.setSignal("Strong Buy")
        advanceUntilIdle()
        assertEquals("Strong Buy", viewModel.uiState.value.selectedSignal)
    }

    @Test
    fun `pagination works`() = runTest {
        coEvery { repo.getValueScanner(any(), any(), any(), any()) } returns Result.success(
            ValueScannerResponse(candidates = emptyList(), total = 30, page = 1, pages = 2)
        )
        viewModel = ValueScannerViewModel(repo)
        advanceUntilIdle()
        assertEquals(2, viewModel.uiState.value.totalPages)

        viewModel.nextPage()
        advanceUntilIdle()
        assertEquals(2, viewModel.uiState.value.page)
    }
}
