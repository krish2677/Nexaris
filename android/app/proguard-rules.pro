# Add project specific ProGuard rules here.
-keepattributes *Annotation*
-keep class com.desci.compute.data.model.** { *; }
-keep class kotlinx.serialization.** { *; }

# Retrofit
-keepattributes Signature
-keepattributes Exceptions
-keep class retrofit2.** { *; }

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
