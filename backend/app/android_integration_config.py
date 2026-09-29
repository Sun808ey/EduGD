"""Identifiers for the pilot Android integration; no device-wide emergency allowlist."""

DPC_APPLICATION_ID = "io.github.sun808ey.edugd.dpc"
INITIAL_EDUCATIONAL_APPS = frozenset(
    {
        "com.google.android.apps.classroom",
        "com.moodle.moodlemobile",
        "org.khanacademy.android",
        "org.wikipedia",
    }
)
AOSP_GOOGLE_EMULATOR_CANDIDATES = frozenset(
    {
        "com.android.dialer",
        "com.google.android.dialer",
        "com.android.emergency",
        "com.android.systemui",
    }
)
SYSTEM_UI_PACKAGE = "com.android.systemui"
DISCOVERY_ROLES = frozenset(
    {"action_dial", "action_call_emergency", "default_dialer", "emergency_information"}
)
