package com.investai.app.ui.calendar

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.EarningsEvent
import com.investai.app.data.api.models.EconomicEvent
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CalendarUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val earnings: List<EarningsEvent> = emptyList(),
    val economic: List<EconomicEvent> = emptyList(),
    val selectedTab: Int = 0, // 0 = Earnings, 1 = Economic
)

@HiltViewModel
class CalendarViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(CalendarUiState())
    val uiState: StateFlow<CalendarUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun selectTab(tab: Int) {
        _uiState.value = _uiState.value.copy(selectedTab = tab)
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val earningsResult = repo.getEarningsCalendar()
            val economicResult = repo.getEconomicCalendar()
            _uiState.value = _uiState.value.copy(
                isLoading = false,
                earnings = earningsResult.getOrDefault(emptyList()),
                economic = economicResult.getOrDefault(emptyList()),
                error = earningsResult.exceptionOrNull()?.message
                    ?: economicResult.exceptionOrNull()?.message,
            )
        }
    }
}
