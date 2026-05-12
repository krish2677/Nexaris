package com.desci.compute.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.desci.compute.ui.viewmodel.DashboardViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel = hiltViewModel(),
    onNavigateToLeaderboard: () -> Unit,
    onNavigateToProfile: () -> Unit,
    onNavigateToCampaigns: () -> Unit = {},
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("DeSci Compute", fontWeight = FontWeight.Bold)
                        Text(
                            text = state.userEmail,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = onNavigateToLeaderboard) {
                        Icon(Icons.Default.Leaderboard, "Leaderboard")
                    }
                    IconButton(onClick = onNavigateToProfile) {
                        Icon(Icons.Default.Person, "Profile")
                    }
                },
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // ── Compute Control Card ──
            ComputeCard(
                isComputing = state.isComputing,
                healthStatus = state.healthStatus,
                onStart = { viewModel.startComputing() },
                onStop = { viewModel.stopComputing() },
            )

            // Error banner
            state.error?.let { error ->
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer
                    ),
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(Icons.Default.Warning, null, tint = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.width(12.dp))
                        Text(error, modifier = Modifier.weight(1f))
                        IconButton(onClick = { viewModel.clearError() }) {
                            Icon(Icons.Default.Close, "Dismiss")
                        }
                    }
                }
            }

            // ── Campaign Arena Button ──
            Card(
                onClick = onNavigateToCampaigns,
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = Color(0xFF1C1040).copy(alpha = 0.8f)
                ),
            ) {
                Row(
                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("🏟️", fontSize = 28.sp)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Campaign Arena", color = Color.White, fontWeight = FontWeight.Bold)
                        Text("Compete in live AI campaigns", color = Color.White.copy(alpha = 0.7f), style = MaterialTheme.typography.bodySmall)
                    }
                    Icon(Icons.Default.ChevronRight, null, tint = Color(0xFFCDFF00))
                }
            }

            // ── Stats Row ──
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                StatCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.CheckCircle,
                    label = "Completed",
                    value = "${state.completedTasks}",
                    color = Color(0xFF34D399),
                )
                StatCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.Star,
                    label = "Score",
                    value = String.format("%.1f", state.userScore),
                    color = Color(0xFFCDFF00),
                )
            }

            // ── Platform Stats ──
            state.stats?.let { stats ->
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    ),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "Network Status",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.height(12.dp))
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            MiniStat("Contributors", "${stats.totalUsers}")
                            MiniStat("Active Devices", "${stats.activeDevices}")
                            MiniStat("Active Jobs", "${stats.activeJobs}")
                            MiniStat("Multiplier", "${stats.avgRewardMultiplier}x")
                        }
                    }
                }
            }

            // ── Active Jobs ──
            if (state.jobs.isNotEmpty()) {
                Text(
                    "Active Jobs",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                state.jobs.take(5).forEach { job ->
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(job.name, fontWeight = FontWeight.Medium)
                                Text(
                                    "${job.templateType} • ${job.activeWorkers}/${job.requiredWorkers} workers",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            AssistChip(
                                onClick = {},
                                label = { Text("${job.rewardMultiplier}x") },
                                leadingIcon = { Icon(Icons.Default.Bolt, null, Modifier.size(16.dp)) },
                            )
                        }
                    }
                }
            }

            // ── Top Contributors ──
            if (state.leaderboard.isNotEmpty()) {
                TextButton(onClick = onNavigateToLeaderboard) {
                    Text("View Full Leaderboard →")
                }
                state.leaderboard.take(3).forEachIndexed { i, entry ->
                    val medal = when (i) { 0 -> "🥇"; 1 -> "🥈"; 2 -> "🥉"; else -> "" }
                    ListItem(
                        headlineContent = { Text("$medal ${entry.email}") },
                        trailingContent = {
                            Text(
                                String.format("%.0f pts", entry.score),
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        },
                    )
                }
            }

            Spacer(Modifier.height(32.dp))
        }
    }
}

@Composable
private fun ComputeCard(
    isComputing: Boolean,
    healthStatus: com.desci.compute.compute.DeviceHealthCheck.HealthStatus?,
    onStart: () -> Unit,
    onStop: () -> Unit,
) {
    Card(
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth().animateContentSize(),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.horizontalGradient(
                        colors = if (isComputing) {
                            listOf(Color(0xFF2D4A00), Color(0xFF1A3000))
                        } else {
                            listOf(Color(0xFF1C1040), Color(0xFF150D30))
                        }
                    )
                )
                .padding(24.dp),
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                Icon(
                    if (isComputing) Icons.Default.Memory else Icons.Default.PlayArrow,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(48.dp),
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    text = if (isComputing) "Contributing Compute…" else "Ready to Contribute",
                    color = Color.White,
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )

                healthStatus?.let {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Battery: ${it.batteryLevel}% ${if (it.isCharging) "⚡" else ""} | Internet: ${if (it.internetAvailable) "✓" else "✗"}",
                        color = Color.White.copy(alpha = 0.8f),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }

                Spacer(Modifier.height(16.dp))

                Button(
                    onClick = { if (isComputing) onStop() else onStart() },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isComputing) Color(0xFFF87171) else Color(0xFFCDFF00)
                    ),
                    shape = RoundedCornerShape(16.dp),
                    modifier = Modifier.fillMaxWidth(0.7f).height(48.dp),
                ) {
                    Text(
                        if (isComputing) "Stop Contributing" else "Start Contributing",
                        fontWeight = FontWeight.Bold,
                        color = if (isComputing) Color.White else Color.Black,
                    )
                }
            }
        }
    }
}

@Composable
private fun StatCard(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    label: String,
    value: String,
    color: Color,
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(icon, null, tint = color, modifier = Modifier.size(28.dp))
            Spacer(Modifier.height(8.dp))
            Text(value, fontSize = 24.sp, fontWeight = FontWeight.Bold)
            Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun MiniStat(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
