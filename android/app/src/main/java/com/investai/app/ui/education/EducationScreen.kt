package com.investai.app.ui.education

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.data.api.models.EducationArticle
import com.investai.app.ui.components.StockItemSkeleton
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EducationScreen(
    onBack: () -> Unit,
    viewModel: EducationViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Learn to Invest", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        // Category filter chips
        Row(
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            FilterChip(
                selected = state.selectedCategory == null,
                onClick = { viewModel.selectCategory(null) },
                label = { Text("All", fontSize = 12.sp) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Primary,
                    selectedLabelColor = OnPrimary,
                ),
            )
            state.categories.forEach { cat ->
                FilterChip(
                    selected = state.selectedCategory == cat.id,
                    onClick = { viewModel.selectCategory(cat.id) },
                    label = { Text(cat.name, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = Primary,
                        selectedLabelColor = OnPrimary,
                    ),
                )
            }
        }

        LazyColumn(
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (state.isLoading) {
                items(8) { StockItemSkeleton() }
            } else if (state.error != null) {
                item {
                    Text("Error: ${state.error}", color = Loss, modifier = Modifier.padding(16.dp))
                }
            } else {
                val articles = viewModel.filteredArticles
                items(articles) { article ->
                    ArticleCard(
                        article = article,
                        isExpanded = state.expandedArticleId == article.id,
                        onToggle = { viewModel.toggleArticle(article.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ArticleCard(article: EducationArticle, isExpanded: Boolean, onToggle: () -> Unit) {
    Card(
        onClick = onToggle,
        colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(article.title, fontWeight = FontWeight.Medium, fontSize = 14.sp, color = OnSurface)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Surface(
                            color = Primary.copy(alpha = 0.15f),
                            shape = MaterialTheme.shapes.extraSmall,
                        ) {
                            Text(
                                article.category,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                fontSize = 10.sp,
                                color = Primary,
                            )
                        }
                        Surface(
                            color = when (article.difficulty.lowercase()) {
                                "beginner" -> Gain.copy(alpha = 0.15f)
                                "intermediate" -> Caution.copy(alpha = 0.15f)
                                else -> Loss.copy(alpha = 0.15f)
                            },
                            shape = MaterialTheme.shapes.extraSmall,
                        ) {
                            Text(
                                article.difficulty,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                fontSize = 10.sp,
                                color = when (article.difficulty.lowercase()) {
                                    "beginner" -> Gain
                                    "intermediate" -> Caution
                                    else -> Loss
                                },
                            )
                        }
                    }
                }
                Icon(
                    if (isExpanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null,
                    tint = OnSurfaceVariant,
                )
            }
            AnimatedVisibility(visible = isExpanded) {
                Spacer(Modifier.height(8.dp))
                Text(article.content, fontSize = 13.sp, color = OnSurface, lineHeight = 20.sp)
            }
        }
    }
}
