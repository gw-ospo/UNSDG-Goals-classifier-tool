# Hardcoded Threshold Management
## UNSDG Classifier Tool

This document suggests methods to address the problem of hardcoded classification thresholds
in the UNSDG Classifier Tool's classification mechanism.

---

## Problem Summary

Classification thresholds are currently hardcoded in three locations:

1. **`backend/app.py:74`** (Aurora) and **`app.py:175`** (ST URL): filter threshold `> 0.4`
2. **`backend/embedding_url.py:163`**: `classify_repo` default `threshold=0.5`, applied at `:185`
3. **`backend/embedding_url.py:197`**: `main()` overrides it with `threshold=0.7`
4. **`backend/embedding_url.py:178`**: ensemble weighting `alpha=0.3`, equally hardcoded

These thresholds control which SDG predictions are surfaced to users. Hardcoded values mean:
- No way to tune sensitivity without code changes
- No per-user or per-use-case configuration
- Potential mismatch between threshold and actual use case needs

---

## Methods to Deal with Hardcoded Thresholds

### Method 1: Environment Variables 🌟 Recommended
**Best for**: Quick configuration, deployment flexibility, no code changes needed.

**Implementation**:
- Add threshold values as environment variables
- Read them at startup with `os.getenv()` or a config library

**Code example** (`backend/app.py`):
```python
# At top of file, after load_dotenv()
AURORA_THRESHOLD = float(os.getenv("AURORA_THRESHOLD", "0.4"))

# In classify_aurora route:
filtered = [p for p in preds if p.get("prediction", 0) > AURORA_THRESHOLD]
```

**Code example** (`backend/embedding_url.py`):
```python
THRESHOLD = float(os.getenv("CLASSIFICATION_THRESHOLD", "0.5"))

# In classify_repo:
selected = [(name, sc) for (name, sc) in ranked if sc >= THRESHOLD]

# In main():
def main(url, proj_desc=""):
    result = classify_repo(url, threshold=THRESHOLD, ...)
```

**Pros**:
- No code changes required for basic usage
- Easy to override per deployment
- Standard practice for Flask apps

**Cons**:
- Requires restart when changing values
- Not dynamic per-request
- Multiple env vars needed for different thresholds

---

### Method 2: Flask Request Parameters 🌟 Recommended
**Best for**: Per-request control, API flexibility, user-driven tuning.

**Implementation**:
- Accept threshold as query parameter or JSON body field
- Validate and apply it in the route handler

**Code example** (`backend/app.py`):
```python
@app.route('/api/classify_aurora', methods=['POST'])
def classify_aurora():
    data = request.json
    threshold = data.get('threshold', AURORA_THRESHOLD)
    # ... existing code ...
    filtered = [p for p in preds if p.get("prediction", 0) > threshold]
```

**Code example** (`backend/embedding_url.py`):
```python
# In classify_st_url or classify_repo, accept threshold param
def classify_repo(url, threshold=0.5, ...):
    # use the passed threshold instead of hardcoded value
```

**Pros**:
- Per-request flexibility — different thresholds for different repos
- No deployment restart needed
- API consumers can tune as needed
- Works well with the existing POST JSON pattern

**Cons**:
- Requires API changes in both backend and frontend
- Need input validation (range checking, type checking)
- Frontend must pass the parameter through the call chain

---

### Method 3: Configuration File 🌟 Recommended
**Best for**: Persistent configuration, multiple profiles, easy management.

**Implementation**:
- Create a config file (YAML, JSON, or Python) with threshold settings
- Load it at application startup
- Support multiple profiles (e.g., "conservative", "aggressive")

**Config file** (`config.yaml`):
```yaml
aurora_threshold: 0.4
st_url_threshold: 0.5
ensemble_alpha: 0.3

profiles:
  conservative:
    aurora_threshold: 0.6
    st_url_threshold: 0.7
  aggressive:
    aurora_threshold: 0.2
    st_url_threshold: 0.3
```

