package com.investai.app.ui.more

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.preferences.ThemePreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MoreViewModel @Inject constructor(
    private val themePreferences: ThemePreferences,
) : ViewModel() {

    val isDarkMode: StateFlow<Boolean> = themePreferences.isDarkMode
        .stateIn(viewModelScope, SharingStarted.Eagerly, true)

    fun toggleDarkMode() {
        viewModelScope.launch {
            themePreferences.setDarkMode(!isDarkMode.value)
        }
    }
}
