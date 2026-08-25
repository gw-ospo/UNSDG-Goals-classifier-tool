import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from repo_fetcher import get_provider, ProviderError

GITLAB_TARGETS = [
    "https://gitlab.com/fdroid/fdroidclient",
    "https://gitlab.com/gitlab-org/gitlab-test",
    "https://gitlab.com/gitlab-org/gitlab",
    "https://gitlab.com/trapper-project/trapper"
]

def benchmark_gitlab_provider():
    print("=" * 75)
    print("RUNNING INTERACTIVE PROBE AGAINST PRODUCTION GITLAB INSTANCES")
    print("=" * 75)

    for url in GITLAB_TARGETS:
        print(f"\n🚀 Evaluating Path: {url}")
        try:
            # Initialize the provider via the strategy factory
            provider = get_provider(url)
            
            print(f"  ┌─ Provider Class: {provider.__class__.__name__}")
            print(f"  ├─ API Base Endpoint: {provider._API}")
            print(f"  ├─ Extracted Namespace (Owner): '{provider._owner}'")
            print(f"  ├─ Target Project (Repo):       '{provider._repo}'")
            print(f"  └─ URL-Encoded Project Path:    '{provider._encoded_path()}'")
            
            # Test Step 1: Topic Extraction API (uses projects/:id)
            print("  [Action] Querying Project Metadata & Topics...")
            topics = provider.fetch_topics()
            print(f"  └─ Extracted Topics Array: {topics}")
            
            # Test Step 2: Double-hop README Downloader (Metadata -> Raw Ref download)
            print("  [Action] Requesting Asynchronous README Text Blob...")
            readme = provider.fetch_readme()
            if readme:
                first_lines = "\\n".join(readme.strip().split("\n")[:2])
                print(f"  └─ Stream Received ({len(readme)} bytes). Content Snippet:")
                print(f"     \"\"\"{first_lines}...\"\"\"")
            else:
                print("  └─ Status: Request returned an empty string.")

        except ProviderError as err:
            print(f"  ❌ Operational Provider Exception Raised: [{type(err).__name__}] - {err}")
        except Exception as err:
            print(f"  🚨 Runtime Interpreter Crash: {err}")

    print("\n" + "=" * 75)
    print("GITLAB COMPLIANCE TESTING RUN COMPLETE")
    print("=" * 75)

if __name__ == "__main__":
    res = benchmark_gitlab_provider()
    print(res)
