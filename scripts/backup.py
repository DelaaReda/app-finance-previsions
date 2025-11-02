#!/usr/bin/env python3
"""
Backup and maintenance script for Finance Copilot
Addresses inspector's concern about backup strategy
"""
import os
import sys
import shutil
import tarfile
import datetime
from pathlib import Path
from typing import List

def get_backup_dirs() -> List[Path]:
    """Get directories that should be backed up."""
    backup_dirs = []
    
    # Data directory (most important)
    data_dir = Path("data")
    if data_dir.exists():
        backup_dirs.append(data_dir)
    
    # RAG store directory
    rag_dir = Path("data/rag")
    if rag_dir.exists():
        backup_dirs.append(rag_dir)
    
    # Logs directory
    logs_dir = Path("logs")
    if logs_dir.exists():
        backup_dirs.append(logs_dir)
    
    # Cache directory
    cache_dir = Path("cache")
    if cache_dir.exists():
        backup_dirs.append(cache_dir)
    
    return backup_dirs

def create_backup(backup_dir: Path = None, retention_days: int = 30) -> str:
    """
    Create a backup of critical data.
    
    Args:
        backup_dir: Directory to store backups (default: backups/)
        retention_days: Days to keep old backups
    
    Returns:
        Path to created backup file
    """
    if backup_dir is None:
        backup_dir = Path("backups")
    
    # Create backup directory
    backup_dir.mkdir(exist_ok=True)
    
    # Get timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"finance_copilot_backup_{timestamp}.tar.gz"
    backup_path = backup_dir / backup_filename
    
    # Get directories to backup
    dirs_to_backup = get_backup_dirs()
    
    if not dirs_to_backup:
        print("⚠️  No directories found to backup")
        return ""
    
    print(f"📦 Creating backup: {backup_path}")
    print(f"📁 Directories to backup: {len(dirs_to_backup)}")
    
    try:
        # Create tar.gz archive
        with tarfile.open(backup_path, "w:gz") as tar:
            for dir_path in dirs_to_backup:
                if dir_path.exists():
                    print(f"  + Adding {dir_path}")
                    tar.add(str(dir_path), arcname=dir_path.name)
                else:
                    print(f"  - Skipping {dir_path} (not found)")
        
        # Get backup size
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"✅ Backup created: {backup_path} ({size_mb:.1f} MB)")
        
        # Clean old backups
        clean_old_backups(backup_dir, retention_days)
        
        return str(backup_path)
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        if backup_path.exists():
            backup_path.unlink()
        return ""

def clean_old_backups(backup_dir: Path, retention_days: int):
    """Clean old backups based on retention policy."""
    print(f"🧹 Cleaning backups older than {retention_days} days...")
    
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    deleted_count = 0
    
    for backup_file in backup_dir.glob("finance_copilot_backup_*.tar.gz"):
        try:
            # Extract timestamp from filename
            # Format: finance_copilot_backup_20251102_143022.tar.gz
            filename = backup_file.name
            date_part = filename.replace("finance_copilot_backup_", "").replace(".tar.gz", "")
            backup_date = datetime.datetime.strptime(date_part, "%Y%m%d_%H%M%S")
            
            if backup_date < cutoff_date:
                backup_file.unlink()
                print(f"  - Deleted old backup: {filename}")
                deleted_count += 1
                
        except Exception as e:
            print(f"  ⚠️  Could not parse date for {backup_file.name}: {e}")
    
    if deleted_count > 0:
        print(f"  🗑️  Deleted {deleted_count} old backups")
    else:
        print(f"  ✅ No old backups to delete")

def restore_backup(backup_file: str, target_dir: Path = None) -> bool:
    """
    Restore from a backup file.
    
    Args:
        backup_file: Path to backup file to restore
        target_dir: Target directory (default: current directory)
    
    Returns:
        True if successful
    """
    backup_path = Path(backup_file)
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    if target_dir is None:
        target_dir = Path(".")
    
    print(f"🔄 Restoring from backup: {backup_file}")
    
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            # Extract all files
            tar.extractall(path=target_dir)
            print("✅ Backup restored successfully")
            return True
            
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

