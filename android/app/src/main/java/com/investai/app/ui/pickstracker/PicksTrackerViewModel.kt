package com.investai.app.ui.pickstracker

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.Pick
import com.investai.app.data.api.models.PickStats
import com.investai.app.data.api.models.PicksResponse
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PicksTrackerUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val picks: List<Pick> = emptyList(),
    val stats: PickStats? = null,
    val selectedType: String? = null,
    val seedingWatchlist: Boolean = false,
    val seedResult: String? = null,
)

@HiltViewModel
class PicksTrackerViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PicksTrackerUiState())
    val uiState: StateFlow<PicksTrackerUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun setType(type: String?) {
        _uiState.value = _uiState.value.copy(selectedType = type)
        load()
    }

    fun seedWatchlist() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(seedingWatchlist = true, seedResult = null)
            repo.seedWatchlist().fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        seedingWatchlist = false,
                        seedResult = "Added ${result.added}, skipped ${result.skipped} of ${result.totalSymbols} symbols",
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(seedingWatchlist = false, seedResult = "Error: ${e.message}")
                },
            )
        }
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            repo.getPicks(type = _uiState.value.selectedType).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        picks = result.picks,
                        stats = result.stats,
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
                },
            )
        }
    }
}
