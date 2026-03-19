# Sign Embedding, Form Clustering, and JSON Generation

This repository implements an end-to-end pipeline for generating sign embeddings, clustering sign forms, and producing JSON files. It also provides instructions for rerunning the process on a regular basis.

## Table of Contents
- [Generating JSON Files](#generating-json-files)
  - [Step 1 — Prepare the Dataset](#step-1--prepare-the-dataset)
  - [Step 2 — Train a Sign Classification Model](#step-2--train-a-sign-classification-model)
  - [Step 3 — Convert the Model into a Feature Extractor](#step-3--convert-the-model-into-a-feature-extractor)
  - [Step 4 — Group Images by Sign and Period](#step-4--group-images-by-sign-and-period)
  - [Step 5 — Cluster Visual Forms](#step-5--cluster-visual-forms)
  - [Step 6 — Identify Canonical and Variant Forms](#step-6--identify-canonical-and-variant-forms)
  - [Step 7 — Select Representative (Centroid) Images](#step-7--select-representative-centroid-images)
  - [Step 8 — Generate Two Final JSON Outputs](#step-8--generate-two-final-json-outputs)
  - [Step 9 — Transform to Import Format](#step-9--transform-to-import-format)
  - [Step 10 — Import into MongoDB](#step-10--import-into-mongodb)
  - [Final Outcome](#final-outcome)
- [Scripts](#scripts)
- [How to Re-run the Pipeline and Generate New JSON Files](#how-to-re-run-the-pipeline-and-generate-new-json-files)


## Generating JSON Files

**Notebook:** [`generating_json.ipynb`](generating_json.ipynb) 

### Step 1 — Prepare the Dataset
- Organize cropped sign images by sign class (folder = sign).  
- Each image belongs to a historical period (encoded in folder path).  
- This structure provides labels (sign) and metadata (period) in `generating_json/new_structure_data`.  

**Purpose:** Give the model supervised labels and contextual grouping.

---

### Step 2 — Train a Sign Classification Model
- Load ResNet18 pretrained on ImageNet.  
- Replace the final layer to classify sign classes.  
- Freeze early layers; fine-tune only the top layers.  
- Train using cross-entropy loss.  
- Use validation + early stopping.  
- Save the best-performing model in `generating_json/resnet18_sign_model_best.pth`.  

**Purpose:** Learn a feature space where images of the same sign look similar.

---

### Step 3 — Convert the Model into a Feature Extractor
- Remove the final classification layer.  
- Pass all images through the network.  
- Extract the embedding vector for each image.  
- Save the following in `generating_json/sign_model_embeddings.npz`:
  - embeddings  
  - sign labels  
  - periods  
  - image paths  

**Purpose:** Turn each image into a meaningful numerical representation.

---

### Step 4 — Group Images by Sign and Period
- Load saved embeddings.  
- Group indices by `(sign, period)`  

**Purpose:** Cluster only comparable images (same sign, same time).

---

### Step 5 — Cluster Visual Forms
- For each `(sign, period)` group:  
  - Automatically choose K based on group size.  
  - Apply KMeans to embeddings.  
- Each cluster represents a distinct visual form.  

**Purpose:** Discover canonical shapes and variants automatically.

---

### Step 6 — Identify Canonical and Variant Forms
- Sort clusters by size.  
- Label:
  - Largest clusters → `canonical1`, `canonical2`  
  - Smaller clusters → `variant1`, `variant2`, …  
- Mark clusters as main if they are canonical or large enough variants.  

**Purpose:** Separate dominant sign forms from rare ones.

---

### Step 7 — Select Representative (Centroid) Images
- Compute cluster centroid (mean embedding).  
- Choose the image closest to centroid as representative.  
- Mark it as `isCentroid = true`.  

**Purpose:** Assign a single image that best represents each form.

---

### Step 8 — Generate Two Final JSON Outputs
For every image, record:
- sign  
- period  
- form label  
- centroid status  
- cluster size  
- main/variant flag  

Generate:
1. **Path-based JSON** (image paths only)  
   - Lightweight, human-readable, easy to debug
2. **Base64-encoded JSON** (image data embedded)  
   - Import-ready  

**Purpose:** Separate lightweight analysis data from heavy import data while preserving identical clustering results.

---

### Step 9 — Transform to Import Format
- Load the path-based clustering JSON.  
- Load a mapping file that connects sign data to annotation IDs.  
- Transform each clustering entry into the MongoDB import format.  
- Nest clustering data under `pcaClustering` field.  
- Add `clusterId` and `clusterRank` fields.  
- Generate `import_ready.json` for database import.  

**Purpose:** Bridge the gap between clustering output and database schema.

**Script:** [`transform_to_import_format.py`](transform_to_import_format.py)

---

### Step 10 — Import into MongoDB
- Connect to MongoDB using `MONGODB_URI` environment variable.  
- Update each annotation document with its clustering data.  
- Add `pcaClustering` field to matching annotations.  
- Report success/failure for each entry.  
- Support test mode to validate before full import.  

**Purpose:** Persist clustering results in the production database.

**Script:** [`import_annotation_clustering.py`](import_annotation_clustering.py)

---

### Final Outcome
From raw sign images, the pipeline produces:
- Learned visual embeddings  
- Automatically identified canonical and variant sign forms  
- Two structured JSON files per run:
  - One for inspection and reproducibility  
  - One for ingestion and deployment  
- Import-ready JSON with annotation clustering data  
- Database updates linking annotations to their clustering metadata  

**Example path-based JSON entry:**
```json
{
  "_id": "57b78370-9bcc-41a8-a586-2f87ec2092e5",
  "image_path": "/generating_json/new_structure_data/0/Old_Babylonian/HS.2087_sign10_0_Old_Babylonian.jpg",
  "fragment_number": "HS.2087",
  "sign": "0",
  "period": "Old_Babylonian",
  "form": "canonical1",
  "isCentroid": true,
  "clusterSize": 2,
  "isMain": true
}
```
**Example Base64-encoded JSON entry:**
```json
{
  "_id": "57b78370-9bcc-41a8-a586-2f87ec2092e5",
  "image": "/9j/4AAQSkZJRgABAQAAAQABAAD/…….+tFZdwT9pk5P3jRTA/9k=",
  "fragment_number": "HS.2087",
  "sign": "0",
  "period": "Old_Babylonian",
  "form": "canonical1",
  "isCentroid": true,
  "clusterSize": 2,
  "isMain": true
}
```

**Example import-ready JSON entry:**
```json
{
  "annotationId": "fe424867cb374697be3110157f17f39c",
  "pcaClustering": {
    "clusterId": "57b78370-9bcc-41a8-a586-2f87ec2092e5",
    "clusterRank": 0,
    "form": "canonical1",
    "isCentroid": true,
    "clusterSize": 2,
    "isMain": true
  }
}
```

---

## Scripts

This repository includes the following Python scripts:

### [`transform_to_import_format.py`](transform_to_import_format.py)
Transforms clustering JSON output into MongoDB import format.

**Usage:**
```bash
python transform_to_import_format.py <clustering_json> <mapping_json> <output_json>
```

**Input:**
- Clustering JSON from the pipeline (`sign_clustering_paths.json`)
- Mapping file connecting signs to annotation IDs (`annotation_mapping.json`)

**Output:**
- Import-ready JSON file with `annotationId` and `pcaClustering` fields

### [`import_annotation_clustering.py`](import_annotation_clustering.py)
Imports clustering data into MongoDB annotations collection.

**Usage:**
```bash
# Test mode (first entry only)
python import_annotation_clustering.py <json_file> --test

# Full import
python import_annotation_clustering.py <json_file>
```

**Requirements:**
- `MONGODB_URI` environment variable must be set
- MongoDB instance with `ebl` database and `annotations` collection

**Features:**
- Updates annotations with `pcaClustering` data
- Reports matched and unmatched entries
- Supports test mode for validation

---

## How to Re-run the Pipeline and Generate New JSON Files

To generate updated JSON files and import them into MongoDB, follow these steps:

### 1. Update the Dataset
Place new or updated cropped sign images into `generating_json/new_structure_data/` following the same folder structure (`sign` / `period`).

### 2. Run the Clustering Pipeline
Run the notebook [`generating_json.ipynb`](generating_json.ipynb) from top to bottom (Steps 0-8).

The pipeline will:
- retrain (or reuse) the sign classification model,  
- regenerate image embeddings,  
- recluster sign forms,  
- and overwrite the existing JSON outputs.

The outputs will be written to:  
- `generating_json/sign_clustering_paths.json`  
- `generating_json/sign_clustering_base64.json`

### 3. Create or Update the Mapping File
Create `annotation_mapping.json` that maps clustering data to annotation IDs:

```json
[
  {
    "annotationId": "fe424867cb374697be3110157f17f39c",
    "sign": "0",
    "period": "Old_Babylonian",
    "fragment_number": "HS.2087"
  }
]
```

This file connects the clustering results to your database annotations. You can generate this by querying your MongoDB annotations collection.

**See [`annotation_mapping.json.example`](annotation_mapping.json.example) for a template.**

**Generating the mapping file from MongoDB:**
```javascript
// MongoDB query to export annotation mapping
db.annotations.aggregate([
  { $unwind: "$annotations" },
  {
    $project: {
      _id: 0,
      annotationId: "$annotations.data.id",
      sign: "$annotations.data.sign",
      period: "$annotations.data.period",
      fragment_number: "$annotations.data.fragmentNumber"
    }
  }
])
```

### 4. Transform to Import Format
Run the transformation script:

```bash
python transform_to_import_format.py \
    generating_json/sign_clustering_paths.json \
    annotation_mapping.json \
    generating_json/import_ready.json
```

This will create `generating_json/import_ready.json` in the format expected by the import script.

### 5. Import into MongoDB
Set your MongoDB connection string and import the data:

```bash
# Set MongoDB URI (if not already set)
export MONGODB_URI="mongodb://localhost:27017/"  # or your connection string

# Test with first entry only
python import_annotation_clustering.py generating_json/import_ready.json --test

# Import all entries
python import_annotation_clustering.py generating_json/import_ready.json
```

The import script will update the annotations collection in the `ebl` database, adding `pcaClustering` data to each matching annotation.

> This process can be repeated at any time to regenerate the JSON files with new data, updated models, or modified clustering parameters, and sync the results to your database.
