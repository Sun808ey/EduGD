import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlinx.serialization)
    alias(libs.plugins.ksp)
}

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
if (keystorePropertiesFile.isFile) {
    keystorePropertiesFile.inputStream().use { stream ->
        keystoreProperties.load(stream)
    }
}

val requiredSigningProperties = listOf("storeFile", "storePassword", "keyAlias", "keyPassword")
val signingProperties = requiredSigningProperties.associateWith { propertyName ->
    keystoreProperties.getProperty(propertyName)?.takeIf { it.isNotBlank() }
}
val signingStoreFile = signingProperties["storeFile"]?.let(rootProject::file)
val releaseSigningConfigured =
    keystorePropertiesFile.isFile &&
        signingProperties.values.all { it != null } &&
        signingStoreFile?.isFile == true

android {
    namespace = "io.github.sun808ey.edugd.dpc"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.sun808ey.edugd.dpc"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-poc"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (releaseSigningConfigured) {
            create("release") {
                storeFile = signingStoreFile
                storePassword = signingProperties.getValue("storePassword")
                keyAlias = signingProperties.getValue("keyAlias")
                keyPassword = signingProperties.getValue("keyPassword")
            }
        }
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
        }
        release {
            isMinifyEnabled = true
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
}

val validateReleaseSigning = tasks.register("validateReleaseSigning") {
    group = "verification"
    description = "Validates the local signing configuration before packaging a release."

    doLast {
        if (!keystorePropertiesFile.isFile) {
            throw GradleException("Missing android-dpc/keystore.properties for release packaging.")
        }

        val missingProperties = signingProperties.filterValues { it == null }.keys
        if (missingProperties.isNotEmpty()) {
            throw GradleException(
                "Missing release signing properties: ${missingProperties.sorted().joinToString(", ")}"
            )
        }

        if (signingStoreFile?.isFile != true) {
            throw GradleException("The configured release keystore file does not exist.")
        }
    }
}

tasks.configureEach {
    if (name in setOf("assembleRelease", "bundleRelease", "packageRelease")) {
        dependsOn(validateReleaseSigning)
    }
    if (name != "validateReleaseSigning" && name.contains("Release")) {
        mustRunAfter(validateReleaseSigning)
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.work.runtime.ktx)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    implementation(libs.kotlinx.serialization.json)
    ksp(libs.androidx.room.compiler)

    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
