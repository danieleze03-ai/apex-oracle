# ⚡ APEX ORACLE — AO-1.0
# Backup System
# Weekly database backup to Google Drive
# Trade history never lost
# "We Don't Predict. We Know."
# ─────────────────────────────────────────────────

import os
import json
import gzip
import shutil
from datetime import datetime, timedelta
from loguru import logger
from dotenv import load_dotenv
from data.database import (
    get_weekly_stats,
    get_last_trades,
    get_top_patterns,
)

load_dotenv()

# ─────────────────────────────────────────────────
# BACKUP SETTINGS
# ─────────────────────────────────────────────────

BACKUP_FOLDER    = "backups"
GDRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
MAX_LOCAL_BACKUPS= 4   # Keep last 4 weeks locally


# ─────────────────────────────────────────────────
# LOCAL BACKUP
# ─────────────────────────────────────────────────

def ensure_backup_folder():
    """Create backup folder if not exists"""
    os.makedirs(BACKUP_FOLDER, exist_ok=True)


def create_local_backup() -> dict:
    """
    Create local backup of all trading data

    Returns:
    {
        "success":   True,
        "filename":  "backup_2026_W23.json.gz",
        "path":      "backups/backup_2026_W23.json.gz",
        "size":      "12.5 KB",
    }
    """
    try:
        ensure_backup_folder()

        week    = datetime.now().strftime("%Y_W%W")
        filename= f"apex_oracle_backup_{week}.json"
        gz_name = f"{filename}.gz"
        path    = os.path.join(BACKUP_FOLDER, gz_name)

        logger.info(f"💾 Creating backup: {gz_name}")

        # ── Gather all data ───────────────────────
        weekly  = get_weekly_stats()
        trades  = get_last_trades(500)   # Last 500 trades
        patterns= get_top_patterns(20)

        # Load strategy config if exists
        strategy = {}
        if os.path.exists("strategy_config.json"):
            with open("strategy_config.json", "r") as f:
                strategy = json.load(f)

        backup_data = {
            "bot":            "APEX ORACLE",
            "version":        "AO-1.0",
            "backup_date":    datetime.now().isoformat(),
            "week":           week,
            "weekly_stats":   weekly,
            "trades":         trades,
            "top_patterns":   patterns,
            "strategy":       strategy,
            "total_trades":   len(trades),
        }

        # ── Save as compressed JSON ───────────────
        json_str = json.dumps(backup_data, indent=2, default=str)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(json_str)

        # Get file size
        size_bytes = os.path.getsize(path)
        size_kb    = round(size_bytes / 1024, 1)

        logger.success(
            f"✅ Local backup created: {gz_name} ({size_kb} KB)"
        )

        # ── Clean old backups ─────────────────────
        cleanup_old_backups()

        return {
            "success":  True,
            "filename": gz_name,
            "path":     path,
            "size":     f"{size_kb} KB",
            "trades":   len(trades),
        }

    except Exception as e:
        logger.error(f"❌ Local backup error: {e}")
        return {"success": False, "error": str(e)}


def cleanup_old_backups():
    """Remove old backups keeping only last N weeks"""
    try:
        ensure_backup_folder()
        files = sorted([
            f for f in os.listdir(BACKUP_FOLDER)
            if f.endswith(".gz")
        ])

        while len(files) > MAX_LOCAL_BACKUPS:
            old_file = os.path.join(BACKUP_FOLDER, files[0])
            os.remove(old_file)
            logger.debug(f"🗑️ Removed old backup: {files[0]}")
            files.pop(0)

    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")


# ─────────────────────────────────────────────────
# GOOGLE DRIVE BACKUP
# ─────────────────────────────────────────────────

def upload_to_google_drive(file_path: str) -> dict:
    """
    Upload backup file to Google Drive
    Requires GOOGLE_DRIVE_FOLDER_ID in .env
    """
    try:
        if not GDRIVE_FOLDER_ID:
            logger.warning(
                "⚠️ GOOGLE_DRIVE_FOLDER_ID not set — "
                "skipping Drive upload"
            )
            return {"success": False, "reason": "No folder ID"}

        from google.oauth2          import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http   import MediaFileUpload

        # Check credentials file
        creds_file = "google_credentials.json"
        if not os.path.exists(creds_file):
            logger.warning(
                "⚠️ google_credentials.json not found — "
                "skipping Drive upload"
            )
            return {"success": False, "reason": "No credentials"}

        credentials = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service   = build("drive", "v3", credentials=credentials)
        file_name = os.path.basename(file_path)

        file_metadata = {
            "name":    file_name,
            "parents": [GDRIVE_FOLDER_ID],
        }

        media = MediaFileUpload(
            file_path,
            mimetype="application/gzip",
            resumable=True,
        )

        result = service.files().create(
            body        = file_metadata,
            media_body  = media,
            fields      = "id, name, size",
        ).execute()

        logger.success(
            f"☁️ Backup uploaded to Drive: "
            f"{result.get('name')} (ID: {result.get('id')})"
        )

        return {
            "success":   True,
            "file_id":   result.get("id"),
            "file_name": result.get("name"),
        }

    except Exception as e:
        logger.error(f"❌ Google Drive upload error: {e}")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────
