package com.investai.app.ui.riskprofile

import com.investai.app.data.api.models.AllocationResponse
import com.investai.app.data.api.models.ProfileResponse
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
class RiskProfileViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repo: MarketRepository
    private lateinit var viewModel: RiskProfileViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repo = mockk()
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `shows form when no profile exists`() = runTest {
        coEvery { repo.getProfile() } returns Result.success(null)
        viewModel = RiskProfileViewModel(repo)
        advanceUntilIdle()
        assertFalse(viewModel.uiState.value.hasProfile)
    }

    @Test
    fun `shows result when profile exists`() = runTest {
        coEvery { repo.getProfile() } returns Result.success(
            ProfileResponse(riskScore = 65, profileLabel = "Balanced", goal = "growth", timeline = "5y")
        )
        coEvery { repo.getProfileAllocation() } returns Result.success(
            AllocationResponse(stocks = 60.0, bonds = 30.0, cash = 10.0)
        )
        viewModel = RiskProfileViewModel(repo)
        advanceUntilIdle()
        assertTrue(viewModel.uiState.value.hasProfile)
        assertEquals("Balanced", viewModel.uiState.value.profile?.profileLabel)
        assertEquals(60.0, viewModel.uiState.value.allocation?.stocks ?: 0.0, 0.01)
    }

    @Test
    fun `updateField changes form state`() = runTest {
        coEvery { repo.getProfile() } returns Result.success(null)
        viewModel = RiskProfileViewModel(repo)
        advanceUntilIdle()

        viewModel.updateField("goal", "income")
        assertEquals("income", viewModel.uiState.value.goal)

        viewModel.updateField("experience", "advanced")
        assertEquals("advanced", viewModel.uiState.value.experience)
    }

    @Test
    fun `retakeQuiz clears profile`() = runTest {
        coEvery { repo.getProfile() } returns Result.success(
            ProfileResponse(riskScore = 65, profileLabel = "Balanced")
        )
        coEvery { repo.getProfileAllocation() } returns Result.success(
            AllocationResponse(stocks = 60.0, bonds = 30.0, cash = 10.0)
        )
        viewModel = RiskProfileViewModel(repo)
        advanceUntilIdle()
        assertTrue(viewModel.uiState.value.hasProfile)

        viewModel.retakeQuiz()
        assertFalse(viewModel.uiState.value.hasProfile)
        assertNull(viewModel.uiState.value.profile)
    }
}