**Code example** (load at startup):
```python
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)

AURORA_THRESHOLD = config.get('aurora_threshold', 0.4)
ST_URL_THRESHOLD = config.get('st_url_threshold', 0.5)
```

**Pros**:
- Single source of truth for all thresholds
- Can have multiple profiles/profiles
- Easy to version control and share
- No environment variable management needed

**Cons**:
- Requires file creation and maintenance
- Still needs restart to change values (unless reloading logic added)
- Additional dependency (yaml library)

---

### Method 4: Command-Line Arguments ⭐
**Best for**: CLI usage, scripting, ad-hoc tuning.

**Implementation**:
- Add `argparse` or similar to `app.py` and `embedding_url.py`
- Support overriding thresholds at runtime

**Code example**:
```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--aurora-threshold", type=float, default=0.4)
parser.add_argument("--st-threshold", type=float, default=0.5)
args = parser.parse_args()

# Use args.aurora_threshold and args.st_threshold
```

**Pros**:
- Good for scripting and ad-hoc testing
- No code deployment needed for simple changes
- Standard Python pattern

**Cons**:
- Not suitable for web server usage (CLI only)
- Each invocation needs explicit args
- Not discoverable for API consumers

---

### Method 5: Dynamic Calculation Based on Data Statistics 🌟
**Best for**: Data-driven thresholds, adaptive classification, scientific rigor.

**Implementation**:
- Calculate thresholds based on analysis of training data
- Use percentiles, Otsu's method, or other statistical approaches
- Store computed thresholds alongside the model

**Approach examples**:
- Use 50th percentile as medium boundary, 75th/25th as high/low
- Calculate based on distribution of scores across validation set
- Use Otsu's thresholding method for binary-like separation
- Use quantile-based thresholds from the score distribution

**Code example**:
```python
# After collecting score data, compute dynamic threshold
import numpy as np

# Example: set threshold at 65th percentile of all historical scores
all_scores = [...]  # collected from previous classifications
dynamic_threshold = np.percentile(all_scores, 65)
```

**Pros**:
- Data-driven, not arbitrary
- Adapts to the actual data distribution
- Potentially better accuracy across diverse repos

**Cons**:
- Requires historical data collection
- More complex to implement and maintain
- May produce inconsistent results over time as data changes
- Overkill for this use case unless doing rigorous ML research

---

### Method 6: Dual Thresholds (High/Medium/Low) 🌟
**Best for**: Richer UI, multiple confidence levels, better user control.

**Implementation**:
- Instead of one threshold, use two: one for "high confidence" and one for "medium"
- Return all three levels to the frontend

**Example**:
```python
HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4

# Classify each SDG into: high, medium, low
high = [p for p in preds if p["prediction"] >= HIGH_THRESHOLD]
medium = [p for p in preds if MEDIUM_THRESHOLD <= p["prediction"] < HIGH_THRESHOLD]
low = [p for p in preds if p["prediction"] < MEDIUM_THRESHOLD]
```

**Pros**:
- Gives users more nuanced information
- UI can show different colors/styles per level
- Doesn't require user to pick a single threshold
- Works well with the existing confidence banding improvement

**Cons**:
- Still needs the thresholds to come from somewhere (env vars, config, etc.)
- Slightly more complex UI logic

---

### Method 7: Model-Calibrated Thresholds 🌟
**Best for**: Machine learning best practices, probability calibration.

**Implementation**:
- Calibrate thresholds using validation data and proper scoring rules
- Use Isotonic Regression or Platt Scaling to convert model outputs to calibrated probabilities
- Set thresholds on the calibrated scale

**Approach**:
1. Collect model scores + human-labeled ground truth
2. Fit calibration model (Platt scaling or isotonic regression)
3. Set thresholds on calibrated output (e.g., 0.5 = "positive")
4. Save calibration artifacts with the model

