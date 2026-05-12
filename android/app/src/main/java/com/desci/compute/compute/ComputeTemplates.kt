package com.desci.compute.compute

import kotlinx.serialization.json.*
import java.security.MessageDigest
import java.nio.ByteBuffer
import kotlin.math.abs
import kotlin.math.min

/**
 * Client-side compute templates — identical logic to the backend
 * for deterministic verification.
 *
 * All templates include memory-safety bounds to prevent OOM on
 * resource-constrained Android devices.
 */
object ComputeTemplates {

    /**
     * Max iterations per task to prevent OOM / ANR on mobile.
     * The backend should chunk tasks smaller than this, but this
     * provides a hard safety net.
     */
    private const val MAX_RANGE_SIZE = 500_000
    private const val MAX_ROW_SUMS = 50_000  // cap for row-level results kept in memory

    fun execute(templateType: String, paramsJson: String, rangeStart: Int, rangeEnd: Int, chunkRef: String?): String {
        val json = Json { ignoreUnknownKeys = true }
        val params = json.parseToJsonElement(paramsJson).jsonObject

        // Hard-cap the range to avoid OOM
        val safeEnd = min(rangeEnd, rangeStart + MAX_RANGE_SIZE)

        val result = when (templateType) {
            "monte_carlo" -> monteCarlo(params, rangeStart, safeEnd)
            "dataset_stats" -> datasetStats(params, rangeStart, safeEnd)
            "matrix_compute" -> matrixCompute(params, rangeStart, safeEnd, chunkRef)
            else -> throw IllegalArgumentException("Unknown template: $templateType")
        }

        return Json.encodeToString(JsonObject.serializer(), result)
    }

    private fun monteCarlo(params: JsonObject, rangeStart: Int, rangeEnd: Int): JsonObject {
        val seed = params["seed"]?.jsonPrimitive?.long ?: 42L
        var insideCircle = 0
        val total = rangeEnd - rangeStart

        for (i in rangeStart until rangeEnd) {
            val hash = sha256(longToBytes(seed) + longToBytes(i.toLong()))
            val x = abs(bytesToDouble(hash.sliceArray(0..7))) % 1.0
            val y = abs(bytesToDouble(hash.sliceArray(8..15))) % 1.0
            if (x * x + y * y <= 1.0) insideCircle++
        }

        val piEstimate = if (total > 0) 4.0 * insideCircle / total else 0.0

        return buildJsonObject {
            put("inside_circle", insideCircle)
            put("total_points", total)
            put("pi_estimate", piEstimate)
            put("range_start", rangeStart)
            put("range_end", rangeEnd)
        }
    }

    private fun datasetStats(params: JsonObject, rangeStart: Int, rangeEnd: Int): JsonObject {
        val seed = params["seed"]?.jsonPrimitive?.long ?: 42L
        val columns = min(params["columns"]?.jsonPrimitive?.int ?: 4, 32)  // cap columns
        val totalRows = rangeEnd - rangeStart

        val sums = DoubleArray(columns)
        val sqSums = DoubleArray(columns)
        val mins = DoubleArray(columns) { Double.MAX_VALUE }
        val maxs = DoubleArray(columns) { Double.MIN_VALUE }

        for (i in rangeStart until rangeEnd) {
            val hash = sha256(longToBytes(seed) + longToBytes(i.toLong()))
            for (col in 0 until columns) {
                val offset = (col * 8) % (hash.size - 8)
                val raw = bytesToDouble(hash.sliceArray(offset until offset + 8))
                val value = abs(raw) % 1000.0
                sums[col] += value
                sqSums[col] += value * value
                if (value < mins[col]) mins[col] = value
                if (value > maxs[col]) maxs[col] = value
            }
        }

        val averages = sums.map { it / totalRows }
        val variances = (0 until columns).map {
            (sqSums[it] / totalRows) - (averages[it] * averages[it])
        }

        return buildJsonObject {
            put("row_count", totalRows)
            put("column_count", columns)
            put("sums", JsonArray(sums.map { JsonPrimitive(it) }))
            put("averages", JsonArray(averages.map { JsonPrimitive(it) }))
            put("mins", JsonArray(mins.map { JsonPrimitive(it) }))
            put("maxs", JsonArray(maxs.map { JsonPrimitive(it) }))
            put("variances", JsonArray(variances.map { JsonPrimitive(it) }))
            put("range_start", rangeStart)
            put("range_end", rangeEnd)
        }
    }

    private fun matrixCompute(params: JsonObject, rangeStart: Int, rangeEnd: Int, chunkRef: String?): JsonObject {
        val seed = params["seed"]?.jsonPrimitive?.long ?: 42L
        val matrixSize = min(params["matrix_size"]?.jsonPrimitive?.int ?: 64, 1024)  // cap size
        val rowCount = rangeEnd - rangeStart

        var blockSum = 0.0

        // Only keep individual row sums if the count is reasonable
        val keepRowSums = rowCount <= MAX_ROW_SUMS
        val rowSums = if (keepRowSums) ArrayList<Double>(rowCount) else null

        for (row in rangeStart until rangeEnd) {
            var rowSum = 0.0
            for (col in 0 until matrixSize) {
                val hashA = sha256(longToBytes(seed + 1) + longToBytes((row * matrixSize + col).toLong()))
                val hashB = sha256(longToBytes(seed) + longToBytes(col.toLong()))
                val a = bytesToDouble(hashA.sliceArray(0..7))
                val b = bytesToDouble(hashB.sliceArray(0..7))
                rowSum += a * b
            }
            rowSums?.add(rowSum)
            blockSum += rowSum
        }

        return buildJsonObject {
            put("block_sum", blockSum)
            put("block_mean", if (rowCount > 0) blockSum / (rowCount * matrixSize) else 0.0)
            if (rowSums != null) {
                put("row_sums", JsonArray(rowSums.map { JsonPrimitive(it) }))
            } else {
                put("row_sums_truncated", true)
            }
            put("rows_processed", rowCount)
            put("range_start", rangeStart)
            put("range_end", rangeEnd)
        }
    }

    // ── Crypto helpers ──

    private fun sha256(data: ByteArray): ByteArray =
        MessageDigest.getInstance("SHA-256").digest(data)

    private fun longToBytes(value: Long): ByteArray =
        ByteBuffer.allocate(8).putLong(value).array()

    private fun bytesToDouble(bytes: ByteArray): Double =
        ByteBuffer.wrap(bytes).double
}
