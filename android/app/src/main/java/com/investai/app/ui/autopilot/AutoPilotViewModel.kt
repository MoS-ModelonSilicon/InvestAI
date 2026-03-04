package com.investai.app.ui.autopilot

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.AutopilotProfile
import com.investai.app.data.api.models.AutopilotSimulation
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AutoPilotUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val profiles: List<AutopilotProfile> = emptyList(),
    val selectedProfile: String? = null,
    val simulation: AutopilotSimulation? = null,
    val isSimulating: Boolean = false,
)

@HiltViewModel
class AutoPilotViewModel @Inject constructor(
    private val api: InvestAIApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(AutoPilotUiState())
    val uiState: StateFlow<AutoPilotUiState> = _uiState.asStateFlow()

    init { loadProfiles() }

    fun selectProfile(profileId: String) {
        _uiState.value = _uiState.value.copy(selectedProfile = profileId)
        simulate(profileId)
    }

    private fun loadProfiles() {
        viewModelScope.launch {
            try {
                val profiles = api.getAutopilotProfiles()
                _uiState.value = AutoPilotUiState(
                    isLoading = false,
                    profiles = profiles,
                    selectedProfile = profiles.firstOrNull()?.id,
                )
                profiles.firstOrNull()?.id?.let { simulate(it) }
            } catch (e: Exception) {
                _uiState.value = AutoPilotUiState(isLoading = false, error = e.message)
            }
        }
    }

    private fun simulate(profileId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSimulating = true)
            try {
                val sim = api.simulateAutopilot(profile = profileId)
                _uiState.value = _uiState.value.copy(isSimulating = false, simulation = sim)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isSimulating = false, error = e.message)
            }
        }
    }
}
