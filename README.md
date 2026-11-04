# Respectify Python Client

[![PyPI version](https://badge.fury.io/py/respectify.svg)](https://badge.fury.io/py/respectify)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python client library for the [Respectify API](https://respectify.ai), providing both synchronous and asynchronous interfaces for comment moderation, spam detection, toxicity analysis, and dogwhistle detection.

Respectify aims to be more than comment moderation: it tries to teach and edify users when a comment is rejected.

For bloggers, companies with articles, etc it provides a way to keep discourse civil and on-topic without censorship.

## Features

- Supports the full [Resepctify](https://respectify.ai) feature set for analysing comments and discussion
- Both synchronous (`RespectifyClient`) and asynchronous (`RespectifyAsyncClient`) clients
- The Megacall endpoint allows multiple analyses in a single request

## Installation

```bash
pip install respectify
```

## Quick Start

### Synchronous Client

```python
from respectify import RespectifyClient

# Initialize client
client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)

# Initialize a topic
# Comments on a discussion are in the context of the discussion -- this is any starting material
topic = client.init_topic_from_text("This is my article content")
article_id = topic.article_id

# Evaluate comment quality and toxicity
score = client.evaluate_comment("This is a thoughtful comment", article_id)
print(f"Health: {score.overall_score}/5, Toxicity: {score.toxicity_score:.2f}")

# Comment health: one level per item -- off, relaxed, standard (default), strict, zero_tolerance.
# Threats, identity attacks, sexual content and harassment can only be made stricter.
from respectify import ModerationTolerances, ToleranceLevel
score = client.evaluate_comment("That's a silly take, mate", article_id,
                                tolerances=ModerationTolerances(insult=ToleranceLevel.RELAXED, quality=ToleranceLevel.OFF))
if score.exceeds_tolerance:  # the verdict to act on
    for name, item in score.health_items.items():
        print(f"{name}: {item.score}/5 (accepts {item.minimum}+)")

# Check if a comment is spam
spam_result = client.check_spam("Great post!", article_id)
print(f"Is spam: {spam_result.is_spam}")

# Perspective-compatible scoring for migrations from Google's Perspective API
perspective = client.perspective.analyze_comment(
    {
        "comment": {"text": "You clearly did not read the article."},
        "requestedAttributes": {
            "TOXICITY": {},
            "INSULT": {},
        },
    }
)
print(perspective.attributeScores["TOXICITY"].summaryScore.value)
```

### Asynchronous Client

```python
import asyncio
from respectify import RespectifyAsyncClient

async def main():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    # Initialize topic
    topic = await client.init_topic_from_text("Article content")
    article_id = topic.article_id
    
    # Run multiple analyses concurrently
    spam_task = client.check_spam("Great post!", article_id)
    score_task = client.evaluate_comment("Thoughtful comment", article_id)
    
    spam_result, score_result = await asyncio.gather(spam_task, score_task)
    
    print(f"Spam: {spam_result.is_spam}, Health: {score_result.overall_score}/5")

asyncio.run(main())
```

### Megacall for Efficiency

Perform multiple analyses in a single API call:

```python
# Instead of multiple separate calls...
result = client.megacall(
    comment="Test comment",
    article_id=article_id, # pre-registered with init_topic_from_url() (reads a page) or init_topic_from_text() (anything you send it)
    include_spam=True,
    include_relevance=True, 
    include_comment_score=True,
    include_dogwhistle=True
)

# Access individual results
print(f"Spam: {result.spam.is_spam if result.spam else 'N/A'}")
print(f"Health: {result.comment_score.overall_score if result.comment_score else 'N/A'}/5")
print(f"On topic: {result.relevance.on_topic.is_on_topic if result.relevance else 'N/A'}")
print(f"Dogwhistles: {result.dogwhistle.detection.dogwhistles_detected if result.dogwhistle else 'N/A'}")
```

## API Reference

### Available Methods

**Topic Management:**
- `init_topic_from_text(text, topic_description=None)` - Initialize topic from text content
- `init_topic_from_url(url, topic_description=None)` - Initialize topic from URL

**Comment Analysis:**
- `evaluate_comment(comment, article_id, revision_token=None)` - Evaluates a comment on logical fallacies, objectionable phrases, negative tone, low effort
- `check_relevance(comment, article_id, banned_topics=None, revision_token=None)` - Relevance and banned topic detection
- `check_dogwhistle(comment, article_id, sensitive_topics=None, dogwhistle_examples=None, revision_token=None)` - Dogwhistle detection
- `check_spam(comment, article_id=None, revision_token=None)` - Spam detection

Each of these has a `*_response` twin (`evaluate_comment_response`, `check_spam_response`, ...) that returns a `RespectifyResponse` with the same result in `.result` plus the free plan's `.revision_token` (see below).

**Batch Operations:**
- `megacall(comment, article_id, **options)` - Multiple analyses in one call (`megacall_response` returns the `RespectifyResponse`)

**Perspective Compatibility:**
- `client.perspective.analyze_comment(request)` - Public Perspective-compatible `analyzeComment`
- `client.perspective.suggest_comment_score(request)` - Public Perspective-compatible `suggestCommentScore`

**Authentication:**
- `check_user_credentials()` - Verify API credentials work without calling any normal API

### Response Schemas

All API responses are parsed into strongly-typed Pydantic models:

- `InitTopicResponse` - Topic initialization result
- `SpamDetectionResult` - Spam analysis with confidence scores
- `CommentScore` - Quality metrics and toxicity analysis
- `CommentRelevanceResult` - Topic relevance and banned topic detection  
- `DogwhistleResult` - Dogwhistle detection with detailed analysis
- `MegaCallResult` - Container for multiple analysis results
- `UserCheckResponse` - Authentication verification result
- `RespectifyResponse[T]` - Returned by the `*_response` methods: the parsed result in `.result` and the free plan's `.revision_token`

### Error Handling

```python
from respectify import (
    RespectifyError,                # Base exception; .error_code is the server's machine-readable code, if any
    AuthenticationError,            # Invalid credentials (401)
    BadRequestError,                # Invalid parameters (400)
    PaymentRequiredError,           # Credit balance too low for the call (402)
    FreeAllowanceExhaustedError,    # Free plan's comments used up (402, subclass of PaymentRequiredError); .upgrade_url
    RevisionLimitReachedError,      # Free plan: this comment has had all its attempts (409)
    RateLimitedError,               # Too many requests (429); .retry_after_seconds when the server says
    RequestTimeoutError,            # The request timed out before a response arrived; .timeout_seconds
    ServerError,                    # Server issues (500+)
)

try:
    result = client.check_spam("test", article_id)
except AuthenticationError:
    print("Please check your API credentials")
except FreeAllowanceExhaustedError as e:
    print(f"Free comments used up. Add credit at {e.upgrade_url}")
except PaymentRequiredError:
    print("Your credit balance does not cover this call. Add funds to continue.")
except RateLimitedError as e:
    print(f"Slow down; retry in {e.retry_after_seconds} seconds")
except BadRequestError as e:
    print(f"Invalid request: {e.message}")
```

### The Free Plan and Revision Tokens

On the free plan each comment is assessed free of charge a limited number of times: the first assessment plus a few revisions, after the writer has been shown what to improve. The server tells the two apart with a token it issues in the `X-Respectify-Revision-Token` response header. Read it with a `*_response` method and send it back with `revision_token=` when the same comment is re-assessed, so the revision is not counted as a new comment:

```python
first = client.evaluate_comment_response(comment, article_id)
if first.result.exceeds_tolerance:
    # Show first.result's findings to the writer and let them revise, then:
    revised = client.evaluate_comment(revised_comment, article_id, revision_token=first.revision_token)
```

`revision_token` is `None` for paid accounts, which never receive one, and the Perspective-compatible endpoints never use it. Sending the token back once the comment has had all its attempts raises `RevisionLimitReachedError`; using up the plan's free comments raises `FreeAllowanceExhaustedError`, whose `upgrade_url` points at the billing page.

### Response Sanitization

All string values in API responses are automatically HTML-encoded to prevent XSS. API responses echo back user-submitted comment text (in quoted fallacies, objectionable phrases, etc.) so this encoding is applied by default to make responses safe to render in HTML.

## Configuration

### Client Options

```python
client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)
```

## Development

### Running Tests

You will need to provide real Respectify credentials, because this will make calls against the actual API - not a mocked version. Use a key dedicated to testing to separate this from your normal usage.

Create a `.env` file for testing:

```bash
RESPECTIFY_EMAIL=your-email@example.com
RESPECTIFY_API_KEY=your-api-key
REAL_ARTICLE_ID=a-genuine-initialised-article
```

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with real API (requires .env file with real credentials)
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=respectify --cov-report=html
```

### Building Documentation

```bash
# Install documentation dependencies  
pip install -e ".[docs]"

# Build documentation
cd docs
make html

# Serve documentation locally
python -m http.server 8000 --directory _build/html
```

### Code Quality

```bash
# Run ruff linting and formatting
ruff check respectify/
ruff format respectify/

# Beartype provides runtime type checking automatically
# Big fans of beartype here
```

## Requirements

- Python 3.9+
- httpx >= 0.24.0
- pydantic >= 2.0.0  
- beartype >= 0.15.0

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Full API documentation](https://docs.respectify.org)
- **Issues**: [GitHub Issues](https://github.com/respectify/respectify-python/issues)
- **Website**: [Respectify.ai](https://respectify.ai)

## Changelog

### v0.1.0 (2025-01-XX)

- Initial release
- Synchronous and asynchronous client support
- Complete API coverage for all Respectify endpoints
- Comprehensive type safety with Pydantic schemas
- Megacall support for efficient batch operations
- Full test suite with real API integration
- Sphinx documentation with examples
