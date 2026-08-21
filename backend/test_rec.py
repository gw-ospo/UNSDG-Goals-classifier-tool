from services.recommendation_pipeline import assess_relevance

# Test case 1: Too short description
result = assess_relevance("short", "short")
print("Test 1 - Too short:")
print(f"  relevant: {result['relevant']}, reason: {result['reason']}")
print(f"  suggestions: {result['suggestions'][:2]}...")
print()

# Test case 2: Heavily technical
result = assess_relevance(
    "This project is a Python React Django Flask application using PostgreSQL Redis Docker Kubernetes",
    "This project is a Python React Django Flask application using PostgreSQL Redis Docker Kubernetes"
)
print("Test 2 - Heavily technical:")
print(f"  relevant: {result['relevant']}, reason: {result['reason']}")
print(f"  suggestions: {result['suggestions'][:2]}...")
print()

# Test case 3: Good signals
result = assess_relevance(
    "This project helps rural farmers improve crop yields using sustainable agriculture techniques",
    "This project helps rural farmers improve crop yields using sustainable agriculture techniques"
)
print("Test 3 - Good signals:")
print(f"  relevant: {result['relevant']}, reason: {result['reason']}")
print(f"  text_quality: {result['text_quality']}")
print(f"  suggestions: {result['suggestions'][:2]}...")
print()

# Test case 4: With README
result = assess_relevance(
    "A web app that connects patients with doctors",
    "![image](img.png) [link](http://example.com) Heavy Python Django codebase with many dependencies"
)
print("Test 4 - Mixed signals:")
print(f"  relevant: {result['relevant']}, reason: {result['reason']}")
print(f"  text_quality: {result['text_quality']}")
print(f"  suggestions: {result['suggestions'][:2]}...")