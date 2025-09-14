# Megacall Examples

The `megacall` method allows you to perform multiple types of analysis in a single API request, which is more efficient than making separate calls for each analysis type.

## Basic Megacall Usage

```python
from respectify import RespectifyClient

client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)

# Initialize topic
topic = client.init_topic_from_text("Article about Python programming")
article_id = topic.article_id

# Perform multiple analyses in one call
result = client.megacall(
    comment="This is a comprehensive comment about Python programming",
    article_id=article_id,
    include_spam=True,
    include_relevance=True,
    include_comment_score=True,
    include_dogwhistle=True
)

# Access individual results
if result.spam:
    print(f"Spam detected: {result.spam.is_spam}")
    print(f"Spam confidence: {result.spam.confidence:.2f}")

if result.relevance:
    print(f"On topic: {result.relevance.on_topic.is_on_topic}")
    print(f"Banned topics: {result.relevance.banned_topics.banned_topics}")

if result.comment_score:
    print(f"Quality score: {result.comment_score.overall_score}/5")
    print(f"Toxicity score: {result.comment_score.toxicity_score:.2f}")

if result.dogwhistle:
    print(f"Dogwhistles detected: {result.dogwhistle.detection.dogwhistles_detected}")
```

## Selective Analysis

You can choose which analyses to include:

```python
# Only spam and quality analysis
result = client.megacall(
    comment="Test comment",
    article_id=article_id,
    include_spam=True,
    include_comment_score=True
    # include_relevance and include_dogwhistle are False by default
)

# Only the requested analyses will be populated
assert result.spam is not None
assert result.comment_score is not None
assert result.relevance is None
assert result.dogwhistle is None
```

## Advanced Parameters

### Banned Topics for Relevance Analysis

```python
result = client.megacall(
    comment="This comment discusses political issues",
    article_id=article_id,
    include_relevance=True,
    banned_topics=["politics", "religion", "controversial topics"]
)

if result.relevance:
    banned = result.relevance.banned_topics
    print(f"Banned topics found: {banned.banned_topics}")
    print(f"Quantity on banned topics: {banned.quantity_on_banned_topics:.2f}")
```

### Dogwhistle Detection Parameters

```python
result = client.megacall(
    comment="This comment might contain coded language",
    article_id=article_id,
    include_dogwhistle=True,
    sensitive_topics=["politics", "race", "social issues"],
    dogwhistle_examples=[
        "coded phrase example",
        "another dogwhistle pattern"
    ]
)

if result.dogwhistle and result.dogwhistle.details:
    details = result.dogwhistle.details
    print(f"Dogwhistle terms: {details.dogwhistle_terms}")
    print(f"Categories: {details.categories}")
    print(f"Harm potential: {details.harm_potential:.2f}")
```

## Async Megacall

```python
import asyncio
from respectify import RespectifyAsyncClient

async def async_megacall_example():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    topic = await client.init_topic_from_text("Async programming tutorial")
    article_id = topic.article_id
    
    # Async megacall
    result = await client.megacall(
        comment="Great explanation of async/await patterns!",
        article_id=article_id,
        include_spam=True,
        include_relevance=True,
        include_comment_score=True
    )
    
    print(f"Analysis complete:")
    print(f"  Spam: {result.spam.is_spam if result.spam else 'Not analyzed'}")
    print(f"  Quality: {result.comment_score.overall_score if result.comment_score else 'Not analyzed'}/5")
    print(f"  Relevant: {result.relevance.on_topic.is_on_topic if result.relevance else 'Not analyzed'}")

asyncio.run(async_megacall_example())
```

## Batch Processing with Megacall

