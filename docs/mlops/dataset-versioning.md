# Dataset Versioning & Leakage Prevention

## 1. Immutability
Once a training dataset is compiled by `ml_platform.datasets.builder.build_dataset`:
- It is assigned a unique immutable identifier (e.g. `ds-a1b2c3d4e5f6`).
- Its complete sample manifest is hashed via SHA-256 (`manifest_checksum`).
- Any modification results in a new version rather than an in-place edit.

## 2. Patient-Level Group Isolation
In medical imaging, multiple scans from the same patient (e.g. Left Eye / Right Eye, or longitudinal visits 6 months apart) share patient-specific anatomical characteristics. Random sample-level splitting causes catastrophic data leakage and artificially inflated validation metrics.

DrishtiAI strictly enforces:
$$\text{Patients}(\text{Train}) \cap \text{Patients}(\text{Val}) = \emptyset$$
$$\text{Patients}(\text{Train}) \cap \text{Patients}(\text{Test}) = \emptyset$$
$$\text{Patients}(\text{Val}) \cap \text{Patients}(\text{Test}) = \emptyset$$

## 3. Locked Test Set
The TEST partition is locked upon compilation and serves as the unbiased held-out benchmark for evaluating safety gates and detecting regression against the production model.