def list_backups(backup_dir: Path = None) -> List[Path]:
    """List available backups."""
    if backup_dir is None:
        backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("📁 No backups directory found")
        return []
    
    backups = list(backup_dir.glob("finance_copilot_backup_*.tar.gz"))
    backups.sort(reverse=True)  # Newest first
    
    if not backups:
        print("📭 No backups found")
        return []
    
    print(f"📋 Available backups ({len(backups)}):")
    for i, backup in enumerate(backups[:10], 1):  # Show last 10
        try:
            # Get file size
            size_mb = backup.stat().st_size / (1024 * 1024)
            
            # Get timestamp
            filename = backup.name
            date_part = filename.replace("finance_copilot_backup_", "").replace(".tar.gz", "")
            timestamp = datetime.datetime.strptime(date_part, "%Y%m%d_%H%M%S")
            
            print(f"  {i:2d}. {filename} ({size_mb:.1f} MB) - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"  {i:2d}. {backup.name}")
    
    if len(backups) > 10:
        print(f"     ... and {len(backups) - 10} more")
    
    return backups

def show_backup_stats():
    """Show backup statistics."""
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("📁 No backups directory")
        return
    
    backups = list(backup_dir.glob("finance_copilot_backup_*.tar.gz"))
    
    if not backups:
        print("📭 No backups found")
        return
    
    # Get total size
    total_size = sum(b.stat().st_size for b in backups)
    total_size_mb = total_size / (1024 * 1024)
    
    # Get date range
    dates = []
    for backup in backups:
        try:
            filename = backup.name
            date_part = filename.replace("finance_copilot_backup_", "").replace(".tar.gz", "")
            backup_date = datetime.datetime.strptime(date_part, "%Y%m%d_%H%M%S")
            dates.append(backup_date)
        except:
            continue
    
    if dates:
        oldest = min(dates)
        newest = max(dates)
        print(f"📊 Backup Statistics:")
        print(f"   Total backups: {len(backups)}")
        print(f"   Total size: {total_size_mb:.1f} MB")
        print(f"   Date range: {oldest.strftime('%Y-%m-%d')} to {newest.strftime('%Y-%m-%d')}")
    else:
        print(f"📊 Backup Statistics:")
        print(f"   Total backups: {len(backups)}")
        print(f"   Total size: {total_size_mb:.1f} MB")

def main():
    """Main backup utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Finance Copilot Backup Utility")
    parser.add_argument("action", choices=["create", "list", "restore", "clean", "stats"], 
                       help="Action to perform")
    parser.add_argument("--backup-file", "-f", help="Backup file to restore")
    parser.add_argument("--backup-dir", "-d", help="Backup directory (default: backups/)")
    parser.add_argument("--retention", "-r", type=int, default=30, 
                       help="Retention days (default: 30)")
    
    args = parser.parse_args()
    
    # Set backup directory
    backup_dir = Path(args.backup_dir) if args.backup_dir else Path("backups")
    
    if args.action == "create":
        backup_path = create_backup(backup_dir, args.retention)
        if backup_path:
            print(f"\n🎉 Backup created successfully: {backup_path}")
            return True
        else:
            print("\n❌ Backup creation failed")
            return False
    
    elif args.action == "list":
        list_backups(backup_dir)
        return True
    
    elif args.action == "restore":
        if not args.backup_file:
            print("❌ --backup-file required for restore action")
            return False
        
        success = restore_backup(args.backup_file)
        if success:
            print("\n🎉 Restore completed successfully")
            return True
        else:
            print("\n❌ Restore failed")
            return False
    
    elif args.action == "clean":
        clean_old_backups(backup_dir, args.retention)
        print("\n✅ Cleanup completed")
        return True
    
    elif args.action == "stats":
        show_backup_stats()
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)