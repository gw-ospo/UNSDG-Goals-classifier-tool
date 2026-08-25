"""
inference.py
~~~~~~~~~~~~

In-process SDG classification, replacing the HTTP hop to the old `models/`
Flask service.

Contract is deliberately identical to the retired ``POST /predict`` endpoint:
text in, ``{sdg_label: probability}`` out. Nothing about the backend leaks in
here, so this can be wrapped in a route again if the model ever needs to move
back onto its own host — see ``MODEL_SERVICE_URL`` in ``embedding_url.py``.

Loading is lazy so importing this module is free and the process can bind its
port before ~1.7 GB of weights are read.
"""

from __future__ import annotations

import torch
from transformers import AutoTokenizer

from sdg_constants import SDG_NAMES
from services.sdg_model import SDGClassifier

BASE_MODEL = "studio-ousia/luke-large-lite"
CHECKPOINT_REPO = "GE-Lab/SDGs-classifier"
CHECKPOINT_FILE = "best_model.pt"
NUM_CLASSES = 17
DROPOUT_RATE = 0.26     # optimised rate from the paper's training run
MAX_LENGTH = 512

_model = None
_tokenizer = None
_device = None


def _assert_checkpoint_covers_model(model, state_dict) -> None:
    """Guard the from_config() optimisation in sdg_model.py.

    SDGClassifier builds its backbone from config alone, downloading no
    pretrained weights. That is only correct because this checkpoint supplies
    *every* parameter. strict=True already enforces it, but its error is a wall
    of key names; this one says what actually broke and why it matters.
    """
    missing = sorted(set(model.state_dict()) - set(state_dict))
    if missing:
        raise RuntimeError(
            f"Checkpoint is missing {len(missing)} parameter(s) the model needs, "
            f"e.g. {missing[:3]}. sdg_model.py builds the backbone with "
            "AutoModel.from_config(), so anything absent from the checkpoint would "
            "be left randomly initialised. If the base model changed, that "
            "optimisation is no longer safe."
        )


def load() -> None:
    """Build the tokenizer and model. Idempotent; safe to call from a warmup."""
    global _model, _tokenizer, _device
    if _model is not None:
        return

    from huggingface_hub import hf_hub_download

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = SDGClassifier(
        model_path=BASE_MODEL,
        pooler_dropout=DROPOUT_RATE,
        class_number=NUM_CLASSES,
    )

    weights_path = hf_hub_download(repo_id=CHECKPOINT_REPO, filename=CHECKPOINT_FILE)
    state_dict = torch.load(weights_path, map_location=device)
    _assert_checkpoint_covers_model(model, state_dict)
    model.load_state_dict(state_dict, strict=True)
    del state_dict  # release the staging copy once it is in the model

    if device.type == "cuda":
        model = model.half()
    model.to(device).eval()

    _model, _tokenizer, _device = model, tokenizer, device


def is_loaded() -> bool:
    """Whether the weights are resident — the readiness signal, not liveness."""
    return _model is not None


def predict_scores(text: str) -> dict[str, float]:
    """Return ``{sdg_label: probability}`` for *text*.

    Probabilities are rounded to 4 decimals. That is not cosmetic: the retired
    /predict endpoint rounded before serialising to JSON, so callers were
    calibrated against rounded values. Dropping the rounding here would shift
    every downstream ensemble score in the 5th decimal.
    """
    if not text:
        raise ValueError("No text provided")

    load()

    enc = _tokenizer(
        text,
        add_special_tokens=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_token_type_ids=True,
        return_tensors="pt",
    ).to(_device)

    seq_len = enc["input_ids"].shape[1]
    enc["position"] = torch.arange(seq_len).unsqueeze(0).to(_device)
    enc["labels"] = torch.zeros(1, NUM_CLASSES).to(_device)

    with torch.no_grad():
        logits, _, _ = _model(**enc)

    probs = torch.sigmoid(logits).squeeze(0).float().cpu().numpy()
    return {label: round(float(p), 4) for label, p in zip(SDG_NAMES, probs)}
