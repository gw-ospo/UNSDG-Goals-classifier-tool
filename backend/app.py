import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from embedding_url import main as classify_url
from aurora_api import main as aurora_classify
from dotenv import load_dotenv
from services.recommendation_pipeline import assess_relevance
load_dotenv()

try:
    from services.repo_fetcher import (
        InvalidURLError,
        UnsupportedHostError,
        RepositoryNotFoundError,
        RateLimitError,
        FetchError,
    )
except Exception:
    # If import fails, degrade gracefully — all map to ValueError
    InvalidURLError         = ValueError
    UnsupportedHostError    = ValueError
    RepositoryNotFoundError = ValueError
    RateLimitError          = ValueError
    FetchError              = ValueError

app = Flask(__name__)
CORS(app)


@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({'message': 'Hello, World!'})


# ---------------------------------------------------------------------------
# Aurora
# ---------------------------------------------------------------------------

@app.route('/api/classify_aurora', methods=['POST'])
def classify_aurora():
    data               = request.json
    projectName        = data.get('projectName')
    projectUrl         = data.get('projectUrl')
    projectDescription = data.get('projectDescription')

    if not projectDescription:
        return jsonify({'error': 'Project description is required'}), 400

    print("\n===== RUNNING AURORA API MODEL =====")
    try:
        aurora_result = aurora_classify(
            text         = projectDescription,
            project_name = projectName,
            project_url  = projectUrl,
        )
        print("Aurora API model completed successfully")
    except Exception as e:
        print(f"Aurora API model failed: {e}")
        return jsonify({"error": str(e), "message": "Aurora API classification failed"}), 500

    # ── Recommendation pipeline: assess why no SDGs were returned ──────────
    rec = assess_relevance(
        projectDescription or "",
        aurora_result.get("project_description", "") or "",
    )

    sdg_preds = aurora_result.get("sdg_predictions", {})
    preds = (
        [{"sdg": name, "prediction": score} for name, score in sdg_preds.items()]
        if isinstance(sdg_preds, dict)
        else sdg_preds
    )
    filtered = [p for p in preds if p.get("prediction", 0) > 0.4]

    response = {
        "projectName": aurora_result.get("project_name"),
        "projectUrl":  aurora_result.get("project_url"),
        "predictions": filtered,
        "recommendation": {
            "reason": rec["reason"],
            "suggestions": rec["suggestions"],
            "text_quality": rec["text_quality"],
        } if not filtered else None,
    }

    return jsonify(response), 200


# ---------------------------------------------------------------------------
# ST URL
# ---------------------------------------------------------------------------

@app.route('/api/classify_st_url', methods=['POST'])
def classify_st_url():
    data               = request.json
    projectName        = data.get('projectName')
    projectUrl         = data.get('projectUrl')
    projectDescription = data.get('projectDescription', '')

    if not projectDescription:
        return jsonify({'error': 'Project description is required'}), 400

    print("\n===== RUNNING SENTENCE TRANSFORMER URL MODEL =====")

    if not projectUrl:
        return jsonify({
            "projectName": projectName,
            "projectUrl":  projectUrl,
            "predictions": [],
            "message":     "No project URL provided, skipping URL-based classification",
        }), 200

    try:
        st_url_result = classify_url(
            url                 = projectUrl,
            project_description = projectDescription,
        )
        print("ST URL model completed successfully")

    # ── 400 — bad input from the user ────────────────────────────────────────
    # These all mean the URL is wrong in some way the user can fix themselves.
    except (InvalidURLError, UnsupportedHostError, ValueError) as e:
        print(f"ST URL model bad URL: {e}")
        return jsonify({
            "error":   str(e),
            "message": "Invalid or unsupported repository URL. "
                       "Accepted: github.com, gitlab.com, codeberg.org, bitbucket.org "
                       "and self-hosted GitLab instances.",
        }), 400

    # ── 404 — repo exists in a valid URL shape but can't be reached ──────────
    except RepositoryNotFoundError as e:
        print(f"ST URL model repo not found: {e}")
        return jsonify({
            "error":   str(e),
            "message": "Repository not found. Check the URL and ensure the repo is public.",
        }), 404

    # ── 429 — rate limited by the forge API ───────────────────────────────────
    except RateLimitError as e:
        print(f"ST URL model rate limited: {e}")
        return jsonify({
            "error":   str(e),
            "message": "Rate limit hit on the repository API. Try again in a few minutes.",
        }), 429

    # ── 502 — network/HTTP failure fetching from the forge ────────────────────
    except (FetchError, requests.exceptions.HTTPError) as e:
        print(f"ST URL model fetch error: {e}")
        return jsonify({
            "error":   str(e),
            "message": "Failed to fetch repository data. "
                       "Ensure the repository is public and the URL is correct.",
        }), 502

    # ── 500 — anything else (model failure, microservice down, etc.) ──────────
    except Exception as e:
        print(f"ST URL model unexpected error: {e}")
        return jsonify({
            "error":   str(e),
            "message": "Sentence Transformer URL model classification failed.",
        }), 500

    # ── Recommendation pipeline: assess why no SDGs were returned ──────────
    rec = assess_relevance(
        projectDescription or "",
        st_url_result.get("meta", {}).get("description", "") or "",
    )

    preds = [
        {"sdg": name, "prediction": score}
        for name, score in st_url_result.get("sdg_predictions", {}).items()
    ]
    filtered = [p for p in preds if p.get("prediction", 0) > 0.4]

    response = {
        "projectName": projectName,
        "projectUrl":  projectUrl,
        "predictions": filtered,
        "recommendation": {
            "reason": rec["reason"],
            "suggestions": rec["suggestions"],
            "text_quality": rec["text_quality"],
        } if not filtered else None,
    }

    return jsonify(response), 200


if __name__ == '__main__':
    # Port 8010 rather than Flask's default 5000 — macOS AirPlay Receiver
    # occupies 5000. Keep in sync with API_BASE_URL in frontend/services/api.ts.
    app.run(debug=True, port=8010)