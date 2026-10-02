package io.github.sun808ey.edugd.dpc.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(entities = [DeviceIdentityEntity::class, PolicyEnvelopeEntity::class, PolicyStateEntity::class, SuspensionJournalEntity::class, OutboxEntity::class, AuditEventEntity::class, CapabilityReportEntity::class], version = 4, exportSchema = false)
abstract class DpcDatabase : RoomDatabase() {
    abstract fun dpcDao(): DpcDao
    companion object {
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE device_identity ADD COLUMN credentialAlgorithm TEXT NOT NULL DEFAULT ''")
                database.execSQL("ALTER TABLE device_identity ADD COLUMN apiOrigin TEXT NOT NULL DEFAULT ''")
                database.execSQL("ALTER TABLE device_identity ADD COLUMN serverTime TEXT NOT NULL DEFAULT ''")
            }
        }
        private val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE device_identity ADD COLUMN serverSigningKeyId TEXT NOT NULL DEFAULT ''")
                database.execSQL("ALTER TABLE device_identity ADD COLUMN serverSigningPublicKey TEXT NOT NULL DEFAULT ''")
                database.execSQL("ALTER TABLE device_identity ADD COLUMN serverSigningKeyFingerprint TEXT NOT NULL DEFAULT ''")
                database.execSQL("ALTER TABLE device_identity ADD COLUMN lastAcceptedServerTimeEpochSeconds INTEGER NOT NULL DEFAULT 0")
            }
        }
        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(database: SupportSQLiteDatabase) = Unit
        }
        @Volatile private var INSTANCE: DpcDatabase? = null
        fun getDatabase(context: Context): DpcDatabase = INSTANCE ?: synchronized(this) {
            INSTANCE ?: Room.databaseBuilder(context.applicationContext, DpcDatabase::class.java, "edugd_dpc.db").addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_3_4).build().also { INSTANCE = it }
        }
    }
}
