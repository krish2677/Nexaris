package com.desci.compute.data.local

import android.content.Context
import androidx.room.*

@Entity(tableName = "compute_history")
data class ComputeHistoryEntity(
    @PrimaryKey val taskId: String,
    val jobId: String,
    val templateType: String,
    val status: String,
    val resultJson: String? = null,
    val startedAt: Long = System.currentTimeMillis(),
    val completedAt: Long? = null,
)

@Dao
interface ComputeHistoryDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(entry: ComputeHistoryEntity)

    @Query("SELECT * FROM compute_history ORDER BY startedAt DESC LIMIT :limit")
    suspend fun getRecent(limit: Int = 50): List<ComputeHistoryEntity>

    @Query("SELECT COUNT(*) FROM compute_history WHERE status = 'completed'")
    suspend fun getCompletedCount(): Int

    @Query("SELECT COUNT(*) FROM compute_history")
    suspend fun getTotalCount(): Int

    @Query("SELECT * FROM compute_history WHERE status = 'pending_submit' ORDER BY startedAt ASC")
    suspend fun getPendingSubmissions(): List<ComputeHistoryEntity>

    @Query("DELETE FROM compute_history WHERE startedAt < :before")
    suspend fun cleanup(before: Long)
}

@Database(entities = [ComputeHistoryEntity::class], version = 2, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun computeHistoryDao(): ComputeHistoryDao

    companion object {
        @Suppress("DEPRECATION")
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "desci_compute.db")
                .fallbackToDestructiveMigration()
                .build()
    }
}
