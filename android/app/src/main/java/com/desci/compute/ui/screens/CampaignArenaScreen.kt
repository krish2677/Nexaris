package com.desci.compute.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.desci.compute.data.model.CampaignLeaderboardEntry
import com.desci.compute.data.model.CampaignResponse
import com.desci.compute.ui.viewmodel.CampaignViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import java.time.Instant
import java.time.temporal.ChronoUnit

// Theme colors — Neon Lime + Dark Purple
private val LimeColor = Color(0xFFCDFF00)
private val AmberColor = Color(0xFFFBBF24)
private val PurpleColor = Color(0xFF8B5CF6)
private val GreenColor = Color(0xFF34D399)
private val RedColor = Color(0xFFF87171)

private val priorityColors = mapOf(
    "critical" to RedColor,
    "high" to AmberColor,
    "medium" to LimeColor,
    "low" to GreenColor,
)

private val typeEmojis = mapOf(
    "supply_balancing" to "⚡", "retention" to "👥",
    "streak" to "🔥", "new_contributor" to "🆕",
    "referral" to "🎯", "dataset_completion" to "📊",
    "reliability" to "🛡️", "time_based" to "⏰",
    "experimental" to "🧪",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CampaignArenaScreen(
    viewModel: CampaignViewModel = hiltViewModel(),
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("🏟️ Campaign Arena", fontWeight = FontWeight.Bold)
                        Text(
                            "${state.campaigns.size} active competitions",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = {
                        if (state.selectedCampaign != null) viewModel.clearSelection()
                        else onBack()
                    }) {
                        Icon(Icons.Default.ArrowBack, "Back")
                    }
                },
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(vertical = 12.dp),
        ) {
            // Error banner
            state.error?.let { error ->
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                        shape = RoundedCornerShape(12.dp),
                    ) {
                        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Warning, null, tint = MaterialTheme.colorScheme.error)
                            Spacer(Modifier.width(8.dp))
                            Text(error, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
                            IconButton(onClick = { viewModel.clearError() }) {
                                Icon(Icons.Default.Close, "Dismiss", Modifier.size(18.dp))
                            }
                        }
                    }
                }
            }

            if (state.selectedCampaign != null) {
                // ── Campaign Detail View ──
                val c = state.selectedCampaign!!

                item {
                    CampaignDetailHeader(
                        name = c.name,
                        type = c.campaignType,
                        priority = c.priority,
                        reasoning = c.reasoning,
                        rewardPool = c.rewardPool,
                        multiplier = c.multiplier,
                        participants = c.participants,
                        durationHours = c.durationHours,
                        endTime = c.endTime,
                        myRank = c.myRank,
                        myScore = c.myScore,
                    )
                }

                // Join button
                if (c.myRank == null && c.status == "active") {
                    item {
                        Button(
                            onClick = { viewModel.joinCampaign(c.id) },
                            enabled = !state.isJoining,
                            modifier = Modifier.fillMaxWidth().height(52.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = LimeColor),
                            shape = RoundedCornerShape(16.dp),
                        ) {
                            Text(
                                if (state.isJoining) "Joining…" else "🏆 Join Competition",
                                fontWeight = FontWeight.Bold,
                                color = Color.Black,
                                fontSize = 16.sp,
                            )
                        }
                    }
                }

                // Leaderboard
                item {
                    Text(
                        "🏆 Live Leaderboard",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }

                if (c.leaderboard.isEmpty()) {
                    item {
                        Card(
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                            ),
                        ) {
                            Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                                Text("No participants yet — be the first!", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                } else {
                    itemsIndexed(c.leaderboard) { index, entry ->
                        LeaderboardRow(entry = entry, index = index)
                    }
                }
            } else {
                // ── My Stats ──
                state.rankings?.let { r ->
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatMiniCard(
                                modifier = Modifier.weight(1f),
                                emoji = "🏆",
                                value = "${r.totalCampaigns}",
                                label = "Campaigns",
                            )
                            StatMiniCard(
                                modifier = Modifier.weight(1f),
                                emoji = "💰",
                                value = String.format("%.4f", r.totalRewardsSol),
                                label = "SOL Earned",
                            )
                        }
                    }
                }

                // Treasury balance
                state.treasury?.let { t ->
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                            ),
                        ) {
                            Row(
                                Modifier.padding(16.dp).fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column {
                                    Text("Treasury Pool", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text(
                                        String.format("%.4f SOL", t.solBalance),
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 20.sp,
                                        color = AmberColor,
                                    )
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("Distributed", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text(
                                        String.format("%.4f SOL", t.totalRewardsDistributed),
                                        fontWeight = FontWeight.SemiBold,
                                        color = GreenColor,
                                    )
                                }
                            }
                        }
                    }
                }

                // ── Campaign List ──
                item {
                    Text(
                        "Active Competitions",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                }

                if (state.campaigns.isEmpty()) {
                    item {
                        Card(
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                            ),
                        ) {
                            Column(
                                Modifier.fillMaxWidth().padding(48.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                            ) {
                                Text("🏟️", fontSize = 48.sp)
                                Spacer(Modifier.height(12.dp))
                                Text(
                                    "No active campaigns",
                                    fontWeight = FontWeight.SemiBold,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                                Text(
                                    "The AI agent is analyzing the network…",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                                )
                            }
                        }
                    }
                } else {
                    items(state.campaigns) { campaign ->
                        CampaignCard(
                            campaign = campaign,
                            onClick = { viewModel.selectCampaign(campaign.id) },
                        )
                    }
                }
            }

            item { Spacer(Modifier.height(24.dp)) }
        }
    }
}

