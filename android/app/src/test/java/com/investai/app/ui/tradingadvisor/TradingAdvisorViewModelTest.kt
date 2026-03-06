package com.investai.app.ui.tradingadvisor

import com.investai.app.data.api.models.TradingDashboard
import com.investai.app.data.api.models.TradingPackage
import com.investai.app.data.api.models.TradingPick
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
class TradingAdvisorViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repo: MarketRepository
    private lateinit var viewModel: TradingAdvisorViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repo = mockk()

        coEvery { repo.getTradingDashboard() } returns Result.success(
            TradingDashboard(
                marketMood = "Bullish",
                packages = listOf(
                    TradingPackage(
                        name = "Momentum",
                        description = "Momentum plays",
                        picks = listOf(
                            TradingPick(symbol = "NVDA", score = 90.0, signal = "Strong Buy"),
                        ),
                    ),
                ),
                picks = listOf(
                    TradingPick(symbol = "TSLA", score = 75.0, signal = "Buy"),
                ),
            )
        )

        viewModel = TradingAdvisorViewModel(repo)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `init loads trading dashboard`() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertNotNull(state.dashboard)
        assertEquals("Bullish", state.dashboard?.marketMood)
        assertEquals(1, state.dashboard?.packages?.size)
        assertEquals("NVDA", state.dashboard?.packages?.first()?.picks?.first()?.symbol)
    }

    @Test
    fun `error state on failure`() = runTest {
        coEvery { repo.getTradingDashboard() } returns Result.failure(RuntimeException("Timeout"))
        viewModel = TradingAdvisorViewModel(repo)
        advanceUntilIdle()
        assertEquals("Timeout", viewModel.uiState.value.error)
        assertNull(viewModel.uiState.value.dashboard)
    }
}
