package com.investai.app.ui.recommendations

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.InvestAIApi
import com.investai.app.data.api.models.Recommendation
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class RecommendationsUiState(
    val isLoading: Boolean = true,
    val error: String? = null,
    val recommendations: List<Recommendation> = emptyList(),
)

@HiltViewModel
class RecommendationsViewModel @Inject constructor(
    private val api: InvestAIApi,
) : ViewModel() {

    private val _uiState = MutableStateFlow(RecommendationsUiState())
    val uiState: StateFlow<RecommendationsUiState> = _uiState.asStateFlow()

    init { load() }

    private fun load() {
        viewModelScope.launch {
            try {
                val response = api.getRecommendations()
                _uiState.value = RecommendationsUiState(
                    isLoading = false,
                    recommendations = response.recommendations,
                )
            } catch (e: Exception) {
                _uiState.value = RecommendationsUiState(isLoading = false, error = e.message)
            }
        }
    }
}
