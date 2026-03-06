package com.investai.app.ui.education

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.investai.app.data.api.models.EducationArticle
import com.investai.app.data.api.models.EducationCategory
import com.investai.app.data.repository.MarketRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class EducationUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val categories: List<EducationCategory> = emptyList(),
    val articles: List<EducationArticle> = emptyList(),
    val selectedCategory: String? = null,
    val expandedArticleId: String? = null,
)

@HiltViewModel
class EducationViewModel @Inject constructor(
    private val repo: MarketRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(EducationUiState())
    val uiState: StateFlow<EducationUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun selectCategory(categoryId: String?) {
        _uiState.value = _uiState.value.copy(selectedCategory = categoryId)
    }

    fun toggleArticle(articleId: String) {
        _uiState.value = _uiState.value.copy(
            expandedArticleId = if (_uiState.value.expandedArticleId == articleId) null else articleId,
        )
    }

    val filteredArticles: List<EducationArticle>
        get() {
            val state = _uiState.value
            return if (state.selectedCategory == null) state.articles
            else state.articles.filter { it.category == state.selectedCategory }
        }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            repo.getEducation().fold(
                onSuccess = { result ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        categories = result.categories,
                        articles = result.articles,
                    )
                },
                onFailure = { e ->
                    _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
                },
            )
        }
    }
}
