package com.desci.compute.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Auth ──

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    @SerialName("wallet_address") val walletAddress: String? = null,
    @SerialName("referral_code") val referralCode: String? = null,
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
)

@Serializable
data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String,
    @SerialName("user_id") val userId: String,
)

@Serializable
data class UserResponse(
    val id: String,
    val email: String,
    @SerialName("wallet_address") val walletAddress: String? = null,
    @SerialName("total_score") val totalScore: Double = 0.0,
    @SerialName("referral_code") val referralCode: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
)

// ── Device ──

@Serializable
data class DeviceRegisterRequest(
    @SerialName("device_type") val deviceType: String = "android",
    @SerialName("cpu_cores") val cpuCores: Int,
    val ram: Int,
    @SerialName("device_power_factor") val devicePowerFactor: Double = 1.0,
)

@Serializable
data class HeartbeatRequest(
    @SerialName("device_id") val deviceId: String,
    val status: String,
    @SerialName("cpu_load") val cpuLoad: Double? = null,
    @SerialName("memory_usage") val memoryUsage: Double? = null,
)

@Serializable
data class DeviceResponse(
    val id: String,
    @SerialName("device_type") val deviceType: String,
    @SerialName("device_power_factor") val devicePowerFactor: Double,
    @SerialName("cpu_cores") val cpuCores: Int,
    val ram: Int,
    val status: String,
    @SerialName("last_seen") val lastSeen: String,
)

// ── Task ──

@Serializable
data class TaskAssignment(
    val id: String,
    @SerialName("job_id") val jobId: String,
    @SerialName("template_type") val templateType: String,
    @SerialName("parameters_json") val parametersJson: String,
    @SerialName("range_start") val rangeStart: Int? = null,
    @SerialName("range_end") val rangeEnd: Int? = null,
    @SerialName("chunk_reference") val chunkReference: String? = null,
    @SerialName("reward_multiplier") val rewardMultiplier: Double = 1.0,
)

@Serializable
data class TaskSubmission(
    @SerialName("task_id") val taskId: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("result_json") val resultJson: String,
)

@Serializable
data class SubmitResponse(
    val status: String,
    val validated: Boolean = false,
)

// ── Job ──

@Serializable
data class JobResponse(
    val id: String,
    @SerialName("owner_id") val ownerId: String,
    val name: String,
    @SerialName("template_type") val templateType: String,
    @SerialName("parameters_json") val parametersJson: String,
    val priority: Int,
    @SerialName("reward_multiplier") val rewardMultiplier: Double,
    @SerialName("active_workers") val activeWorkers: Int,
    @SerialName("required_workers") val requiredWorkers: Int,
    @SerialName("validation_strategy") val validationStrategy: String,
    val status: String,
    @SerialName("created_at") val createdAt: String,
)

// ── Leaderboard ──

@Serializable
data class LeaderboardEntry(
    @SerialName("user_id") val userId: String,
    val email: String,
    val score: Double,
    val rank: Int,
)

@Serializable
data class LeaderboardResponse(
    val leaderboard: List<LeaderboardEntry>,
)

// ── Stats ──

@Serializable
data class PlatformStats(
    @SerialName("total_users") val totalUsers: Int,
    @SerialName("active_devices") val activeDevices: Int,
    @SerialName("total_jobs") val totalJobs: Int,
    @SerialName("active_jobs") val activeJobs: Int,
    @SerialName("completed_tasks") val completedTasks: Int,
    @SerialName("pending_tasks") val pendingTasks: Int,
    @SerialName("total_compute_hours") val totalComputeHours: Double,
    @SerialName("avg_reward_multiplier") val avgRewardMultiplier: Double,
)

// ── Events ──

@Serializable
data class EventRequest(
    @SerialName("event_name") val eventName: String,
    @SerialName("metadata_json") val metadataJson: String = "{}",
)

// ── Campaigns ──

@Serializable
data class CampaignResponse(
    val id: String,
    val name: String,
    @SerialName("campaign_type") val campaignType: String,
    val priority: String,
    val status: String,
    val reasoning: String? = null,
    @SerialName("reward_pool") val rewardPool: Double = 0.0,
    val multiplier: Double = 1.0,
    @SerialName("duration_hours") val durationHours: Int = 24,
    val participants: Int = 0,
    @SerialName("torque_primitives") val torquePrimitives: List<String> = emptyList(),
    @SerialName("start_time") val startTime: String? = null,
    @SerialName("end_time") val endTime: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class CampaignsListResponse(
    val campaigns: List<CampaignResponse>,
    val total: Int = 0,
)

@Serializable
data class CampaignDetailResponse(
    val id: String,
    val name: String,
    @SerialName("campaign_type") val campaignType: String,
    val priority: String,
    val status: String,
    val reasoning: String? = null,
    @SerialName("reward_pool") val rewardPool: Double = 0.0,
    val multiplier: Double = 1.0,
    @SerialName("duration_hours") val durationHours: Int = 24,
    val participants: Int = 0,
    @SerialName("start_time") val startTime: String? = null,
    @SerialName("end_time") val endTime: String? = null,
    val leaderboard: List<CampaignLeaderboardEntry> = emptyList(),
    @SerialName("my_rank") val myRank: Int? = null,
    @SerialName("my_score") val myScore: Double? = null,
    @SerialName("my_reward") val myReward: Double? = null,
)

@Serializable
data class CampaignLeaderboardEntry(
    @SerialName("user_id") val userId: String,
    val email: String? = null,
    val wallet: String? = null,
    val score: Double = 0.0,
    @SerialName("validated_units") val validatedUnits: Int = 0,
    val rank: Int = 0,
    @SerialName("reward_earned") val rewardEarned: Double = 0.0,
    @SerialName("joined_at") val joinedAt: String? = null,
)

@Serializable
data class CampaignLeaderboardResponse(
    @SerialName("campaign_id") val campaignId: String,
    val leaderboard: List<CampaignLeaderboardEntry>,
)

@Serializable
data class JoinCampaignResponse(
    val success: Boolean,
    val message: String? = null,
    val error: String? = null,
)

// ── Treasury ──

@Serializable
data class TreasuryBalanceResponse(
    @SerialName("sol_balance") val solBalance: Double = 0.0,
    @SerialName("treasury_wallet") val treasuryWallet: String? = null,
    @SerialName("total_deposits") val totalDeposits: Double = 0.0,
    @SerialName("total_rewards_distributed") val totalRewardsDistributed: Double = 0.0,
    @SerialName("ledger_balance") val ledgerBalance: Double = 0.0,
    @SerialName("utilization_rate") val utilizationRate: Double = 0.0,
)

// ── User Rankings ──

@Serializable
data class UserRankingEntry(
    @SerialName("campaign_id") val campaignId: String,
    @SerialName("campaign_name") val campaignName: String,
    @SerialName("campaign_status") val campaignStatus: String,
    val rank: Int = 0,
    val score: Double = 0.0,
    @SerialName("validated_units") val validatedUnits: Int = 0,
    @SerialName("reward_earned_sol") val rewardEarnedSol: Double = 0.0,
    @SerialName("joined_at") val joinedAt: String? = null,
)

@Serializable
data class UserRankingsResponse(
    @SerialName("total_campaigns") val totalCampaigns: Int = 0,
    @SerialName("total_rewards_sol") val totalRewardsSol: Double = 0.0,
    val rankings: List<UserRankingEntry> = emptyList(),
)
