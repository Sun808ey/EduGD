package io.github.sun808ey.edugd.dpc.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        DeviceIdentityEntity::class,
        PolicyEnvelopeEntity::class,
        PolicyStateEntity::class,
        SuspensionJournalEntity::class,
        OutboxEntity::class,
        AuditEventEntity::class,
        CapabilityReportEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class DpcDatabase : RoomDatabase() {
    abstract fun dpcDao(): DpcDao

    companion object {
        @Volatile
        private var INSTANCE: DpcDatabase? = null

        fun getDatabase(context: Context): DpcDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    DpcDatabase::class.java,
                    "edugd_dpc.db"
                ).build().also { INSTANCE = it }
            }
        }
    }
}
