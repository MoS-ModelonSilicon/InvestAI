package com.investai.app.ui.riskprofile

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.components.StockItemSkeleton
import com.investai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RiskProfileScreen(
    onBack: () -> Unit,
    viewModel: RiskProfileViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Risk Profile", fontWeight = FontWeight.Bold) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Surface),
        )

        if (state.isLoading) {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(4) { StockItemSkeleton() }
            }
        } else if (state.hasProfile && state.profile != null) {
            // Show existing profile result
            ProfileResult(state = state, onRetake = { viewModel.retakeQuiz() })
        } else {
            // Show questionnaire
            ProfileForm(state = state, viewModel = viewModel)
        }
    }
}

@Composable
private fun ProfileResult(state: RiskProfileUiState, onRetake: () -> Unit) {
    val profile = state.profile!!
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Your Profile", fontSize = 14.sp, color = OnSurfaceVariant)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        profile.profileLabel,
                        fontWeight = FontWeight.Bold,
                        fontSize = 24.sp,
                        color = Primary,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Risk Score: ${profile.riskScore}/100",
                        fontSize = 14.sp,
                        color = OnSurface,
                    )
                    Spacer(Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = { profile.riskScore / 100f },
                        modifier = Modifier.fillMaxWidth().height(8.dp),
                        color = when {
                            profile.riskScore <= 33 -> Gain
                            profile.riskScore <= 66 -> Caution
                            else -> Loss
                        },
                        trackColor = OutlineVariant,
                    )
                }
            }
        }

        // Allocation
        state.allocation?.let { alloc ->
            item {
                Card(
                    colors = CardDefaults.cardColors(containerColor = SurfaceContainer),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Suggested Allocation", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = OnSurface)
                        Spacer(Modifier.height(12.dp))
                        AllocationBar("Stocks", alloc.stocks, Primary)
                        AllocationBar("Bonds", alloc.bonds, BlueInfo)
                        AllocationBar("Cash", alloc.cash, Gain)
                    }
                }
            }
        }

        item {
            OutlinedButton(
                onClick = onRetake,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Retake Quiz")
            }
        }
    }
}

@Composable
private fun AllocationBar(label: String, pct: Double, color: androidx.compose.ui.graphics.Color) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(label, fontSize = 13.sp, color = OnSurface)
            Text("%.0f%%".format(pct), fontSize = 13.sp, fontWeight = FontWeight.Bold, color = color)
        }
        LinearProgressIndicator(
            progress = { (pct / 100f).toFloat() },
            modifier = Modifier.fillMaxWidth().height(6.dp),
            color = color,
            trackColor = OutlineVariant,
        )
    }
}

@Composable
private fun ProfileForm(state: RiskProfileUiState, viewModel: RiskProfileViewModel) {
    LazyColumn(
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text("Investment Questionnaire", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = OnSurface)
            Text("Answer these questions to determine your risk profile", fontSize = 12.sp, color = OnSurfaceVariant)
        }

        item {
            QuestionDropdown(
                label = "Investment Goal",
                value = state.goal,
                options = listOf("growth" to "Growth", "income" to "Income", "preservation" to "Capital Preservation", "speculation" to "Speculation"),
                onSelect = { viewModel.updateField("goal", it) },
            )
        }
        item {
            QuestionDropdown(
                label = "Timeline",
                value = state.timeline,
                options = listOf("< 1 year" to "< 1 Year", "1-3 years" to "1-3 Years", "3-5 years" to "3-5 Years", "5-10 years" to "5-10 Years", "10+ years" to "10+ Years"),
                onSelect = { viewModel.updateField("timeline", it) },
            )
        }
        item {
            QuestionDropdown(
                label = "Investment Style",
                value = state.investmentStyle,
                options = listOf("conservative" to "Conservative", "balanced" to "Balanced", "aggressive" to "Aggressive"),
                onSelect = { viewModel.updateField("investmentStyle", it) },
            )
        }
        item {
            QuestionDropdown(
                label = "Experience Level",
                value = state.experience,
                options = listOf("beginner" to "Beginner", "intermediate" to "Intermediate", "advanced" to "Advanced"),
                onSelect = { viewModel.updateField("experience", it) },
            )
        }
        item {
            QuestionDropdown(
                label = "If the market dropped 20%, you would...",
                value = state.riskReaction,
                options = listOf("sell" to "Sell everything", "hold" to "Hold and wait", "buy" to "Buy more"),
                onSelect = { viewModel.updateField("riskReaction", it) },
            )
        }
        item {
            QuestionDropdown(
                label = "Income Stability",
                value = state.incomeStability,
                options = listOf("unstable" to "Unstable", "moderate" to "Moderate", "stable" to "Stable"),
                onSelect = { viewModel.updateField("incomeStability", it) },
            )
        }

        // Error
        state.error?.let {
            item {
                Text("Error: $it", color = Loss, fontSize = 12.sp)
            }
        }

        // Submit
        item {
            Button(
                onClick = { viewModel.submitProfile() },
                modifier = Modifier.fillMaxWidth(),
                enabled = !state.isSubmitting,
                colors = ButtonDefaults.buttonColors(containerColor = Primary),
            ) {
                if (state.isSubmitting) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp, color = OnPrimary)
                } else {
                    Text("Calculate My Profile")
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun QuestionDropdown(
    label: String,
    value: String,
    options: List<Pair<String, String>>,
    onSelect: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val displayValue = options.find { it.first == value }?.second ?: value

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = it },
    ) {
        OutlinedTextField(
            value = displayValue,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = Primary,
                unfocusedBorderColor = OutlineVariant,
                focusedLabelColor = Primary,
                unfocusedLabelColor = OnSurfaceVariant,
                focusedTextColor = OnSurface,
                unfocusedTextColor = OnSurface,
            ),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (v, l) ->
                DropdownMenuItem(
                    text = { Text(l) },
                    onClick = { onSelect(v); expanded = false },
                )
            }
        }
    }
}
