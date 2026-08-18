"""
test_dpga_real_positives.py

Caveman v3 — real positive project, real ground truth, pull straight
from DPGA registry spreadsheet (single-SDG-tagged entries only, for
clean signal). Compare predicted vs ground truth, compute COSINE_LOW/HIGH.
"""

import os
import sys
import requests
import numpy as np
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import sdg_constants
from embedding_url import get_embedder

ST_URL_ENDPOINT = "http://127.0.0.1:8010/api/classify_st_url"

# ── negative set, unchanged from before ───────────────────────────────────
NEGATIVE_PROJECTS = [
    {"projectName": "redis/redis", "projectUrl": "https://github.com/redis/redis", "projectDescription": "In-memory data structure store, used as database, cache and message broker."},
    {"projectName": "facebook/react", "projectUrl": "https://github.com/facebook/react", "projectDescription": "A JavaScript library for building user interfaces with reusable components."},
    {"projectName": "gitlab-org/gitlab", "projectUrl": "https://gitlab.com/gitlab-org/gitlab", "projectDescription": "DevOps platform for source code management, CI/CD, and project planning."},
    {"projectName": "docker/compose", "projectUrl": "https://github.com/docker/compose", "projectDescription": "Tool for defining and running multi-container Docker applications."},
    {"projectName": "Codeberg/pages-server", "projectUrl": "https://codeberg.org/Codeberg/pages-server", "projectDescription": "Static site hosting infrastructure server for Codeberg Pages."},
    {"projectName": "prettier/prettier", "projectUrl": "https://github.com/prettier/prettier", "projectDescription": "An opinionated code formatter supporting many languages and editors."},
    {"projectName": "vercel/next.js", "projectUrl": "https://github.com/vercel/next.js", "projectDescription": "The React Framework for the Web, used for building server-rendered applications."},
    {"projectName": "kubernetes/kubernetes", "projectUrl": "https://github.com/kubernetes/kubernetes", "projectDescription": "Production-grade container orchestration system for automating deployment and scaling."},
    {"projectName": "pytorch/pytorch", "projectUrl": "https://github.com/pytorch/pytorch", "projectDescription": "Tensors and dynamic neural networks in Python with strong GPU acceleration."},
    {"projectName": "nginx/nginx", "projectUrl": "https://github.com/nginx/nginx", "projectDescription": "High performance web server and reverse proxy."},
    {"projectName": "sveltejs/svelte", "projectUrl": "https://github.com/sveltejs/svelte", "projectDescription": "Cybernetically enhanced web apps framework."},
    {"projectName": "elastic/elasticsearch", "projectUrl": "https://github.com/elastic/elasticsearch", "projectDescription": "Distributed, RESTful search and analytics engine."},
    {"projectName": "apache/kafka", "projectUrl": "https://github.com/apache/kafka", "projectDescription": "Distributed event streaming platform for high-performance data pipelines."},
    {"projectName": "webpack/webpack", "projectUrl": "https://github.com/webpack/webpack", "projectDescription": "A module bundler for JavaScript applications."},
    {"projectName": "golang/go", "projectUrl": "https://github.com/golang/go", "projectDescription": "The Go programming language, its compiler, and standard library."},
    {"projectName": "rust-lang/rust", "projectUrl": "https://github.com/rust-lang/rust", "projectDescription": "A language empowering everyone to build reliable and efficient software."},
    {"projectName": "microsoft/vscode", "projectUrl": "https://github.com/microsoft/vscode", "projectDescription": "Visual Studio Code, a lightweight but powerful source code editor."},
    {"projectName": "postgres/postgres", "projectUrl": "https://github.com/postgres/postgres", "projectDescription": "Mirror of the official PostgreSQL GIT repository, an object-relational database system."},
    {"projectName": "grafana/grafana", "projectUrl": "https://github.com/grafana/grafana", "projectDescription": "The open and composable observability and data visualization platform."},
    {"projectName": "hashicorp/terraform", "projectUrl": "https://github.com/hashicorp/terraform", "projectDescription": "Tool for building, changing, and versioning infrastructure safely and efficiently."},
    {"projectName": "apache/airflow", "projectUrl": "https://github.com/apache/airflow", "projectDescription": "Platform to programmatically author, schedule and monitor workflows."},
    {"projectName": "electron/electron", "projectUrl": "https://github.com/electron/electron", "projectDescription": "Build cross-platform desktop apps with JavaScript, HTML, and CSS."},
    {"projectName": "tensorflow/tensorflow", "projectUrl": "https://github.com/tensorflow/tensorflow", "projectDescription": "An open source machine learning framework for everyone."},
    {"projectName": "ansible/ansible", "projectUrl": "https://github.com/ansible/ansible", "projectDescription": "Radically simple IT automation platform for configuration management and deployment."},
    {"projectName": "vitejs/vite", "projectUrl": "https://github.com/vitejs/vite", "projectDescription": "Next generation frontend build tooling, fast and lean."},
    {"projectName": "expressjs/express", "projectUrl": "https://github.com/expressjs/express", "projectDescription": "Fast, unopinionated, minimalist web framework for Node.js."},
    {"projectName": "django/django", "projectUrl": "https://github.com/django/django", "projectDescription": "The Web framework for perfectionists with deadlines."},
    {"projectName": "spring-projects/spring-boot", "projectUrl": "https://github.com/spring-projects/spring-boot", "projectDescription": "Framework to build production-grade Spring-based applications quickly."},
    {"projectName": "mongodb/mongo", "projectUrl": "https://github.com/mongodb/mongo", "projectDescription": "The MongoDB Database, a document-oriented NoSQL database."},
    {"projectName": "jestjs/jest", "projectUrl": "https://github.com/jestjs/jest", "projectDescription": "Delightful JavaScript testing framework with a focus on simplicity."},
]
# ── real positive set, pulled from DPGA registry xlsx, single-SDG-tagged ──
# ground_truth_sdg is the ACTUAL flagged SDG number from the registry data
POSITIVE_PROJECTS = [
    {"projectName": "Food Fortification Quality Management System",
     "projectUrl": "https://github.com/Food-Fortification/Food-Fortification-Quality-Management-System",
     "projectDescription": "FFQMS is an end-to-end digital solution that ensures quality assurance (QA), quality control (QC), and traceability starting from the procurement of raw materials in food fortification.",
     "ground_truth_sdg": 2},
    {"projectName": "AccessMod",
     "projectUrl": "https://github.com/unige-geohealth/accessmod",
     "projectDescription": "AccessMod is a free, open-source, standalone software to model physical accessibility to health services, to account for shortage of capacity in these services, to measure referral times and distances between health services.",
     "ground_truth_sdg": 3},
    {"projectName": "Android FHIR SDK",
     "projectUrl": "https://github.com/google/android-fhir",
     "projectDescription": "The Android FHIR SDK is a set of Kotlin libraries for building offline-capable, mobile-first healthcare applications using the HL7 FHIR standard.",
     "ground_truth_sdg": 3},
    {"projectName": "Chamilo",
     "projectUrl": "https://github.com/chamilo/chamilo-lms",
     "projectDescription": "Chamilo is an Open Source Learning Management System that vows to help increase the availability of quality education around the world.",
     "ground_truth_sdg": 4},
    {"projectName": "cQube",
     "projectUrl": "https://github.com/Sunbird-cQube/cQube_Base",
     "projectDescription": "cQube is an open-source platform for data-based insights in education. It allows for aggregated data to be visualized in a simple fashion, leading to insights and better decision-making for education administrators.",
     "ground_truth_sdg": 4},
    {"projectName": "Safe YOU",
     "projectUrl": "https://github.com/safeyou-space/safeyou",
     "projectDescription": "Safe YOU is an innovative technological solution created to reduce gender-based violence through a mobile application and multifunctional web platform.",
     "ground_truth_sdg": 5},
    {"projectName": "Energy Access Explorer",
     "projectUrl": "https://github.com/energyaccessexplorer",
     "projectDescription": "The first open-source, online and interactive geospatial platform that enables energy planners, clean energy entrepreneurs, donors, and development institutions to identify opportunities for energy access interventions.",
     "ground_truth_sdg": 7},
    {"projectName": "Mifos X",
     "projectUrl": "https://github.com/openMF/android-client",
     "projectDescription": "The Mifos X DPG suite includes a core banking platform, payment orchestration engine, and mobile banking interfaces to enable effective delivery of financial services to the world's poor.",
     "ground_truth_sdg": 8},
    {"projectName": "Open Supply Hub",
     "projectUrl": "https://github.com/opensupplyhub/open-supply-hub",
     "projectDescription": "Open Supply Hub is a non-profit powering the transition to safe and sustainable production with the world's most complete, open and accessible global map of production facilities.",
     "ground_truth_sdg": 8},
    {"projectName": "Janssen Project",
     "projectUrl": "https://github.com/JanssenProject/jans",
     "projectDescription": "A low-code digital identity platform for workforce, consumer and citizen identity based on open standards like OAuth, OpenID, FIDO and SCIM.",
     "ground_truth_sdg": 9},
    {"projectName": "Deon",
     "projectUrl": "https://github.com/drivendataorg/deon",
     "projectDescription": "Deon is a command line tool that allows you to easily add an ethics checklist to your data science projects, covering data collection, storage, analysis, and modeling fairness concerns.",
     "ground_truth_sdg": 10},
    {"projectName": "UrbanPy",
     "projectUrl": "https://github.com/EL-BID/urbanpy",
     "projectDescription": "A library to download, process and visualize high resolution urban data in an easy and fast way. It also estimates and visualizes urban service accessibility.",
     "ground_truth_sdg": 11},
    {"projectName": "CodeCarbon",
     "projectUrl": "https://github.com/mlco2/codecarbon",
     "projectDescription": "CodeCarbon estimates how much carbon dioxide is produced by the cloud or personal computing resources used to execute machine learning code, to raise awareness of environmental impact.",
     "ground_truth_sdg": 12},
    {"projectName": "ClimWeb",
     "projectUrl": "https://github.com/wmo-raf/climweb",
     "projectDescription": "Open-source platform enabling climate and environmental institutions to deliver services, featuring state-of-the-art data visualizations, satellite imagery, and climate early warning products.",
     "ground_truth_sdg": 13},
    {"projectName": "Zamba",
     "projectUrl": "https://github.com/drivendataorg/zamba",
     "projectDescription": "AI tools for wildlife monitoring with camera trap videos. Zamba is a command-line tool built in Python to automatically identify the species seen in camera trap footage.",
     "ground_truth_sdg": 15},
    {"projectName": "Aid Management Platform",
     "projectUrl": "https://github.com/devgateway/amp",
     "projectDescription": "AMP helps governments and development partners gather, access, and monitor information on development activities, with the goal of increasing aid effectiveness.",
     "ground_truth_sdg": 16},
    {"projectName": "Care | Open Healthcare Network", "projectUrl": "https://github.com/coronasafe/care",
     "projectDescription": "CARE is a transformative healthcare management system, centralizing patient and capacity management across hospitals.",
     "ground_truth_sdg": 3},
    {"projectName": "Connect For Life", "projectUrl": "https://github.com/johnsonandjohnson/openmrs-distro-cfl",
     "projectDescription": "Connect for Life is a communication platform built on OpenMRS. The platform engages with patients remotely and provides continuity of care.",
     "ground_truth_sdg": 3},
    {"projectName": "Data Observation Toolkit", "projectUrl": "https://github.com/datakind/Data-Observation-Toolkit",
     "projectDescription": "DOT is a toolkit used to monitor data as it's collected and enters a database, to flag problems with data integrity and quality.",
     "ground_truth_sdg": 3},
    {"projectName": "Jellow AAC Communicator", "projectUrl": "https://github.com/jellow-aac/jellow-communicator-android",
     "projectDescription": "Jellow Basic Communicator is a freely downloadable Augmentative and Alternative Communication (AAC) system that uses icons/images.",
     "ground_truth_sdg": 4},
    {"projectName": "Sunbird Saral", "projectUrl": "https://github.com/Sunbird-Saral/Project-Saral",
     "projectDescription": "Sunbird Saral enables users to create structured digital information from a physical form, for education administration.",
     "ground_truth_sdg": 4},
    {"projectName": "The Turing Way", "projectUrl": "https://github.com/the-turing-way/the-turing-way",
     "projectDescription": "The Turing Way is an open source, open collaboration and community-driven guide on data science education.",
     "ground_truth_sdg": 4},
    {"projectName": "POTLOCK", "projectUrl": "https://github.com/potlock",
     "projectDescription": "POTLOCK is the portal for public goods, non-profits, and communities to raise funds transparently through a global donor network.",
     "ground_truth_sdg": 8},
    {"projectName": "La Suite Drive", "projectUrl": "https://github.com/suitenumerique/drive/",
     "projectDescription": "Drive empowers teams to securely store, share, and collaborate on files while maintaining full control over their data.",
     "ground_truth_sdg": 9},
    {"projectName": "La Suite Meet", "projectUrl": "https://github.com/suitenumerique/meet",
     "projectDescription": "Powered by LiveKit, La Suite Meet is a video conference software offering Zoom-level performance with high-quality video and audio.",
     "ground_truth_sdg": 9},
    {"projectName": "LibreSign", "projectUrl": "https://github.com/LibreSign/libresign/",
     "projectDescription": "LibreSign is an open-source digital and electronic signature platform ensuring secure, legally compliant document signing.",
     "ground_truth_sdg": 9},
    {"projectName": "Oobee", "projectUrl": "https://github.com/GovTechSG/oobee-desktop",
     "projectDescription": "Oobee (formerly Purple A11y) is a customisable, automated accessibility testing tool that finds accessibility issues.",
     "ground_truth_sdg": 10},
    {"projectName": "Accessible Kazakhstan", "projectUrl": "https://github.com/qlt2020/doskaz",
     "projectDescription": "A model of an online map with information on accessibility of public facilities that enables people with limited mobility to navigate public space.",
     "ground_truth_sdg": 11},
    {"projectName": "DiCRA", "projectUrl": "https://github.com/undpindia/dicra",
     "projectDescription": "Data in Climate Resilient Agriculture is a collaborative geospatial platform providing open access to key geospatial datasets pertinent to agriculture.",
     "ground_truth_sdg": 13},
    {"projectName": "Altinn", "projectUrl": "https://github.com/Altinn/altinn-studio",
     "projectDescription": "Altinn is a platform for digital dialogue between businesses, private individuals and public agencies, used by government.",
     "ground_truth_sdg": 16},
    {"projectName": "Consul Democracy", "projectUrl": "https://github.com/consul/consul",
     "projectDescription": "Consul Democracy is a complete citizen participation tool for an open, transparent, and democratic government.",
     "ground_truth_sdg": 16},
    {"projectName": "FormSG", "projectUrl": "https://github.com/opengovsg/FormSG",
     "projectDescription": "FormSG is a form builder tool that enables public officers to instantly create customisable forms to safely collect citizen data.",
     "ground_truth_sdg": 16},
]