# STRATEGY BACKUP
# ─────────────────────────────────────────────────

def backup_strategy() -> bool:
    """
    Backup current strategy config
    Saves versioned copy in backups folder
    """
    try:
        if not os.path.exists("strategy_config.json"):
            return True

        ensure_backup_folder()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        dest      = os.path.join(
            BACKUP_FOLDER,
            f"strategy_{timestamp}.json"
        )
        shutil.copy("strategy_config.json", dest)
        logger.debug(f"💾 Strategy backed up: {dest}")
        return True

    except Exception as e:
        logger.error(f"❌ Strategy backup error: {e}")
        return False


# ─────────────────────────────────────────────────
# RESTORE FROM BACKUP
# ─────────────────────────────────────────────────

def list_backups() -> list:
    """List all available backups"""
    try:
        ensure_backup_folder()
        files = sorted([
            f for f in os.listdir(BACKUP_FOLDER)
            if f.endswith(".gz")
        ], reverse=True)

        backups = []
        for f in files:
            path       = os.path.join(BACKUP_FOLDER, f)
            size_bytes = os.path.getsize(path)
            size_kb    = round(size_bytes / 1024, 1)
            backups.append({
                "filename": f,
                "path":     path,
                "size":     f"{size_kb} KB",
                "date":     f.replace("apex_oracle_backup_", "")
                             .replace(".json.gz", ""),
            })

        return backups

    except Exception as e:
        logger.error(f"❌ List backups error: {e}")
        return []


def restore_from_backup(filename: str) -> dict:
    """
    Restore strategy config from backup
    Does NOT restore trades (those stay in Supabase)
    """
    try:
        path = os.path.join(BACKUP_FOLDER, filename)

        if not os.path.exists(path):
            return {"success": False, "error": "Backup not found"}

        with gzip.open(path, "rt", encoding="utf-8") as f:
            backup_data = json.load(f)

        strategy = backup_data.get("strategy", {})
        if strategy:
            with open("strategy_config.json", "w") as f:
                json.dump(strategy, f, indent=2)
            logger.success(f"✅ Strategy restored from {filename}")
            return {
                "success":  True,
                "filename": filename,
                "trades":   backup_data.get("total_trades", 0),
            }

        return {"success": False, "error": "No strategy in backup"}

    except Exception as e:
        logger.error(f"❌ Restore error: {e}")
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────
# MASTER BACKUP RUNNER
# ─────────────────────────────────────────────────

def run_weekly_backup() -> dict:
    """
    Main backup function — runs every Sunday
    1. Create local backup
    2. Upload to Google Drive
    3. Backup strategy config
    4. Send Telegram alert
    """
    try:
        logger.info("💾 Starting weekly backup...")

        # ── Step 1: Local backup ──────────────────
        local = create_local_backup()

        if not local["success"]:
            return {"success": False, "error": "Local backup failed"}

        # ── Step 2: Google Drive (optional) ──────
        drive = {"success": False, "reason": "Skipped"}
        if GDRIVE_FOLDER_ID:
            drive = upload_to_google_drive(local["path"])

        # ── Step 3: Strategy backup ───────────────
        backup_strategy()

        # ── Step 4: Build result ──────────────────
        result = {
            "success":      True,
            "filename":     local["filename"],
            "size":         local["size"],
            "trades":       local["trades"],
            "drive_upload": drive["success"],
            "timestamp":    datetime.now().isoformat(),
        }

        logger.success(
            f"✅ Weekly backup complete! "
            f"{local['trades']} trades | "
            f"Size: {local['size']} | "
            f"Drive: {drive['success']}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Weekly backup error: {e}")
        return {"success": False, "error": str(e)}


def should_run_backup() -> bool:
    """
    Check if backup should run
    Runs every Sunday at 1am WAT
    """
    now = datetime.now()
    return (
        now.weekday() == 6 and   # Sunday
        now.hour == 1 and        # 1am
        now.minute < 30          # Within first 30 mins
    )


# ─────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n⚡ APEX ORACLE — Backup System Test")
    print("─" * 45)

    print("\nTesting local backup...")
    result = create_local_backup()

    if result["success"]:
        print(f"✅ Backup created!")
        print(f"   File:   {result['filename']}")
        print(f"   Size:   {result['size']}")
        print(f"   Trades: {result['trades']}")
    else:
        print(f"❌ Backup failed: {result.get('error')}")

    print("\nListing backups...")
    backups = list_backups()
    for b in backups:
        print(f"  → {b['filename']} ({b['size']})")

    print("\n✅ Backup system test complete!")