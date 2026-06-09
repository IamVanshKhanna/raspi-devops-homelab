---
name: backup-ops
description: Restic/B2 backup operations — list, verify, restore snapshots
version: 1.0.0
category: homelab
---

## Triggers
- "backup status"
- "list restic snapshots"
- "verify backup"
- "restore from backup"
- "when was last backup"

## Allowed Commands (read-only, no confirmation)
- `restic -r $RESTIC_REPOSITORY snapshots`
- `restic -r $RESTIC_REPOSITORY snapshots --latest 5`
- `restic -r $RESTIC_REPOSITORY snapshots --json`
- `restic -r $RESTIC_REPOSITORY check --read-data-subset=5%`
- `restic -r $RESTIC_REPOSITORY stats --mode raw-data`

## Allowed Actions (require confirmation)
- **Restore specific snapshot**: `restic -r $RESTIC_REPOSITORY restore <snapshot_id> --target /mnt/restore-test --dry-run`
- **Restore latest**: `restic -r $RESTIC_REPOSITORY restore latest --target /mnt/restore-test --dry-run`
- **Full restore (production)**: `restic -r $RESTIC_REPOSITORY restore latest --target /mnt/restore` (requires explicit "yes, restore to production")

## Forbidden
- `restic forget` (pruning)
- `restic prune`
- `restic init` (already initialized)
- Any `rm` or destructive commands

## Context Variables (from environment)
- `RESTIC_REPOSITORY`
- `RESTIC_PASSWORD`
- `B2_ACCOUNT_ID`
- `B2_ACCOUNT_KEY`

## Example Usage
> "Show me the last 3 restic snapshots"
> "Verify the backup repository integrity"
> "Restore the latest snapshot to /mnt/restore-test"
> "What's the size of the last backup?"