from services.recommendation_pipeline import _clean_text, _is_too_short

text = "This project is a Python React Django Flask application using PostgreSQL Redis Docker Kubernetes"
cleaned = _clean_text(text)
print(f"Cleaned: '{cleaned}'")
print(f"Word count: {len(cleaned.split())}")

tech_keywords = ["python", "javascript", "react", "api", "database",
                 "framework", "library", "container", "docker", "cls",
                 "function", "import", "class", "module"]
tech_count = sum(1 for kw in tech_keywords if kw in cleaned.lower())
print(f"Tech keywords found: {tech_count}")
print(f"Ratio: {tech_count / len(cleaned.split()) if len(cleaned.split()) > 0 else 'N/A'}")

# Check domain keywords
domain_keywords = {
    "health": ["health", "medical", "hospital", "patient", "clinical"],
    "education": ["education", "learning", "school", "student", "teaching"],
    "environment": ["environment", "climate", "ecological", "sustainability"],
    "water": ["water", "sanitation", "hygiene", "wash"],
    "energy": ["energy", "power", "electricity", "renewable"],
    "agriculture": ["agriculture", "farm", "farming", "crop", "rural"],
    "governance": ["governance", "policy", "government", "policy"],
    "gender": ["gender", "women", "equality", "female"],
}

cleaned_lower = cleaned.lower()
print("\nDomain keyword checks:")
for category, keywords in domain_keywords.items():
    found = [kw for kw in keywords if kw in cleaned_lower]
    if found:
        print(f"  {category}: {found}")

# Check problem keywords
problem_keywords = ["problem", "solution", "beneficiaries", "users", "impact",
                    "helps", "addresses", "reduces", "improves"]
print("\nProblem keyword checks:")
for kw in problem_keywords:
    if kw in cleaned_lower:
        print(f"  Found: {kw}")