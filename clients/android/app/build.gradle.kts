plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "hu.finsync.spike"
    compileSdk = 36

    defaultConfig {
        applicationId = "hu.finsync.spike"
        minSdk = 26
        targetSdk = 36
        versionCode = 2
        versionName = "0.2-m2"
    }

    buildTypes {
        // Plain HTTP only in debug builds (the local API on the emulator's 10.0.2.2 or the LAN);
        // a release build reaches the API only over HTTPS (the tunnel of ADR 0007).
        getByName("debug") { manifestPlaceholders["cleartext"] = "true" }
        getByName("release") { manifestPlaceholders["cleartext"] = "false" }
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2025.05.01"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.core:core-ktx:1.16.0")
    // Sending with retry and backoff when a network is available (planned in technology-stack.md#android).
    implementation("androidx.work:work-runtime-ktx:2.10.1")
    testImplementation("junit:junit:4.13.2")
}
