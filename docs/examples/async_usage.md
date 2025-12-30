# Asynchronous Usage Examples

This page demonstrates asynchronous usage patterns with the Respectify Python client.

## Setting Up the Async Client

```python
import asyncio
from respectify import RespectifyAsyncClient

async def main():
    # Initialize the async client
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key",
        base_url="https://app.respectify.ai",  # Optional
        timeout=30.0  # Optional
    )
```

## Sequential Operations

```python
async def sequential_analysis():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    # Initialize topic
    topic = await client.init_topic_from_text("Article content here")
    article_id = topic.article_id
    
    # Analyze comments sequentially
    comment = "This is a test comment"
    
    spam_result = await client.check_spam(comment, article_id)
    print(f"Spam check: {spam_result.is_spam}")
    
    score_result = await client.evaluate_comment(comment, article_id)
    print(f"Quality score: {score_result.overall_score}/5")
    
    relevance_result = await client.check_relevance(comment, article_id)
    print(f"On topic: {relevance_result.on_topic.is_on_topic}")

asyncio.run(sequential_analysis())
```

## Concurrent Operations

The real power of the async client comes from running multiple operations concurrently:

```python
async def concurrent_analysis():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    # Initialize topic
    topic = await client.init_topic_from_text("Article content here")
    article_id = topic.article_id
    
    comment = "This is a test comment for concurrent analysis"
    
    # Run multiple analyses concurrently
    spam_task = client.check_spam(comment, article_id)
    score_task = client.evaluate_comment(comment, article_id)
    relevance_task = client.check_relevance(comment, article_id)
    dogwhistle_task = client.check_dogwhistle(comment)
    
    # Wait for all tasks to complete
    spam_result, score_result, relevance_result, dogwhistle_result = await asyncio.gather(
        spam_task, score_task, relevance_task, dogwhistle_task
    )
    
    print(f"Spam: {spam_result.is_spam}")
    print(f"Score: {score_result.overall_score}/5")
    print(f"Toxicity: {score_result.toxicity_score:.2f}")
    print(f"On topic: {relevance_result.on_topic.is_on_topic}")
    print(f"Dogwhistles: {dogwhistle_result.detection.dogwhistles_detected}")

asyncio.run(concurrent_analysis())
```

## Batch Processing Multiple Comments

```python
async def batch_process_comments():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    # Initialize topic
    topic = await client.init_topic_from_text("Article about Python programming")
    article_id = topic.article_id
    
    comments = [
        "Great article about Python!",
        "This is spam with links to buy stuff",
        "Python is terrible, use JavaScript instead",
        "Thanks for the detailed explanation of async/await",
        "First comment!"
    ]
    
    # Process all comments concurrently
    tasks = [
        client.megacall(
            comment=comment,
            article_id=article_id,
            include_spam=True,
            include_comment_score=True,
            include_relevance=True
        )
        for comment in comments
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Process results
    for i, result in enumerate(results):
        comment = comments[i]
        print(f"\nComment {i+1}: '{comment[:50]}...'")
        print(f"  Spam: {result.spam.is_spam} (confidence: {result.spam.confidence:.2f})")
        print(f"  Quality: {result.comment_score.overall_score}/5")
        print(f"  Toxicity: {result.comment_score.toxicity_score:.2f}")
        print(f"  Relevant: {result.relevance.on_topic.is_on_topic}")

asyncio.run(batch_process_comments())
```

## Context Manager Pattern

```python
async def using_context_manager():
    """Example using async context manager pattern (if implemented)."""
    
    # Note: This is a conceptual example - the current client doesn't implement
    # async context manager, but it could be added for resource management
    
    async with RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    ) as client:
        topic = await client.init_topic_from_text("Article content")
        result = await client.check_spam("Test comment", topic.article_id)
        print(f"Result: {result.is_spam}")
```

## Error Handling in Async Code

```python
from respectify import AuthenticationError, BadRequestError, RespectifyError

async def async_error_handling():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    try:
        # This will fail with bad request
        result = await client.check_spam("", article_id)
    except BadRequestError as e:
        print(f"Bad request: {e.message}")
    except AuthenticationError as e:
        print(f"Auth error: {e.message}")
    except RespectifyError as e:
        print(f"API error: {e.message}")

asyncio.run(async_error_handling())
```

## Using asyncio.as_completed for Progressive Results

```python
async def progressive_results():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    topic = await client.init_topic_from_text("Programming tutorial")
    article_id = topic.article_id
    
    comments = [
        "Excellent tutorial!",
        "Could use more examples",
        "This helped me understand async programming",
        "More beginner-friendly content please"
    ]
    
    # Create tasks
    tasks = [
        client.evaluate_comment(comment, article_id)
        for comment in comments
    ]
    
    # Process results as they complete
    for i, coro in enumerate(asyncio.as_completed(tasks)):
        result = await coro
        print(f"Completed analysis {i+1}: Quality score {result.overall_score}/5")

asyncio.run(progressive_results())
```

## Rate Limiting with Semaphores

```python
async def rate_limited_processing():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    # Limit concurrent requests to avoid overwhelming the API
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
    
    async def process_comment(comment, article_id):
        async with semaphore:
            return await client.check_spam(comment, article_id)
    
    topic = await client.init_topic_from_text("Rate limiting example")
    article_id = topic.article_id
    
    # Process many comments with rate limiting
    comments = [f"Test comment {i}" for i in range(20)]
    
    tasks = [
        process_comment(comment, article_id)
        for comment in comments
    ]
    
    results = await asyncio.gather(*tasks)
    
    spam_count = sum(1 for result in results if result.is_spam)
    print(f"Processed {len(results)} comments, {spam_count} flagged as spam")

asyncio.run(rate_limited_processing())
```