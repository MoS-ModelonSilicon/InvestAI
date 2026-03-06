package com.investai.app.ui.valuescanner

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.ValueScannerResponse
import com.investai.app.data.api.models.ValueStock
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ValueScannerUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val candidates: List<ValueStock> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val totalPages: Int = 1,
    val selectedSector: String? = null,
    val selectedSignal: String? = null,
    val sortBy: String = "score",
    val sectors: List<String> = emptyList(),
)

@HiltViewModel
class ValueScannerViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ValueScannerUiState())
    val uiState: StateFlow<ValueScannerUiState> = _uiState.asStateFlow()

    init {
        loadSectors()
        search()
    }

    fun setSector(sector: String?) {
        _uiState.value = _uiState.value.copy(selectedSector = sector, page = 1)
        search()
    }

    fun setSignal(signal: String?) {
        _uiState.value = _uiState.value.copy(selectedSignal = signal, page = 1)
        search()
    }

    fun setSortBy(sortBy: String) {
        _uiState.value = _uiState.value.copy(sortBy = sortBy, page = 1)
        search()
    }

    fun nextPage() {
        if (_uiState.value.page < _uiState.value.totalPages) {
            _uiState.value = _uiState.value.copy(page = _uiState.value.page + 1)
            search()
        }
    }

    fun previousPage() {
        if (_uiState.value.page > 1) {
            _uiState.value = _uiState.value.copy(page = _uiState.value.page - 1)
            search()
        }
    }

    private fun loadSectors() {
        viewModelScope.launch {
            repo.getValueScannerSectors().onSuccess { data ->
                _uiState.value = _uiState.value.copy(sectors = data.sectors)
            }
        }
    }

    fun search() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val state = _uiState.value
            repo.getValueScanner(
                sector = state.selectedSector,
                signal = state.selectedSignal,
                sortBy = state.sortBy,
                page = state.page,
            ).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        candidates = result.candidates,
                        total = result.total,
                        page = result.page,
                        totalPages = result.pages,
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
                },
            )
        }
    }
}
