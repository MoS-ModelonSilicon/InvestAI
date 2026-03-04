package com.investai.app.ui.screener

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.ScreenerResponse
import com.investai.app.data.api.models.ScreenerSectors
import com.investai.app.data.api.models.ScreenerStock
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ScreenerUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val stocks: List<ScreenerStock> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val totalPages: Int = 1,

    // Filters
    val assetType: String? = null,
    val selectedSector: String? = null,
    val selectedRegion: String? = null,

    // Available filter options
    val sectors: List<String> = emptyList(),
    val regions: List<String> = emptyList(),
)

@HiltViewModel
class ScreenerViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ScreenerUiState())
    val uiState: StateFlow<ScreenerUiState> = _uiState.asStateFlow()

    init {
        loadSectors()
        search()
    }

    fun setAssetType(type: String?) {
        _uiState.value = _uiState.value.copy(assetType = type, page = 1)
        search()
    }

    fun setSector(sector: String?) {
        _uiState.value = _uiState.value.copy(selectedSector = sector, page = 1)
        search()
    }

    fun setRegion(region: String?) {
        _uiState.value = _uiState.value.copy(selectedRegion = region, page = 1)
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
            repo.getScreenerSectors().onSuccess { data ->
                _uiState.value = _uiState.value.copy(
                    sectors = data.sectors,
                    regions = data.regions,
                )
            }
        }
    }

    fun search() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            val state = _uiState.value
            repo.getScreener(
                assetType = state.assetType,
                sector = state.selectedSector,
                region = state.selectedRegion,
                page = state.page,
            ).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        stocks = result.stocks,
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
