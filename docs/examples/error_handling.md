# Error Handling Examples

The Respectify Python client provides specific exception classes for different types of API errors, making it easy to handle different error conditions appropriately.

## Exception Hierarchy

```
RespectifyError (base exception)
├── AuthenticationError (401)
├── BadRequestError (400)
├── PaymentRequiredError (402)
├── UnsupportedMediaTypeError (415)
└── ServerError (500+)
```

## Basic Error Handling

```python
from respectify import (
    RespectifyClient,
    RespectifyError,
    AuthenticationError,
    BadRequestError,
    PaymentRequiredError,
    ServerError
)

client = RespectifyClient(
    email="your-email@example.com",
    api_key="your-api-key"
)

try:
    result = client.check_spam("Test comment", article_id)
    print(f"Spam detected: {result.is_spam}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    print("Please check your email and API key")
except BadRequestError as e:
    print(f"Bad request: {e.message}")
    print("Please check your request parameters")
except PaymentRequiredError as e:
    print(f"Payment required: {e.message}")
    print("Your plan doesn't include access to this endpoint")
except ServerError as e:
    print(f"Server error: {e.message}")
    print("Please try again later")
except RespectifyError as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    if e.response_data:
        print(f"Response data: {e.response_data}")
```

## Specific Error Scenarios

### Authentication Errors

```python
def handle_auth_errors():
    # Wrong credentials
    wrong_client = RespectifyClient(
        email="wrong@example.com",
        api_key="invalid-key"
    )
    
    try:
        result = wrong_client.check_spam("Test", article_id)
    except AuthenticationError as e:
        print(f"Authentication failed: {e.message}")
        # Log the error, prompt user for correct credentials
        return None
    
    return result
```

### Bad Request Errors

```python
def handle_validation_errors(client, article_id):
    try:
        # Empty comment will cause BadRequestError
        result = client.check_spam("", article_id)
    except BadRequestError as e:
        print(f"Validation error: {e.message}")
        if e.response_data:
            # API might return detailed validation errors
            errors = e.response_data.get('errors', [])
            for error in errors:
                print(f"  - {error}")
        return None
    
    return result
```

### Payment Required Errors

```python
def handle_subscription_errors(client):
    try:
        result = client.check_dogwhistle("Test comment")
    except PaymentRequiredError as e:
        print(f"Subscription error: {e.message}")
        print("This endpoint requires a paid plan")
        # Redirect user to upgrade page or show pricing
        return None
    except RespectifyError as e:
        print(f"Other API error: {e.message}")
        return None
    
    return result
```

## Async Error Handling

```python
import asyncio
from respectify import RespectifyAsyncClient, RespectifyError

async def async_error_handling():
    client = RespectifyAsyncClient(
        email="your-email@example.com",
        api_key="your-api-key"
    )
    
    try:
        result = await client.check_spam("Test comment", article_id)
        return result
    except AuthenticationError as e:
        print(f"Async auth error: {e.message}")
        return None
    except RespectifyError as e:
        print(f"Async API error: {e.message}")
        return None

# Usage
result = asyncio.run(async_error_handling())
```

## Retry Logic with Exponential Backoff

```python
import time
import random
from respectify import RespectifyClient, ServerError, RespectifyError

def make_request_with_retry(client, max_retries=3):
    """Make a request with exponential backoff retry logic."""
    
    for attempt in range(max_retries + 1):
        try:
            return client.check_spam("Test comment", article_id)
        except ServerError as e:
            if attempt == max_retries:
                raise  # Re-raise on final attempt
            
            # Exponential backoff with jitter
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"Server error on attempt {attempt + 1}, retrying in {delay:.2f}s")
            time.sleep(delay)
        except RespectifyError as e:
            # Don't retry non-server errors
            raise

# Usage
client = RespectifyClient(email="...", api_key="...")
try:
    result = make_request_with_retry(client)
    print(f"Success: {result.is_spam}")
except RespectifyError as e:
    print(f"Failed after retries: {e.message}")
```

