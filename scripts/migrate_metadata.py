#!/usr/bin/env python3
"""
Metadata Migration Script

One-time migration of all existing metadata.json files from flat format
to comprehensive eBay-ready schema format.

Usage:
    python scripts/migrate_metadata.py
"""

import json
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema.migrator import MetadataMigrator, validate_migration


def find_listing_folders(base_path: Path) -> List[Path]:
    """
    Find all folders containing metadata.json files

    Args:
        base_path: Base directory to search

    Returns:
        List of folders with metadata.json
    """
    listing_folders = []

    for item in base_path.iterdir():
        if item.is_dir():
            metadata_file = item / 'metadata.json'
            if metadata_file.exists():
                # Skip if already migrated (check for schema_version)
                try:
                    with open(metadata_file) as f:
                        data = json.load(f)
                        if 'schema_version' in data:
                            print(f"⏩ Skipping {item.name} (already migrated)")
                            continue
                except (json.JSONDecodeError, KeyError):
                    pass

                listing_folders.append(item)

    return listing_folders


def backup_metadata(metadata_file: Path) -> Path:
    """
    Create backup of original metadata file

    Args:
        metadata_file: Path to metadata.json

    Returns:
        Path to backup file
    """
    backup_file = metadata_file.with_suffix('.json.backup')

    # If backup already exists, add timestamp
    if backup_file.exists():
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = metadata_file.parent / f'metadata.json.backup_{timestamp}'

    shutil.copy2(metadata_file, backup_file)
    return backup_file


def migrate_listing(folder: Path, migrator: MetadataMigrator) -> Dict[str, Any]:
    """
    Migrate a single listing folder

    Args:
        folder: Listing folder path
        migrator: MetadataMigrator instance

    Returns:
        Migration result dict
    """
    metadata_file = folder / 'metadata.json'

    # Load old metadata
    with open(metadata_file) as f:
        old_metadata = json.load(f)

    # Create backup
    backup_file = backup_metadata(metadata_file)

    # Migrate
    new_metadata = migrator.migrate(old_metadata)

    # Validate
    validation = validate_migration(old_metadata, new_metadata)

    # Save new metadata
    with open(metadata_file, 'w') as f:
        json.dump(new_metadata, f, indent=2, ensure_ascii=False)

    return {
        'folder': folder.name,
        'backup_file': backup_file.name,
        'validation': validation,
        'old_field_count': len(old_metadata),
        'new_field_count': len([k for k in new_metadata.keys() if new_metadata[k]])
    }


def print_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print migration summary

    Args:
        results: List of migration results
    """
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)

    total_migrated = len(results)
    successful = sum(1 for r in results if r['validation']['success'])

    print(f"\nTotal listings processed: {total_migrated}")
    print(f"Successfully migrated: {successful}")
    print(f"Failed validations: {total_migrated - successful}")

    if total_migrated > 0:
        print("\nPer-Listing Details:")
        print("-" * 70)

        for result in results:
            folder = result['folder']
            validation = result['validation']

            status = "✓" if validation['success'] else "✗"
            print(f"{status} {folder}")
            print(f"   Backup: {result['backup_file']}")
            print(f"   Old fields: {validation['old_field_count']}, "
                  f"Tracked: {validation['tracked_field_count']}")

            if not validation['success']:
                print(f"   ⚠️  Missing fields: {validation['missing_fields']}")

            print()

    print("=" * 70)
    print("\nMigration complete!")
    print("\nNext steps:")
    print("  1. Review migrated metadata.json files")
    print("  2. Install dependencies: pip install -r requirements.txt")
    print("  3. Set up .env file with API keys (ANTHROPIC_API_KEY)")
    print("  4. Run enrichment: python -m src.cli.main enrich <listing_name>")
    print("\nBackups saved as metadata.json.backup in each folder")
    print("=" * 70 + "\n")


def main():
    """Main migration workflow"""
    # Get base path (parent of scripts folder)
    base_path = Path(__file__).parent.parent

    print("=" * 70)
    print("METADATA MIGRATION TOOL")
    print("=" * 70)
    print(f"\nSearching for listings in: {base_path}")

    # Find all listing folders
    listing_folders = find_listing_folders(base_path)

    if not listing_folders:
        print("\n⚠️  No unmigrated listings found.")
        print("All metadata files already migrated or no metadata.json files found.")
        return

    print(f"\nFound {len(listing_folders)} listing(s) to migrate:")
    for folder in listing_folders:
        print(f"  • {folder.name}")

    # Confirm
    response = input("\nProceed with migration? [y/N]: ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        return

    print("\n" + "-" * 70)
    print("Starting migration...")
    print("-" * 70 + "\n")

    # Create migrator
    migrator = MetadataMigrator()

    # Migrate each listing
    results = []
    for i, folder in enumerate(listing_folders, 1):
        print(f"[{i}/{len(listing_folders)}] Migrating {folder.name}...", end=" ")

        try:
            result = migrate_listing(folder, migrator)
            results.append(result)
            print("✓")
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                'folder': folder.name,
                'error': str(e),
                'validation': {'success': False}
            })

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
