package com.investai.app.ui.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.investai.app.ui.theme.*

@Composable
fun ForgotPasswordScreen(
    onBack: () -> Unit,
    onPasswordReset: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    // 0 = enter email, 1 = enter code + new password
    var step by remember { mutableIntStateOf(0) }
    var email by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    var newPassword by remember { mutableStateOf("") }

    // Clear state on mount
    LaunchedEffect(Unit) { viewModel.clearError() }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Surface),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 400.dp)
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // Back button
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = {
                    if (step == 1) {
                        step = 0
                        viewModel.clearError()
                    } else {
                        onBack()
                    }
                }) {
                    Icon(
                        imageVector = Icons.Filled.ArrowBack,
                        contentDescription = "Back",
                        tint = OnSurface,
                    )
                }
                Spacer(Modifier.width(8.dp))
                Text(
                    text = if (step == 0) "Reset Password" else "Enter Code",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = OnSurface,
                )
            }
            Spacer(Modifier.height(24.dp))

            AnimatedContent(targetState = step, label = "resetStep") { currentStep ->
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    if (currentStep == 0) {
                        // Step 1: Enter email
                        Text(
                            text = "Enter your email address and we'll send you a 6-digit code to reset your password.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = OnSurfaceVariant,
                            textAlign = TextAlign.Center,
                        )
                        Spacer(Modifier.height(24.dp))

                        OutlinedTextField(
                            value = email,
                            onValueChange = { email = it },
                            label = { Text("Email") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Email,
                                imeAction = ImeAction.Done,
                            ),
                            keyboardActions = KeyboardActions(
                                onDone = {
                                    if (email.isNotBlank()) {
                                        viewModel.forgotPassword(email) { returnedCode ->
                                            if (returnedCode != null) code = returnedCode
                                            step = 1
                                        }
                                    }
                                },
                            ),
                            colors = textFieldColors(),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                        )
                        Spacer(Modifier.height(16.dp))

                        // Messages
                        if (uiState.error != null) {
                            Text(text = uiState.error!!, color = Loss, style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.height(8.dp))
                        }
                        if (uiState.successMessage != null) {
                            Text(text = uiState.successMessage!!, color = Gain, style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.height(8.dp))
                        }

                        Button(
                            onClick = {
                                viewModel.forgotPassword(email) { returnedCode ->
                                    if (returnedCode != null) code = returnedCode
                                    step = 1
                                }
                            },
                            enabled = email.isNotBlank() && !uiState.isLoading,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Primary),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            if (uiState.isLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    color = OnPrimary,
                                    strokeWidth = 2.dp,
                                )
                            } else {
                                Text("Send Reset Code", fontWeight = FontWeight.SemiBold)
                            }
                        }
                    } else {
                        // Step 2: Enter code + new password
                        Text(
                            text = "Enter the 6-digit code sent to your email and choose a new password.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = OnSurfaceVariant,
                            textAlign = TextAlign.Center,
                        )
                        Spacer(Modifier.height(24.dp))

                        OutlinedTextField(
                            value = code,
                            onValueChange = { if (it.length <= 6 && it.all { c -> c.isDigit() }) code = it },
                            label = { Text("6-Digit Code") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = ImeAction.Next,
                            ),
                            keyboardActions = KeyboardActions(onNext = { focusManager.moveFocus(FocusDirection.Down) }),
                            colors = textFieldColors(),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                        )
                        Spacer(Modifier.height(12.dp))

                        OutlinedTextField(
                            value = newPassword,
                            onValueChange = { newPassword = it },
                            label = { Text("New Password") },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Password,
                                imeAction = ImeAction.Done,
                            ),
                            keyboardActions = KeyboardActions(
                                onDone = {
                                    if (code.length == 6 && newPassword.length >= 4) {
                                        viewModel.resetPassword(email, code, newPassword) { onPasswordReset() }
                                    }
                                },
                            ),
                            colors = textFieldColors(),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                        )
                        Spacer(Modifier.height(16.dp))

                        // Messages
                        if (uiState.error != null) {
                            Text(text = uiState.error!!, color = Loss, style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.height(8.dp))
                        }
                        if (uiState.successMessage != null) {
                            Text(text = uiState.successMessage!!, color = Gain, style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.height(8.dp))
                        }

                        Button(
                            onClick = {
                                viewModel.resetPassword(email, code, newPassword) { onPasswordReset() }
                            },
                            enabled = code.length == 6 && newPassword.length >= 4 && !uiState.isLoading,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Primary),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            if (uiState.isLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    color = OnPrimary,
                                    strokeWidth = 2.dp,
                                )
                            } else {
                                Text("Reset Password", fontWeight = FontWeight.SemiBold)
                            }
                        }
                        Spacer(Modifier.height(16.dp))

                        TextButton(onClick = { viewModel.forgotPassword(email) { returnedCode -> if (returnedCode != null) code = returnedCode } }) {
                            Text("Resend code", color = Primary, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun textFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Primary,
    unfocusedBorderColor = OutlineVariant,
    focusedLabelColor = Primary,
    cursorColor = Primary,
    focusedTextColor = OnSurface,
    unfocusedTextColor = OnSurface,
)