@Composable
private fun CampaignCard(campaign: CampaignResponse, onClick: () -> Unit) {
    val pColor = priorityColors[campaign.priority] ?: LimeColor
    val emoji = typeEmojis[campaign.campaignType] ?: "⚡"

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .animateContentSize(),
        shape = RoundedCornerShape(16.dp),
    ) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            // Type icon
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(pColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(emoji, fontSize = 22.sp)
            }

            Spacer(Modifier.width(14.dp))

            Column(Modifier.weight(1f)) {
                Text(campaign.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    "${campaign.campaignType.replace("_", " ")} · ${campaign.participants} participants · ${campaign.multiplier}x",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Column(horizontalAlignment = Alignment.End) {
                Text(
                    String.format("%.0f", campaign.rewardPool),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = AmberColor,
                )
                campaign.endTime?.let {
                    CountdownText(endTime = it)
                }
            }
        }
    }
}

@Composable
private fun CampaignDetailHeader(
    name: String, type: String, priority: String, reasoning: String?,
    rewardPool: Double, multiplier: Double, participants: Int,
    durationHours: Int, endTime: String?, myRank: Int?, myScore: Double?,
) {
    val pColor = priorityColors[priority] ?: LimeColor
    val emoji = typeEmojis[type] ?: "⚡"

    Card(
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.horizontalGradient(
                        listOf(Color(0xFF1C1040), Color(0xFF150D30))
                    )
                )
                .padding(24.dp),
        ) {
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(emoji, fontSize = 28.sp)
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(name, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text(
                            type.replace("_", " ").replaceFirstChar { it.uppercase() },
                            color = pColor,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }

                reasoning?.let {
                    Spacer(Modifier.height(12.dp))
                    Text("\"$it\"", color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Light)
                }

                Spacer(Modifier.height(16.dp))

                // Reward pool
                Text(
                    String.format("%.0f tokens", rewardPool),
                    color = AmberColor,
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 32.sp,
                )

                Spacer(Modifier.height(12.dp))

                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    InfoChip("👥 $participants")
                    InfoChip("⚡ ${multiplier}x")
                    InfoChip("⏱ ${durationHours}h")
                    endTime?.let { InfoChip(endTime = it) }
                }

                // My stats
                if (myRank != null || myScore != null) {
                    Spacer(Modifier.height(12.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        myRank?.let {
                            Text("Your rank: #$it", color = LimeColor, fontWeight = FontWeight.Bold)
                        }
                        myScore?.let {
                            Text("Score: ${String.format("%.1f", it)}", color = AmberColor, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LeaderboardRow(entry: CampaignLeaderboardEntry, index: Int) {
    val medal = when (index) { 0 -> "🥇"; 1 -> "🥈"; 2 -> "🥉"; else -> "#${entry.rank}" }
    val bgColor = when {
        index == 0 -> Color(0xFFCDFF00).copy(alpha = 0.08f)
        index < 3 -> Color(0xFFC0C0C0).copy(alpha = 0.06f)
        else -> Color.Transparent
    }

    Card(
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = bgColor),
    ) {
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(medal, fontSize = if (index < 3) 24.sp else 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.width(42.dp))
            Column(Modifier.weight(1f)) {
                Text(
                    entry.email ?: entry.userId.take(12) + "…",
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                entry.wallet?.let {
                    Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    String.format("%.1f", entry.score),
                    fontWeight = FontWeight.Bold,
                    color = LimeColor,
                )
                Text(
                    "${entry.validatedUnits} tasks",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (entry.rewardEarned > 0) {
                Spacer(Modifier.width(12.dp))
                Text(
                    "${entry.rewardEarned} SOL",
                    fontWeight = FontWeight.SemiBold,
                    color = AmberColor,
                    fontSize = 12.sp,
                )
            }
        }
    }
}

@Composable
private fun StatMiniCard(modifier: Modifier = Modifier, emoji: String, value: String, label: String) {
    Card(modifier = modifier, shape = RoundedCornerShape(16.dp)) {
        Column(
            Modifier.padding(16.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(emoji, fontSize = 24.sp)
            Spacer(Modifier.height(4.dp))
            Text(value, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun InfoChip(text: String? = null, endTime: String? = null) {
    if (endTime != null) {
        var remaining by remember { mutableStateOf("") }
        LaunchedEffect(endTime) {
            while (isActive) {
                try {
                    val end = Instant.parse(endTime)
                    val now = Instant.now()
                    val secs = ChronoUnit.SECONDS.between(now, end)
                    remaining = if (secs <= 0) "Ended" else {
                        val h = secs / 3600; val m = (secs % 3600) / 60; val s = secs % 60
                        "${h}h ${m}m ${s}s"
                    }
                } catch (_: Exception) { remaining = "—" }
                delay(1000)
            }
        }
        Text(
            "⏱ $remaining",
            color = Color.White.copy(alpha = 0.9f),
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
        )
    } else if (text != null) {
        Text(text, color = Color.White.copy(alpha = 0.9f), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun CountdownText(endTime: String) {
    var remaining by remember { mutableStateOf("") }
    LaunchedEffect(endTime) {
        while (isActive) {
            try {
                val end = Instant.parse(endTime)
                val now = Instant.now()
                val secs = ChronoUnit.SECONDS.between(now, end)
                remaining = if (secs <= 0) "Ended" else {
                    val h = secs / 3600; val m = (secs % 3600) / 60
                    "${h}h ${m}m"
                }
            } catch (_: Exception) { remaining = "—" }
            delay(1000)
        }
    }
    Text(
        remaining,
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.Bold,
        color = AmberColor.copy(alpha = 0.9f),
    )
}
