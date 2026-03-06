package com.investai.app.ui.riskprofile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.AllocationResponse
import com.investai.app.data.api.models.ProfileAnswers
import com.investai.app.data.api.models.ProfileResponse
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class RiskProfileUiState(
    val isLoading: Boolean = false,
    val isSubmitting: Boolean = false,
    val error: String? = null,
    val profile: ProfileResponse? = null,
    val allocation: AllocationResponse? = null,
    val hasProfile: Boolean = false,
    // Form fields
    val goal: String = "growth",
    val timeline: String = "5-10 years",
    val investmentStyle: String = "balanced",
    val initialInvestment: String = "10000-50000",
    val monthlyInvestment: String = "500-1000",
    val experience: String = "intermediate",
    val riskReaction: String = "hold",
    val incomeStability: String = "stable",
)

@HiltViewModel
class RiskProfileViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(RiskProfileUiState())
    val uiState: StateFlow<RiskProfileUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
    }

    fun updateField(field: String, value: String) {
        _uiState.value = when (field) {
            "goal" -> _uiState.value.copy(goal = value)
            "timeline" -> _uiState.value.copy(timeline = value)
            "investmentStyle" -> _uiState.value.copy(investmentStyle = value)
            "initialInvestment" -> _uiState.value.copy(initialInvestment = value)
            "monthlyInvestment" -> _uiState.value.copy(monthlyInvestment = value)
            "experience" -> _uiState.value.copy(experience = value)
            "riskReaction" -> _uiState.value.copy(riskReaction = value)
            "incomeStability" -> _uiState.value.copy(incomeStability = value)
            else -> _uiState.value
        }
    }

    fun submitProfile() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSubmitting = true, error = null)
            val s = _uiState.value
            val answers = ProfileAnswers(
                goal = s.goal,
                timeline = s.timeline,
                investmentStyle = s.investmentStyle,
                initialInvestment = s.initialInvestment,
                monthlyInvestment = s.monthlyInvestment,
                experience = s.experience,
                riskReaction = s.riskReaction,
                incomeStability = s.incomeStability,
            )
            repo.submitProfile(answers).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isSubmitting = false,
                        profile = result,
                        hasProfile = true,
                    )
                    loadAllocation()
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isSubmitting = false, error = e.message)
                },
            )
        }
    }

    fun retakeQuiz() {
        _uiState.value = _uiState.value.copy(hasProfile = false, profile = null, allocation = null)
    }

    private fun loadProfile() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            repo.getProfile().fold(
                onSuccess = { result ->
                    if (result != null && result.profileLabel.isNotEmpty()) {
                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            profile = result,
                            hasProfile = true,
                        )
                        loadAllocation()
                    } else {
                        _uiState.value = _uiState.value.copy(isLoading = false, hasProfile = false)
                    }
                },
                onFailure = {
                    _uiState.value = _uiState.value.copy(isLoading = false, hasProfile = false)
                },
            )
        }
    }

    private fun loadAllocation() {
        viewModelScope.launch {
            repo.getProfileAllocation().onSuccess { alloc ->
                _uiState.value = _uiState.value.copy(allocation = alloc)
            }
        }
    }
}
