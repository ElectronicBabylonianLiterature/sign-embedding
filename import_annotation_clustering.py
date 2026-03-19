"""
Import clustering data for annotations into MongoDB.

Usage:
    python import_annotation_clustering.py <json_file>
    python import_annotation_clustering.py <json_file> --test
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, List
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


SEPARATOR_LINE = '=' * 60
EBL_DATABASE_NAME = 'ebl'
ANNOTATIONS_COLLECTION_NAME = 'annotations'


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Import clustering data for annotations from JSON file'
    )
    parser.add_argument(
        'json_file',
        help='Path to the JSON file containing annotation clustering data'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: import only the first entry'
    )
    return parser.parse_args()


def connect_to_mongodb_database() -> Database:
    print("Connecting to MongoDB...")
    mongodb_connection_uri = os.getenv('MONGODB_URI', '')
    
    if not mongodb_connection_uri:
        raise ValueError("MONGODB_URI environment variable is not set")
    
    client = MongoClient(mongodb_connection_uri)
    return client[EBL_DATABASE_NAME]


def load_import_entries_from_file(file_path: str) -> List[Dict[str, Any]]:
    print(f"Loading clustering data from {file_path}...")
    
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        import_entries = json.load(file)
    
    print(f"Loaded {len(import_entries)} annotation entries")
    return import_entries


def add_clustering_data_to_annotation(
    annotations_collection: Collection,
    annotation_id: str,
    clustering_data: Dict[str, Any]
) -> bool:
    update_result = annotations_collection.update_one(
        {'annotations.data.id': annotation_id},
        {'$set': {'annotations.$[elem].pcaClustering': clustering_data}},
        array_filters=[{'elem.data.id': annotation_id}]
    )
    
    if update_result.matched_count == 0:
        print(f"  WARNING: Annotation '{annotation_id}' not found in database")
        return False
    
    if update_result.modified_count == 0:
        print(f"  INFO: Annotation '{annotation_id}' already has this clustering data")
    else:
        print(f"  SUCCESS: Updated annotation '{annotation_id}'")
    
    return True


def process_import_entry(
    annotations_collection: Collection,
    import_entry: Dict[str, Any],
    entry_number: int,
    total_entries: int
) -> bool:
    annotation_id = import_entry.get('annotationId')
    clustering_data = import_entry.get('pcaClustering')
    
    if not annotation_id:
        print(f"Entry {entry_number}: ERROR - Missing annotationId")
        return False
    
    if not clustering_data:
        print(f"Entry {entry_number}: ERROR - Missing pcaClustering data")
        return False
    
    print(f"[{entry_number}/{total_entries}] Processing annotation: {annotation_id}")
    return add_clustering_data_to_annotation(annotations_collection, annotation_id, clustering_data)


def print_summary(total_processed: int, successful_updates: int, not_found_count: int) -> None:
    print(f"\n{SEPARATOR_LINE}")
    print(f"Import completed:")
    print(f"  Total processed: {total_processed}")
    print(f"  Successfully updated: {successful_updates}")
    print(f"  Not found: {not_found_count}")
    print(f"{SEPARATOR_LINE}")


def import_all_clustering_data(
    database: Database,
    import_entries: List[Dict[str, Any]],
    is_test_mode: bool = False
) -> None:
    annotations_collection = database[ANNOTATIONS_COLLECTION_NAME]
    
    entries_to_process = import_entries[:1] if is_test_mode else import_entries
    total_entries = len(entries_to_process)
    
    if is_test_mode:
        print("\n*** TEST MODE: Processing only the first entry ***\n")
    
    print(f"Processing {total_entries} annotation(s)...\n")
    
    successful_updates = 0
    not_found_count = 0
    
    for entry_number, import_entry in enumerate(entries_to_process, start=1):
        if process_import_entry(annotations_collection, import_entry, entry_number, total_entries):
            successful_updates += 1
        else:
            not_found_count += 1
    
    print_summary(total_entries, successful_updates, not_found_count)


def handle_error_and_exit(error: Exception) -> None:
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    try:
        arguments = parse_arguments()
        database = connect_to_mongodb_database()
        import_entries = load_import_entries_from_file(arguments.json_file)
        
        import_all_clustering_data(database, import_entries, is_test_mode=arguments.test)
        
    except (FileNotFoundError, ValueError) as error:
        handle_error_and_exit(error)
    except Exception as error:
        print(f"Unexpected error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
