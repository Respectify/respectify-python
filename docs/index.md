# Respectify Python Client

A Python client library for the [Respectify API](https://respectify.ai), providing both synchronous and asynchronous interfaces for comment moderation, spam detection, toxicity analysis, and dogwhistle detection.

## Features

- **Dual Interface**: Both synchronous (`RespectifyClient`) and asynchronous (`RespectifyAsyncClient`) clients
- **Type Safety**: Full type hints with Pydantic schema validation  
- **Comprehensive Coverage**: All Respectify API endpoints supported
- **Error Handling**: Custom exception classes for different API error conditions
- **Modern Python**: Uses httpx for HTTP requests, beartype for runtime type checking

## Installation

```bash
pip install respectify
```

## Quick Start

### Synchronous Client

```python
from respectify import RespectifyClient

client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)

# Initialize a topic
topic = client.init_topic_from_text("This is my article content")
article_id = topic.article_id

# Check if a comment is spam
spam_result = client.check_spam("Great post!", article_id)
print(f"Is spam: {spam_result.is_spam}")

# Evaluate comment quality and toxicity
score = client.evaluate_comment("This is a thoughtful comment", article_id)
print(f"Overall score: {score.overall_score}/5")
print(f"Toxicity: {score.toxicity_score:.2f}")
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
    
    # Initialize a topic
    topic = await client.init_topic_from_text("This is my article content")
    article_id = topic.article_id
    
    # Run multiple checks concurrently
    spam_task = client.check_spam("Great post!", article_id)
    score_task = client.evaluate_comment("Thoughtful comment", article_id)
    
    spam_result, score_result = await asyncio.gather(spam_task, score_task)
    
    print(f"Is spam: {spam_result.is_spam}")
    print(f"Overall score: {score_result.overall_score}/5")

asyncio.run(main())
```

## API Reference

```{toctree}
:maxdepth: 2

api/clients
api/schemas
api/exceptions
```

## Examples

```{toctree}
:maxdepth: 1

examples/basic_usage
examples/async_usage
examples/error_handling
examples/megacall
```

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex` 
- {ref}`search`