## Async Retry Logic

```python
import asyncio
import random
from respectify import RespectifyAsyncClient, ServerError, RespectifyError

async def async_request_with_retry(client, max_retries=3):
    """Async request with exponential backoff retry logic."""
    
    for attempt in range(max_retries + 1):
        try:
            return await client.check_spam("Test comment", article_id)
        except ServerError as e:
            if attempt == max_retries:
                raise
            
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"Server error on attempt {attempt + 1}, retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
        except RespectifyError as e:
            raise

# Usage
async def main():
    client = RespectifyAsyncClient(email="...", api_key="...")
    try:
        result = await async_request_with_retry(client)
        print(f"Success: {result.is_spam}")
    except RespectifyError as e:
        print(f"Failed after retries: {e.message}")

asyncio.run(main())
```

## Graceful Degradation

```python
from respectify import RespectifyClient, PaymentRequiredError, RespectifyError

class CommentModerator:
    def __init__(self, client):
        self.client = client
        self.features_available = {
            'spam': True,
            'quality': True,
            'relevance': True,
            'dogwhistle': True
        }
    
    def moderate_comment(self, comment, article_id):
        """Moderate a comment with graceful feature degradation."""
        results = {}
        
        # Try spam detection
        if self.features_available['spam']:
            try:
                results['spam'] = self.client.check_spam(comment, article_id)
            except PaymentRequiredError:
                print("Spam detection not available in your plan")
                self.features_available['spam'] = False
            except RespectifyError as e:
                print(f"Spam detection error: {e.message}")
        
        # Try quality scoring
        if self.features_available['quality']:
            try:
                results['quality'] = self.client.evaluate_comment(comment, article_id)
            except PaymentRequiredError:
                print("Quality scoring not available in your plan")
                self.features_available['quality'] = False
            except RespectifyError as e:
                print(f"Quality scoring error: {e.message}")
        
        # Try dogwhistle detection
        if self.features_available['dogwhistle']:
            try:
                results['dogwhistle'] = self.client.check_dogwhistle(comment)
            except PaymentRequiredError:
                print("Dogwhistle detection not available in your plan")
                self.features_available['dogwhistle'] = False
            except RespectifyError as e:
                print(f"Dogwhistle detection error: {e.message}")
        
        return results

# Usage
client = RespectifyClient(email="...", api_key="...")
moderator = CommentModerator(client)

results = moderator.moderate_comment("Test comment", article_id)
for feature, result in results.items():
    if result:
        print(f"{feature}: Available")
    else:
        print(f"{feature}: Not available")
```

## Logging Errors

```python
import logging
from respectify import RespectifyClient, RespectifyError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def moderate_with_logging(client, comment, article_id):
    """Moderate comment with comprehensive error logging."""
    try:
        result = client.check_spam(comment, article_id)
        logger.info(f"Successfully analyzed comment: spam={result.is_spam}")
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e.message}")
        logger.error("Please verify API credentials")
        raise
    except BadRequestError as e:
        logger.warning(f"Bad request: {e.message}")
        logger.warning(f"Comment: {comment[:100]}...")
        if e.response_data:
            logger.warning(f"API response: {e.response_data}")
        raise
    except PaymentRequiredError as e:
        logger.warning(f"Feature not available: {e.message}")
        return None  # Graceful degradation
    except ServerError as e:
        logger.error(f"Server error: {e.message}")
        logger.error(f"Status code: {e.status_code}")
        raise
    except RespectifyError as e:
        logger.error(f"Unexpected API error: {e.message}")
        logger.error(f"Status code: {e.status_code}")
        logger.error(f"Response: {e.response_data}")
        raise

# Usage
client = RespectifyClient(email="...", api_key="...")
try:
    result = moderate_with_logging(client, "Test comment", article_id)
    if result:
        print(f"Moderation complete: {result.is_spam}")
except RespectifyError:
    print("Moderation failed, check logs for details")
```