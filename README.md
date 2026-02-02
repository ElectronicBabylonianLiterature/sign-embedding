# Sign Embedding, Form Clustering, and JSON Generation

This repository implements an end-to-end pipeline for generating sign embeddings, clustering sign forms, and producing JSON files. It also provides instructions for rerunning the process on a regular basis.

## Table of Contents
- [Generating JSON Files](#generating-json-files)
  - [Step 1 — Prepare the Dataset](#step-1---prepare-the-dataset)
  - [Step 2 — Train a Sign Classification Model](#step-2---train-a-sign-classification-model)
  - [Step 3 — Convert the Model into a Feature Extractor](#step-3---convert-the-model-into-a-feature-extractor)
  - [Step 4 — Group Images by Sign and Period](#step-4---group-images-by-sign-and-period)
  - [Step 5 — Cluster Visual Forms](#step-5---cluster-visual-forms)
  - [Step 6 — Identify Canonical and Variant Forms](#step-6---identify-canonical-and-variant-forms)
  - [Step 7 — Select Representative (Centroid) Images](#step-7---select-representative-centroid-images)
  - [Step 8 — Generate Two Final JSON Outputs](#step-8---generate-two-final-json-outputs)
  - [Final Outcome](#final-outcome)
- [How to Re-run the Pipeline and generate new JSON files](#how-to-re-run-the-pipeline)

---

## Generating JSON Files

**Notebook:** `generating_json.ipynb`  

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

### Final Outcome
From raw sign images, the pipeline produces:
- Learned visual embeddings  
- Automatically identified canonical and variant sign forms  
- Two structured JSON files per run:
  - One for inspection and reproducibility  
  - One for ingestion and deployment  

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