**Pros**:
- Statistically sound approach
- Thresholds meaningful for the specific model
- Can improve accuracy if model is poorly calibrated

**Cons**:
- Requires labeled validation data
- Additional complexity and dependencies
- May overfit to specific dataset
- Overkill for this project's scope

---

### Method 8: Hybrid Approach (Recommended)
**Best for**: Balanced solution covering most use cases.

**Implementation**:
- Default thresholds via config file or environment variables
- Per-request override via API parameters
- Dual thresholds (High/Medium/Low) for richer UI
- Validation to ensure reasonable ranges

**Setup flow**:
1. Create `config.yaml` with reasonable defaults (e.g., 0.4 for Aurora, 0.5 for ST URL)
2. Support `?threshold=0.3` API parameter to override
3. Frontend shows High/Medium/Low bands based on the active threshold
4. Document how to adjust thresholds for different use cases

**Pros**:
- Covers: deployment config, per-request tuning, UI richness
- No single point of failure
- Forward-compatible with future features
- Good balance of complexity vs. utility

**Cons**:
- Most complex to implement initially
- More moving parts to maintain

---

## Recommendation Priority

| Rank | Method | Why |
|------|--------|-----|
| 1 | **Environment Variables + API Parameters** | Simplest, most flexible, standard Flask pattern |
| 2 | **Config File** | Persistent settings, multiple profiles, easy to version control |
| 3 | **Dual Thresholds (High/Medium/Low)** | Richer UI without requiring user to pick threshold |
| 4 | **Command-Line Arguments** | For CLI/testing scenarios |
| 5 | **Dynamic/Statistical Calculation** | Overkill unless doing research |
| 6 | **Model Calibration** | Overkill for this project scope |

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
1. Add `AURORA_THRESHOLD` and `ST_URL_THRESHOLD` environment variables
2. Add `threshold` parameter to `/api/classify_aurora` and `/api/classify_st_url` endpoints
3. Add dual thresholds (High/Medium/Low) to the prediction output format

### Phase 2: Configuration (2-3 days)
1. Create `config.yaml` with default thresholds
2. Add fallback to config file when env vars not set
3. Document how to adjust thresholds

### Phase 3: Polish (1-2 days)
1. Add input validation for threshold values (0-1 range)
2. Add OpenAPI/swagger documentation for threshold parameters
3. Update frontend to display confidence bands based on active threshold

---

## Code Changes Required

### `backend/app.py` changes:
```python
# Add after line 8 (load_dotenv):
AURORA_THRESHOLD = float(os.getenv("AURORA_THRESHOLD", "0.4"))

# In classify_aurora route (line 67):
threshold = request.json.get('threshold', AURORA_THRESHOLD)
filtered = [p for p in preds if p.get("prediction", 0) > threshold]
```

### `backend/embedding_url.py` changes:
```python
# Add after imports / constants:
ST_URL_THRESHOLD = float(os.getenv("ST_URL_THRESHOLD", "0.5"))

# In classify_repo function signature (line 154):
def classify_repo(url, threshold=ST_URL_THRESHOLD, ...):

# In main function (line 186-188):
def main(url, proj_desc=""):
    result = classify_repo(url, threshold=ST_URL_THRESHOLD, ...)
```

### New file: `config.yaml` (optional):
```yaml
aurora_threshold: 0.4
st_url_threshold: 0.5
```

---

## Summary

The hardcoded threshold problem has 8 viable solutions ranging from simple environment variable overrides to sophisticated statistical calibration. 

**Recommended approach**: Start with **Method 1 (Environment Variables)** + **Method 3 (Dual Thresholds)** for quick impact, then add **Method 2 (API Parameters)** for per-request control, and optionally **Method 4 (Config File)** for persistent settings.

This covers 90% of use cases with minimal complexity, and the remaining methods are available if/when needs evolve.