```python
def batch_moderate_comments(client, comments, article_id):
    """Efficiently moderate multiple comments using megacall."""
    
    results = []
    
    for i, comment in enumerate(comments):
        print(f"Processing comment {i+1}/{len(comments)}")
        
        try:
            result = client.megacall(
                comment=comment,
                article_id=article_id,
                include_spam=True,
                include_relevance=True,
                include_comment_score=True,
                include_dogwhistle=True,
                banned_topics=["politics", "religion"]
            )
            
            # Create summary
            summary = {
                'comment': comment[:100] + ('...' if len(comment) > 100 else ''),
                'spam': result.spam.is_spam if result.spam else None,
                'spam_confidence': result.spam.confidence if result.spam else None,
                'quality_score': result.comment_score.overall_score if result.comment_score else None,
                'toxicity_score': result.comment_score.toxicity_score if result.comment_score else None,
                'on_topic': result.relevance.on_topic.is_on_topic if result.relevance else None,
                'banned_topics': result.relevance.banned_topics.banned_topics if result.relevance else [],
                'dogwhistles': result.dogwhistle.detection.dogwhistles_detected if result.dogwhistle else None
            }
            
            results.append(summary)
            
        except Exception as e:
            print(f"Error processing comment {i+1}: {e}")
            results.append({
                'comment': comment[:100],
                'error': str(e)
            })
    
    return results

# Usage
client = RespectifyClient(email="...", api_key="...")
topic = client.init_topic_from_text("Discussion about programming")

comments = [
    "Great article, very informative!",
    "This is spam - buy our product at spamsite.com",
    "I disagree with the political implications here",
    "Could you provide more examples?",
    "First comment! Love this content."
]

results = batch_moderate_comments(client, comments, topic.article_id)

# Print summary
for result in results:
    if 'error' in result:
        print(f"❌ ERROR: {result['comment']} - {result['error']}")
    else:
        status_icons = []
        if result['spam']:
            status_icons.append("🚫 SPAM")
        if result['quality_score'] and result['quality_score'] <= 2:
            status_icons.append("📉 LOW QUALITY")
        if result['toxicity_score'] and result['toxicity_score'] > 0.7:
            status_icons.append("☠️ TOXIC")
        if result['dogwhistles']:
            status_icons.append("🔍 DOGWHISTLE")
        if not result['on_topic']:
            status_icons.append("❓ OFF-TOPIC")
        
        status = " | ".join(status_icons) if status_icons else "✅ CLEAN"
        print(f"{status}: {result['comment']}")
```

## Async Batch Processing

```python
import asyncio
from respectify import RespectifyAsyncClient

async def async_batch_megacall(client, comments, article_id, max_concurrent=5):
    """Process multiple comments concurrently with rate limiting."""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_comment(comment):
        async with semaphore:
            try:
                return await client.megacall(
                    comment=comment,
                    article_id=article_id,
                    include_spam=True,
                    include_relevance=True,
                    include_comment_score=True
                )
            except Exception as e:
                print(f"Error processing comment: {e}")
                return None
    
    # Create tasks
    tasks = [process_comment(comment) for comment in comments]
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks)
    
    # Process results
    for i, (comment, result) in enumerate(zip(comments, results)):
        if result is None:
            print(f"Comment {i+1}: FAILED")
            continue
            
        flags = []
        if result.spam and result.spam.is_spam:
            flags.append("SPAM")
        if result.comment_score and result.comment_score.overall_score <= 2:
            flags.append("LOW_QUALITY")
        if result.relevance and not result.relevance.on_topic.is_on_topic:
            flags.append("OFF_TOPIC")
        
        status = " | ".join(flags) if flags else "CLEAN"
        print(f"Comment {i+1}: {status}")

# Usage
async def main():
    client = RespectifyAsyncClient(email="...", api_key="...")
    
    topic = await client.init_topic_from_text("Programming discussion")
    
    comments = [
        "Excellent tutorial on Python!",
        "Check out my amazing deals at spam-site.com",
        "This article is about cooking, not programming",
        "Thanks for the clear explanation",
        "More examples would be helpful"
    ]
    
    await async_batch_megacall(client, comments, topic.article_id)

asyncio.run(main())
```

## Cost Optimization with Megacall

Using megacall is more cost-effective than individual API calls:

```python
# ❌ Less efficient: 4 separate API calls
spam_result = client.check_spam(comment, article_id)
relevance_result = client.check_relevance(comment, article_id)
score_result = client.evaluate_comment(comment, article_id)
dogwhistle_result = client.check_dogwhistle(comment)

# ✅ More efficient: 1 API call
megacall_result = client.megacall(
    comment=comment,
    article_id=article_id,
    include_spam=True,
    include_relevance=True,
    include_comment_score=True,
    include_dogwhistle=True
)

# Access the same data
spam_data = megacall_result.spam
relevance_data = megacall_result.relevance
score_data = megacall_result.comment_score
dogwhistle_data = megacall_result.dogwhistle
```

## Error Handling with Megacall

```python
from respectify import PaymentRequiredError, RespectifyError

def safe_megacall(client, comment, article_id):
    """Megacall with graceful error handling."""
    
    try:
        return client.megacall(
            comment=comment,
            article_id=article_id,
            include_spam=True,
            include_relevance=True,
            include_comment_score=True,
            include_dogwhistle=True
        )
    except PaymentRequiredError as e:
        print(f"Some features not available: {e.message}")
        # Try with basic features only
        try:
            return client.megacall(
                comment=comment,
                article_id=article_id,
                include_spam=True,
                include_comment_score=True
            )
        except RespectifyError as e2:
            print(f"Basic megacall also failed: {e2.message}")
            return None
    except RespectifyError as e:
        print(f"Megacall failed: {e.message}")
        return None

# Usage
result = safe_megacall(client, "Test comment", article_id)
if result:
    print("Analysis completed successfully")
else:
    print("Analysis failed, check error messages above")
```