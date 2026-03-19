"""
Transform clustering JSON to MongoDB import format.

Usage:
    python transform_to_import_format.py <clustering_json> <mapping_json> <output_json>
"""

import argparse
import json
import sys
from typing import Dict, List, Any
from collections import defaultdict


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Transform clustering JSON to import format'
    )
    parser.add_argument(
        'clustering_json',
        help='Path to the clustering JSON file (sign_clustering_paths.json)'
    )
    parser.add_argument(
        'mapping_json',
        help='Path to mapping file (annotationId -> sign/period/fragment)'
    )
    parser.add_argument(
        'output_json',
        help='Path to output import-ready JSON file'
    )
    return parser.parse_args()


def load_json_from_file(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def index_annotations_by_sign_metadata(mapping_data: List[Dict[str, Any]]) -> Dict[tuple, List[str]]:
    annotation_index_by_sign_period_fragment = defaultdict(list)
    
    for entry in mapping_data:
        annotation_id = entry.get('annotationId')
        sign = entry.get('sign')
        period = entry.get('period')
        fragment_number = entry.get('fragment_number')
        
        if all([annotation_id, sign is not None, period, fragment_number]):
            key = (str(sign), period, fragment_number)
            annotation_index_by_sign_period_fragment[key].append(annotation_id)
    
    return annotation_index_by_sign_period_fragment


def calculate_cluster_rank_from_form_label(form_label: str) -> int:
    if form_label.startswith('canonical'):
        try:
            canonical_number = int(form_label.replace('canonical', ''))
            return canonical_number - 1
        except ValueError:
            return 0
    
    if form_label.startswith('variant'):
        try:
            variant_number = int(form_label.replace('variant', ''))
            return variant_number + 1
        except ValueError:
            return 2
    
    return 0


def create_import_entries_from_clustering(
    clustering_data: List[Dict[str, Any]],
    annotation_index: Dict[tuple, List[str]]
) -> List[Dict[str, Any]]:
    import_entries = []
    matched_entries_count = 0
    unmatched_entries_count = 0
    
    for clustering_entry in clustering_data:
        sign = str(clustering_entry.get('sign', ''))
        period = clustering_entry.get('period', '')
        fragment_number = clustering_entry.get('fragment_number', '')
        
        lookup_key = (sign, period, fragment_number)
        annotation_ids = annotation_index.get(lookup_key, [])
        
        if not annotation_ids:
            unmatched_entries_count += 1
            continue
        
        cluster_id = clustering_entry.get('_id', '')
        form_label = clustering_entry.get('form', 'canonical1')
        is_centroid = clustering_entry.get('isCentroid', False)
        cluster_size = clustering_entry.get('clusterSize', 1)
        is_main = clustering_entry.get('isMain', True)
        cluster_rank = calculate_cluster_rank_from_form_label(form_label)
        
        for annotation_id in annotation_ids:
            import_entry = {
                "annotationId": annotation_id,
                "pcaClustering": {
                    "clusterId": cluster_id,
                    "clusterRank": cluster_rank,
                    "form": form_label,
                    "isCentroid": is_centroid,
                    "clusterSize": cluster_size,
                    "isMain": is_main
                }
            }
            import_entries.append(import_entry)
            matched_entries_count += 1
    
    print(f"\nTransformation summary:")
    print(f"  Matched entries: {matched_entries_count}")
    print(f"  Unmatched entries: {unmatched_entries_count}")
    print(f"  Total import entries: {len(import_entries)}")
    
    return import_entries


def save_json_to_file(data: List[Dict[str, Any]], output_file_path: str) -> None:
    with open(output_file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f"\nSaved import-ready JSON to: {output_file_path}")


def main() -> None:
    args = parse_arguments()
    
    print(f"Loading clustering data from: {args.clustering_json}")
    clustering_data = load_json_from_file(args.clustering_json)
    print(f"  Loaded {len(clustering_data)} clustering entries")
    
    print(f"\nLoading mapping data from: {args.mapping_json}")
    mapping_data = load_json_from_file(args.mapping_json)
    print(f"  Loaded {len(mapping_data)} mapping entries")
    
    print("\nBuilding annotation index...")
    annotation_index = index_annotations_by_sign_metadata(mapping_data)
    print(f"  Indexed {len(annotation_index)} unique sign instances")
    
    print("\nTransforming data...")
    import_entries = create_import_entries_from_clustering(clustering_data, annotation_index)
    
    if import_entries:
        save_json_to_file(import_entries, args.output_json)
    else:
        print("\nWarning: No entries to import. Check your mapping file.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
