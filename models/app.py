import os
import torch
from flask import Flask, request, jsonify
from transformers import AutoTokenizer
from similarities import SDG_DESCS
from classifier import SDGClassifier
from huggingface_hub import hf_hub_download
#from gh_cleaner import clean_github_readme as cleaner
from sentence_transformers import SentenceTransformer
import numpy as np
from similarities import get_embedder
from dotenv import load_dotenv

# Picks up the repository-root .env, same as the backend does.
load_dotenv()

app = Flask(__name__)

print("Loading model and tokenizer...")
# ── Constants ─────────────────────────────────────────────────────────────────
BASE_MODEL   = "studio-ousia/luke-large-lite"
NUM_CLASSES  = 17
THRESHOLD    = 0.5
MAX_LENGTH   = 512
SDG_LABELS = [
    'SDG 1: End poverty in all its forms everywhere',
    'SDG 2: End hunger, achieve food security and improved nutrition and promote sustainable agriculture',
    'SDG 3: Ensure healthy lives and promote well-being for all at all ages',
    'SDG 4: Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all',
    'SDG 5: Achieve gender equality and empower all women and girls',
    'SDG 6: Ensure availability and sustainable management of water and sanitation for all',
    'SDG 7: Ensure access to affordable, reliable, sustainable and modern energy for all',
    'SDG 8: Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all',
    'SDG 9: Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation',
    'SDG 10: Reduce inequality within and among countries',
    'SDG 11: Make cities and human settlements inclusive, safe, resilient and sustainable',
    'SDG 12: Ensure sustainable consumption and production patterns',
    'SDG 13: Take urgent action to combat climate change and its impacts',
    'SDG 14: Conserve and sustainably use the oceans, seas and marine resources for sustainable development',
    'SDG 15: Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss',
    'SDG 16: Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels',
    'SDG 17: Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development'
]

print("Model and tokenizer loaded successfully.")
# ── Global Load (Happens once at server startup) ──────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
model = SDGClassifier(
    model_path=BASE_MODEL,
    pooler_dropout=0.26,
    class_number=NUM_CLASSES,
)

def _assert_checkpoint_covers_model(model, state_dict) -> None:
    """Guard the from_config() optimisation in classifier.py.

    SDGClassifier builds its backbone from config alone, downloading no
    pretrained weights. That is only correct because this checkpoint supplies
    *every* parameter. strict=True already enforces it, but its error is a wall
    of key names; this one says what actually broke and why it matters.
    """
    missing = sorted(set(model.state_dict()) - set(state_dict))
    if missing:
        raise RuntimeError(
            f"Checkpoint is missing {len(missing)} parameter(s) the model needs, "
            f"e.g. {missing[:3]}. classifier.py builds the backbone with "
            "AutoModel.from_config(), so anything absent from the checkpoint would "
            "be left randomly initialised. If the base model changed, that "
            "optimisation is no longer safe."
        )


weights_path = hf_hub_download(repo_id="GE-Lab/SDGs-classifier", filename="best_model.pt")
_state_dict = torch.load(weights_path, map_location=device)
_assert_checkpoint_covers_model(model, _state_dict)
model.load_state_dict(_state_dict, strict=True)
del _state_dict  # release the 1.73 GB staging copy once it is in the model

if device.type == "cuda":
    model = model.half()
model.to(device).eval()

# ── Endpoint ──────────────────────────────────────────────────────────────────
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Clean text using your existing utility
    # cleaned_text = "Our project implements a decentralized grid management system powered by IoT sensors to optimize renewable energy distribution in remote villages. By reducing energy wastage and integrating solar-based microgrids, we are accelerating the transition to clean energy while building resilient community infrastructure."
    # Inference logic

    enc = tokenizer(
        text,
        add_special_tokens=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_token_type_ids=True,
        return_tensors="pt",
    ).to(device)

    T = enc["input_ids"].shape[1]
    enc["position"] = torch.arange(T).unsqueeze(0).to(device)
    enc["labels"] = torch.zeros(1, NUM_CLASSES).to(device)

    with torch.no_grad():
        logits, _, _ = model(**enc)

    probs = torch.sigmoid(logits).squeeze(0).float().cpu().numpy()

    
    return jsonify({
        "scores": {label: round(float(prob), 4) for label, prob in zip(SDG_LABELS, probs)},
        "predictions": [label for label, prob in zip(SDG_LABELS, probs) if prob > THRESHOLD]
    })


@app.route("/similarities", methods=["POST"])
def predict_cosine():
    data = request.json
    text = data.get("text", "")
    label_texts = data.get("label_texts", SDG_DESCS)

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Clean text using your existing utility
    # cleaned_text = cleaner(text)

    emb = get_embedder()
    v_text = emb.encode([text], normalize_embeddings=True)[0]
    v_lbls = emb.encode(label_texts, normalize_embeddings=True)
    sims = np.dot(v_lbls, v_text)  
    sims = (sims - sims.min()) / (sims.max() - sims.min() + 1e-8)  # Normalize to 0..1

    return jsonify({
        "similarities": {label: round(float(sim), 4) for label, sim in zip(label_texts, sims)},
        
    })



@app.route('/', methods=['GET'])
def hello():
    return jsonify({'message': 'Hello, World!'})



if __name__ == "__main__":
    # debug is pinned off: this service is internal, and the reloader would
    # load the LUKE weights a second time. Without this, FLASK_DEBUG in the
    # shared root .env would switch the Werkzeug debugger on here too.
    #
    # Override the port with MODELS_PORT (.env). The backend reaches this
    # service via MODEL_SERVICE_URL, which must point at whatever this binds.
    app.run(debug=False, port=int(os.environ.get("MODELS_PORT", 9010)))