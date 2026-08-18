import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICES_DIR = os.path.join(BACKEND_DIR, "services")

for path in (BACKEND_DIR, SERVICES_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

# Manual, live-network verification / evaluation scripts — not pytest suites.
# eval_dpga_150.py pulls in heavy ML deps (transformers, sentence-transformers)
# and hits live services (GitHub, Groq, GE-Lab microservice); it is run directly.
collect_ignore = [
    "test_dpga_real_positives.py",
    "test_gitlab_provider.py",
    "eval_dpga_150.py",
]