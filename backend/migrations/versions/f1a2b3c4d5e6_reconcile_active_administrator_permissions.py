"""Reconcile the complete permission set for active administrators.

Revision ID: f1a2b3c4d5e6
Revises: e2a6c8d4f0b1
"""

from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e2a6c8d4f0b1"
branch_labels = None
depends_on = None

_PERMISSIONS = (
    "administrator.manage",
    "enrollment_token.issue",
    "enrollment_token.revoke",
    "device_credential.revoke",
    "policy.assign",
    "device.control",
    "policy.manage",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    permissions = ", ".join(f"'{permission}'" for permission in _PERMISSIONS)
    bind.exec_driver_sql(
        f"""
        DO $$
        DECLARE
            administrator_row RECORD;
            permission_name TEXT;
        BEGIN
            FOR administrator_row IN
                SELECT id
                FROM administrators
                WHERE status = 'active'
            LOOP
                FOREACH permission_name IN ARRAY ARRAY[{permissions}]
                LOOP
                    INSERT INTO administrator_permissions (
                        administrator_id,
                        permission,
                        trusted_operator_subject,
                        reason
                    ) VALUES (
                        administrator_row.id,
                        permission_name,
                        'system:administrator-permission-reconciliation',
                        'all active authenticated administrators retain full control access'
                    )
                    ON CONFLICT (administrator_id, permission) DO NOTHING;

                    IF FOUND THEN
                        INSERT INTO administrator_authentication_events (
                            event_uuid,
                            administrator_id,
                            category,
                            trusted_operator_subject,
                            reason
                        ) VALUES (
                            md5(
                                administrator_row.id::text || ':' ||
                                permission_name || ':' ||
                                clock_timestamp()::text
                            )::uuid,
                            administrator_row.id,
                            'permission_granted',
                            'system:administrator-permission-reconciliation',
                            'all active authenticated administrators retain full control access'
                        );
                    END IF;
                END LOOP;
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Permission rows are retained on downgrade so rollback cannot silently
    # revoke administrator access or erase its audit history.
    pass