def hit_st_url(project: dict) -> dict:
    payload = {
        "projectName":        project["projectName"],
        "projectUrl":         project["projectUrl"],
        "projectDescription": project["projectDescription"],
    }
    r = requests.post(ST_URL_ENDPOINT, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def extract_predicted_sdg_numbers(predictions: list[dict]) -> set[int]:
    nums = set()
    for p in predictions:
        match = re.match(r"SDG\s*(\d+)", p.get("sdg", ""))
        if match:
            nums.add(int(match.group(1)))
    return nums


def get_raw_cosine_sims(text: str) -> np.ndarray:
    emb = get_embedder()
    v_text = emb.encode([text], normalize_embeddings=True)[0]
    v_lbls = emb.encode(sdg_constants.SDG_DESCS, normalize_embeddings=True)
    return np.dot(v_lbls, v_text)


def main():
    results = {"positive": [], "negative": [], "all": []}
    ground_truth_hits = 0
    ground_truth_total = 0

    print("=== NEGATIVE PROJECTS ===")
    for proj in NEGATIVE_PROJECTS:
        print(f"\n--- {proj['projectName']} ---")
        try:
            response = hit_st_url(proj)
            print(f"  predictions: {response.get('predictions')}")
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue

        sims = get_raw_cosine_sims(proj["projectDescription"])
        top_sim = float(np.max(sims))
        print(f"  top raw cosine sim: {top_sim:.3f}")
        results["all"].extend(sims.tolist())
        results["negative"].append(top_sim)
        time.sleep(3)

    print("\n\n=== POSITIVE PROJECTS (real DPGA ground truth) ===")
    for proj in POSITIVE_PROJECTS:
        print(f"\n--- {proj['projectName']} (ground truth: SDG {proj['ground_truth_sdg']}) ---")
        try:
            response = hit_st_url(proj)
            predicted = extract_predicted_sdg_numbers(response.get("predictions", []))
            print(f"  predictions: {response.get('predictions')}")
            print(f"  predicted SDGs: {predicted}")
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue

        ground_truth_total += 1
        if proj["ground_truth_sdg"] in predicted:
            ground_truth_hits += 1
            print(f"  ✓ MATCH — correctly identified SDG {proj['ground_truth_sdg']}")
        else:
            print(f"  ✗ MISS — ground truth SDG {proj['ground_truth_sdg']} not in prediction")

        sims = get_raw_cosine_sims(proj["projectDescription"])
        top_sim = float(np.max(sims))
        print(f"  top raw cosine sim: {top_sim:.3f}")
        results["all"].extend(sims.tolist())
        results["positive"].append(top_sim)
        time.sleep(3)

    print("\n\n--- GROUND TRUTH ACCURACY ---")
    if ground_truth_total:
        print(f"correctly matched: {ground_truth_hits}/{ground_truth_total} "
              f"({ground_truth_hits/ground_truth_total:.1%})")

    print("\n--- DISTRIBUTIONS (raw cosine top score) ---")
    for key in ("negative", "positive", "all"):
        vals = results[key]
        if not vals:
            continue
        pct = np.percentile(vals, [10, 25, 50, 75, 90])
        print(f"{key:10s} n={len(vals):3d}  p10={pct[0]:.3f} p25={pct[1]:.3f} "
              f"p50={pct[2]:.3f} p75={pct[3]:.3f} p90={pct[4]:.3f}")

    if results["negative"] and results["positive"]:
        neg_p90 = np.percentile(results["negative"], 90)
        pos_p25 = np.percentile(results["positive"], 25)
        print(f"\nCOSINE_LOW  = {neg_p90:.3f}")
        print(f"COSINE_HIGH = {pos_p25:.3f}")
        if neg_p90 >= pos_p25:
            print("WARNING: overlap — bounds still unreliable")
        else:
            print(f"Gap: {pos_p25 - neg_p90:.3f} — clean separation" if pos_p25 - neg_p90 > 0.05
                  else "Gap small — borderline, more data recommended")


if __name__ == "__main__":
    main()