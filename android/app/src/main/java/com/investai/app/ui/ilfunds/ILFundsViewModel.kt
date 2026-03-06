package com.investai.app.ui.ilfunds

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.ILFund
import com.investai.app.data.api.models.ILFundsMeta
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ILFundsUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val funds: List<ILFund> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val totalPages: Int = 1,
    val fundType: String? = null,
    val manager: String? = null,
    val kosherOnly: Boolean? = null,
    val sortBy: String = "fee",
    val types: List<String> = emptyList(),
    val managers: List<String> = emptyList(),
)

@HiltViewModel
class ILFundsViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ILFundsUiState())
    val uiState: StateFlow<ILFundsUiState> = _uiState.asStateFlow()

    init {
        loadMeta()
        search()
    }

    fun setFundType(type: String?) {
        _uiState.value = _uiState.value.copy(fundType = type, page = 1)
        search()
    }

    fun setKosherOnly(kosher: Boolean?) {
        _uiState.value = _uiState.value.copy(kosherOnly = kosher, page = 1)
        search()
    }

    fun setSortBy(sort: String) {
        _uiState.value = _uiState.value.copy(sortBy = sort, page = 1)
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

    private fun loadMeta() {
        viewModelScope.launch {
            repo.getILFundsMeta().onSuccess { meta ->
                _uiState.value = _uiState.value.copy(
                    types = meta.types,
                    managers = meta.managers,
                )
            }
        }
    }

    fun search() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val s = _uiState.value
            repo.getILFunds(
                fundType = s.fundType,
                manager = s.manager,
                kosherOnly = s.kosherOnly,
                sortBy = s.sortBy,
                page = s.page,
            ).fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        funds = result.funds,
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
