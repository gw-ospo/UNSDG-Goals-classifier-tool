import os
import re
import base64
import requests
from urllib.parse import urlparse
from typing import List, Dict, Tuple
import numpy as np
import sdg_constants
from sdg_constants import SDG_LABELS, SDG_NAMES, SDG_DESCS
from services.repo_fetcher import get_provider
from urllib.parse import urlparse
from services.summariser import summarize_for_sdg
from services.embedder import get_embedder
from services.inference import predict_scores

# repo_fetcher may define ProviderError; if not available, fall back to a generic exception.
try:
    from services.repo_fetcher import ProviderError  # type: ignore
except Exception:  # pragma: no cover
    ProviderError = Exception

# ── CHANGE 1: added project_description param ────────────────────────────────
def fetch_repo_text(url: str, project_description: str = "", max_issues: int = 10) -> Dict:
    # max_issues currently unused; kept for compatibility
    host = urlparse(url).hostname or ""
    token = os.environ.get("GITHUB_TOKEN") if "github.com" in host else None

    provider = get_provider(url, token=token)
    meta: Dict[str, str] = {"name": "", "description": "", "homepage": ""}
    try:
        fetch_meta = getattr(provider, "fetch_meta", None)
        if callable(fetch_meta):
            meta_candidate = fetch_meta()
            if isinstance(meta_candidate, dict):
                meta = meta_candidate
        else:
            meta = {
                "name": getattr(provider, "_name", ""),
                "description": getattr(provider, "_description", ""),
                "homepage": getattr(provider, "_homepage", ""),
            }
    except ProviderError:
        pass

    topics: List[str] = []

    try:
        topics = provider.fetch_topics()    
    except ProviderError:
        pass

    readme: str = ""
    try:
        readme = provider.fetch_readme()
    except ProviderError:
        pass

    # These can all be None depending on the platform response:
    name        = meta.get("name")        or ""
    # ── CHANGE 2: user's description takes priority over repo's description ──
    description = project_description.strip() or meta.get("description") or ""
    homepage    = meta.get("homepage")    or ""
    topics      = topics or []
    readme      = readme or ""

    extracted_summary = summarize_for_sdg(
        readme=readme,
        name=name,
        description=description,
        topics=topics
    )
    print(extracted_summary)
    return {
        "owner": provider._owner,
        "repo":  provider._repo,
        "text":  extracted_summary,
        "meta":  {
            "name":        name,
            "description": description,
            "topics":      topics,
            "homepage":    homepage,
        },
    }


def zero_shot_scores(text: str, labels: List[str]) -> Tuple[np.ndarray, Dict]:

    """
    Score *text* against every SDG with the fine-tuned LUKE classifier.

    Runs in-process by default. Setting MODEL_SERVICE_URL routes the call to a
    remote model service over HTTP instead, which is how this worked when the
    model lived in its own `models/` Flask app. The seam is kept so the model
    can be moved back onto its own host — for GPU inference, or to scale it
    apart from the API — without touching this module's callers.

    Read at call time, not import time: app.py calls load_dotenv() *after*
    importing this module, so a module-level constant would miss the .env value.
    """
    service_url = os.environ.get("MODEL_SERVICE_URL", "").strip()

    if service_url:
        response = requests.post(
            f"{service_url.rstrip('/')}/predict",
            json={"text": text},
            timeout=1500,
        )
        response.raise_for_status()
        payload = response.json()
        scores_obj = payload.get("scores")
        if scores_obj is None and isinstance(payload.get("data"), dict):
            scores_obj = payload["data"].get("scores")
    else:
        # Same contract the /predict route served, including its 4-decimal
        # rounding — see services.inference.predict_scores.
        payload = {}
        scores_obj = predict_scores(text)

    if isinstance(scores_obj, dict):
        ordered_scores = [scores_obj.get(label) for label in sdg_constants.SDG_NAMES]
        if any(v is None for v in ordered_scores):
            raise KeyError(
                "Model scores dict missing expected SDG keys. "
                f"Available keys sample={list(scores_obj.keys())[:5]}"
            )
        scores_list = ordered_scores
    elif isinstance(scores_obj, (list, tuple)):
        scores_list = list(scores_obj)
    else:
        raise TypeError(
            f"Unexpected model scores type={type(scores_obj)} "
            f"payload_keys={list(payload.keys())}"
        )

    detailed_info = {
        "labels": labels,  
        "scores": scores_list,
        "sequence": text[:500]
    }

    return np.array(scores_list, dtype=float), detailed_info



COSINE_LOW  = 0.27 # e.g. 5th percentile of real observed similarities
COSINE_HIGH = 0.34  # e.g. 95th percentile of real observed similarities

def embedding_similarity_scores(text: str, label_texts: List[str]) -> np.ndarray:
    emb = get_embedder()
    v_text = emb.encode([text], normalize_embeddings=True)[0]
    v_lbls = emb.encode(label_texts, normalize_embeddings=True)
    sims = np.dot(v_lbls, v_text)
    sims = np.clip((sims - COSINE_LOW) / (COSINE_HIGH - COSINE_LOW), 0, 1)
    return sims

def ensemble_scores(zs: np.ndarray, es: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """
    Simple mean ensemble; tune alpha if desired.
    """
    return alpha * zs + (1 - alpha) * es

# ── CHANGE 3: added project_description param, passed to fetch_repo_text ─────
def classify_repo(url: str, threshold: float = 0.5, top_k: int = 10, use_ensemble: bool = True, proj_desc: str = ""):
    data = fetch_repo_text(url, project_description=proj_desc)
    text = data["text"][:6000]

    if not text:
        raise ValueError("No text extracted from this repository. Add README or description.")

    zs, zs_details = zero_shot_scores(text, sdg_constants.SDG_NAMES)

    label_score_pairs = list(zip(zs_details["labels"], zs_details["scores"]))
    label_score_pairs.sort(key=lambda x: x[1], reverse=True)
    

    if use_ensemble:
        es = embedding_similarity_scores(text, sdg_constants.SDG_DESCS)
        scores = ensemble_scores(zs, es, alpha=0.3)
    else:
        scores = zs

    idx = np.argsort(scores)[::-1]
    ranked = [(sdg_constants.SDG_NAMES[i], float(scores[i])) for i in idx]

    selected = [(name, sc) for (name, sc) in ranked if sc >= threshold]

    return {
        "repo":        f"{data['owner']}/{data['repo']}",  
        "predictions": selected[:top_k],                  
        "top_all":     ranked[:top_k],
        "meta":        data["meta"],                       
    }

# ── CHANGE 4: main() accepts and passes project_description ──────────────────
def main(url: str, project_description: str = ""):

    result = classify_repo(url, threshold=0.7, use_ensemble=True, proj_desc=project_description)

    predictions = {
        "project_name": result["repo"],
        "project_url": url,
        "sdg_predictions": {
            name: float(f"{score:.3f}") for (name, score) in result["predictions"]
        }
    }

    return predictions

if __name__ == "__main__":
    print("\033[43m GET THE REPO_ANALYSED RESULTS\033[0m")
    