package com.investai.app.ui.smartadvisor

import com.investai.app.data.api.models.AdvisorAnalysis
import com.investai.app.data.api.models.AdvisorRanking
import com.investai.app.data.api.models.AdvisorReport
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
class SmartAdvisorViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repo: MarketRepository
    private lateinit var viewModel: SmartAdvisorViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repo = mockk()

        coEvery { repo.runAdvisorAnalysis(any(), any(), any()) } returns Result.success(
            AdvisorAnalysis(
                rankings = listOf(
                    AdvisorRanking(rank = 1, symbol = "AAPL", name = "Apple", score = 92.0, signal = "Buy", price = 180.0, changePct = 1.2),
                    AdvisorRanking(rank = 2, symbol = "MSFT", name = "Microsoft", score = 88.0, signal = "Buy", price = 400.0, changePct = 0.8),
                ),
                reportCard = AdvisorReport(marketMood = "Cautiously Optimistic", totalScanned = 500, summary = "Market looks okay"),
            )
        )

        viewModel = SmartAdvisorViewModel(repo)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `init loads analysis`() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertNotNull(state.analysis)
        assertEquals(2, state.analysis?.rankings?.size)
        assertEquals("AAPL", state.analysis?.rankings?.first()?.symbol)
    }

    @Test
    fun `setRisk triggers reanalysis`() = runTest {
        advanceUntilIdle()
        viewModel.setRisk("aggressive")
        advanceUntilIdle()
        assertEquals("aggressive", viewModel.uiState.value.risk)
    }

    @Test
    fun `default values`() = runTest {
        advanceUntilIdle()
        val state = viewModel.uiState.value
        assertEquals("balanced", state.risk)
        assertEquals("1y", state.period)
        assertEquals(10000.0, state.amount, 0.01)
    }
}
