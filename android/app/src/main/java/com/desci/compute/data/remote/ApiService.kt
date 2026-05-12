package com.desci.compute.data.remote

import com.desci.compute.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ──
    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): Response<UserResponse>

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): Response<TokenResponse>

    // ── Devices ──
    @POST("devices/register")
    suspend fun registerDevice(@Body body: DeviceRegisterRequest): Response<DeviceResponse>

    @POST("devices/heartbeat")
    suspend fun heartbeat(@Body body: HeartbeatRequest): Response<Unit>

    @GET("devices/")
    suspend fun getDevices(): Response<List<DeviceResponse>>

    // ── Tasks ──
    @GET("tasks/task")
    suspend fun getTask(@Query("device_id") deviceId: String): Response<TaskAssignment?>

    @POST("tasks/submit")
    suspend fun submitResult(@Body body: TaskSubmission): Response<SubmitResponse>

    // ── Jobs ──
    @GET("jobs/")
    suspend fun getJobs(): Response<List<JobResponse>>

    // ── Leaderboard ──
    @GET("leaderboard/")
    suspend fun getLeaderboard(@Query("limit") limit: Int = 50): Response<LeaderboardResponse>

    // ── Stats ──
    @GET("stats/")
    suspend fun getStats(): Response<PlatformStats>

    // ── Events ──
    @POST("events/")
    suspend fun emitEvent(@Body body: EventRequest): Response<Unit>

    // ── Campaigns ──
    @GET("campaigns/active")
    suspend fun getActiveCampaigns(): Response<CampaignsListResponse>

    @GET("campaigns/{id}")
    suspend fun getCampaignDetail(@Path("id") id: String): Response<CampaignDetailResponse>

    @GET("campaigns/{id}/leaderboard")
    suspend fun getCampaignLeaderboard(@Path("id") id: String): Response<CampaignLeaderboardResponse>

    @POST("campaigns/{id}/join")
    suspend fun joinCampaign(@Path("id") id: String): Response<JoinCampaignResponse>

    // ── Treasury ──
    @GET("treasury/balance")
    suspend fun getTreasuryBalance(): Response<TreasuryBalanceResponse>

    // ── User Rankings ──
    @GET("user/rankings")
    suspend fun getUserRankings(): Response<UserRankingsResponse>
}
