# Task review lifecycle columns

The 2026-10-08 revision persists reviewer identity, decision time and optional notes. Approval continues to use `is_approved`; an unapproved task with a review time is rejected, and one without a review time is pending. Approved legacy tasks remain approved.

For a new database, SQLAlchemy creates these columns. Existing development databases use the startup schema-extension mechanism. The SQL file is a one-time migration for a managed deployment that does not use that mechanism: inspect existing columns before running it, and apply only absent columns. It has not been executed against a production database.

Historical `is_approved=false` rows cannot distinguish earlier rejections from unreviewed tasks. They remain pending until reviewed again; this revision does not invent historical reviewer identities or decision dates. The application checks reviewer roles through the admin API. The manual migration, like the existing development extension mechanism, does not add a foreign-key constraint for `reviewed_by`.
