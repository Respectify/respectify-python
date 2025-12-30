# Basic Usage Examples

This page demonstrates basic usage of the Respectify Python client.

## Setting Up the Client

```python
from respectify import RespectifyClient

# Initialize the client with your credentials
client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key",
    base_url="https://app.respectify.ai",  # Optional, defaults to production
    timeout=30.0  # Optional, timeout in seconds
)
```

## Initializing Topics

Before you can analyze comments, you need to initialize a topic (article):

### From Text Content

```python
# Initialize a topic from article text
topic_response = client.init_topic_from_text(
    text="This is the content of my article...",
    topic_description="Optional description of the topic"
)

article_id = topic_response.article_id
print(f"Created topic with ID: {article_id}")
```

### From URL

```python
# Initialize a topic from a URL
topic_response = client.init_topic_from_url(
    url="https://example.com/my-article",
    topic_description="Optional description"
)

article_id = topic_response.article_id
```

## Comment Analysis

### Spam Detection

```python
# Check if a comment is spam
spam_result = client.check_spam(
    comment="This is definitely not spam!",
    article_id=article_id
)

print(f"Is spam: {spam_result.is_spam}")
print(f"Confidence: {spam_result.confidence:.2f}")
print(f"Reasoning: {spam_result.reasoning}")
```

### Comment Quality Evaluation

```python
# Evaluate comment quality and toxicity
comment_score = client.evaluate_comment(
    comment="This is a thoughtful and well-reasoned comment.",
    article_id=article_id
)

print(f"Overall score: {comment_score.overall_score}/5")
print(f"Low effort: {comment_score.appears_low_effort}")
print(f"Toxicity score: {comment_score.toxicity_score:.2f}")
print(f"Toxicity explanation: {comment_score.toxicity_explanation}")

# Check for specific issues
if comment_score.logical_fallacies:
    print("Logical fallacies found:")
    for fallacy in comment_score.logical_fallacies:
        print(f"  - {fallacy.fallacy_name}: {fallacy.quoted_logical_fallacy_example}")

if comment_score.objectionable_phrases:
    print("Objectionable phrases found:")
    for phrase in comment_score.objectionable_phrases:
        print(f"  - {phrase.objectionable_content}: {phrase.explanation}")
```

### Relevance Checking

```python
# Check if comment is relevant to the topic
relevance_result = client.check_relevance(
    comment="This comment is about the main topic of the article.",
    article_id=article_id,
    banned_topics=["politics", "religion"]  # Optional
)

print(f"On topic: {relevance_result.on_topic.is_on_topic}")
print(f"Confidence: {relevance_result.on_topic.confidence:.2f}")
print(f"Reasoning: {relevance_result.on_topic.reasoning}")

# Check banned topics
banned = relevance_result.banned_topics
print(f"Banned topics detected: {banned.banned_topics}")
print(f"Quantity on banned topics: {banned.quantity_on_banned_topics:.2f}")
```

### Dogwhistle Detection

```python
# Check for dogwhistle language
dogwhistle_result = client.check_dogwhistle(
    comment="This seems like a normal comment.",
    sensitive_topics=["politics", "race"],  # Optional
    dogwhistle_examples=["example phrase"]  # Optional
)

print(f"Dogwhistles detected: {dogwhistle_result.detection.dogwhistles_detected}")
print(f"Confidence: {dogwhistle_result.detection.confidence:.2f}")
print(f"Reasoning: {dogwhistle_result.detection.reasoning}")

# Check details if dogwhistles were found
if dogwhistle_result.details:
    print(f"Terms: {dogwhistle_result.details.dogwhistle_terms}")
    print(f"Categories: {dogwhistle_result.details.categories}")
    print(f"Subtlety level: {dogwhistle_result.details.subtlety_level:.2f}")
    print(f"Harm potential: {dogwhistle_result.details.harm_potential:.2f}")
```

## Authentication Check

```python
# Verify your credentials
auth_result = client.check_user_credentials()

if auth_result.success:
    print("Authentication successful!")
else:
    print(f"Authentication failed: {auth_result.message}")
```

## Error Handling

```python
from respectify import AuthenticationError, BadRequestError, RespectifyError

try:
    result = client.check_spam("", article_id)  # Empty comment
except BadRequestError as e:
    print(f"Bad request: {e.message}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RespectifyError as e:
    print(f"API error: {e.message} (Status: {e.status_code})")
```