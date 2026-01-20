"""
Vertex AI Utility Module for Auto-Blogging-DPLUS

This module replaces ai_utils.py to use Google Cloud Vertex AI instead of
the direct Gemini API. It provides rate limiting, caching, and retry logic
specifically for Vertex AI endpoints.
"""

import os
import time
import json
import threading
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from vertexai.generative_models import GenerativeModel, GenerationConfig
from vertexai import init as vertexai_init
from google.api_core import exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from cache_manager import CacheManager

# Try to import Google Search tool (may not be available in all regions/versions)
try:
    from vertexai.generative_models import Tool, GoogleSearchRetrievalTool
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    Tool = None
    GoogleSearchRetrievalTool = None

# Initialize cache
cache = CacheManager()


class VertexRateLimiter:
    """
    Thread-safe rate limiter for Vertex AI API calls.
    Implements token bucket algorithm and usage tracking.
    """

    def __init__(self, requests_per_minute=15, requests_per_day=1500):
        """
        Initialize rate limiter with conservative defaults.

        Args:
            requests_per_minute: Maximum requests per minute (default: 15)
            requests_per_day: Maximum requests per day (default: 2500)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_day = requests_per_day

        # Token bucket for rate limiting
        self.min_bucket = requests_per_minute
        self.min_bucket_last_refill = time.time()
        self.min_bucket_lock = threading.Lock()

        # Daily usage tracking
        self.daily_usage = 0
        self.daily_usage_date = datetime.now().date()
        self.daily_usage_lock = threading.Lock()

        # Usage log file
        self.usage_log_file = "vertex_usage.json"
        self._load_usage_log()

    def _load_usage_log(self):
        """Load usage statistics from file."""
        try:
            if os.path.exists(self.usage_log_file):
                with open(self.usage_log_file, 'r') as f:
                    data = json.load(f)
                    saved_date = datetime.fromisoformat(data.get('date', '2000-01-01')).date()
                    if saved_date == self.daily_usage_date:
                        self.daily_usage = data.get('count', 0)
        except Exception as e:
            print(f"VertexRateLimiter: Could not load usage log: {e}")

    def _save_usage_log(self):
        """Save usage statistics to file."""
        try:
            with open(self.usage_log_file, 'w') as f:
                json.dump({
                    'date': self.daily_usage_date.isoformat(),
                    'count': self.daily_usage
                }, f)
        except Exception as e:
            print(f"VertexRateLimiter: Could not save usage log: {e}")

    def _refill_minute_bucket(self):
        """Refill the minute bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.min_bucket_last_refill

        # Refill based on elapsed time (linear refill)
        refill_amount = int(elapsed * (self.requests_per_minute / 60.0))
        if refill_amount > 0:
            self.min_bucket = min(self.requests_per_minute, self.min_bucket + refill_amount)
            self.min_bucket_last_refill = now

    def _check_daily_limit(self):
        """Check if daily limit has been reached."""
        with self.daily_usage_lock:
            # Reset if it's a new day
            if datetime.now().date() != self.daily_usage_date:
                self.daily_usage = 0
                self.daily_usage_date = datetime.now().date()

            if self.daily_usage >= self.requests_per_day:
                print(f"VertexRateLimiter: Daily limit reached ({self.daily_usage}/{self.requests_per_day})")
                return False
            return True

    def _record_usage(self):
        """Record a single API usage."""
        with self.daily_usage_lock:
            if datetime.now().date() != self.daily_usage_date:
                self.daily_usage = 0
                self.daily_usage_date = datetime.now().date()

            self.daily_usage += 1
            self._save_usage_log()

    def get_daily_usage(self):
        """Get current daily usage."""
        with self.daily_usage_lock:
            if datetime.now().date() != self.daily_usage_date:
                return 0
            return self.daily_usage

    def acquire(self, timeout=300):
        """
        Acquire permission to make an API call.

        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)

        Returns:
            True if permission granted, False if timeout or limit exceeded
        """
        if not self._check_daily_limit():
            return False

        start_time = time.time()

        while True:
            with self.min_bucket_lock:
                self._refill_minute_bucket()

                if self.min_bucket >= 1:
                    self.min_bucket -= 1
                    self._record_usage()
                    return True

            # Check timeout
            if time.time() - start_time >= timeout:
                print(f"VertexRateLimiter: Timeout waiting for rate limit (timeout={timeout}s)")
                return False

            # Wait before retrying (exponential backoff up to 10 seconds)
            wait_time = min(10, 1 + (time.time() - start_time) * 0.5)
            time.sleep(wait_time)


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter():
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        # Conservative limits for Vertex AI
        _rate_limiter = VertexRateLimiter(
            requests_per_minute=10,
            requests_per_day=2500
        )
    return _rate_limiter


def call_vertex_with_retry(model: GenerativeModel, prompt: str, max_retries: int = 3,
                          generation_config: Optional[GenerationConfig] = None) -> Optional[Any]:
    """
    Calls Vertex AI API with rate limiting and exponential backoff.

    Args:
        model: Vertex AI GenerativeModel instance
        prompt: The prompt to send
        max_retries: Maximum number of retry attempts (default: 3)
        generation_config: Optional generation config

    Returns:
        Response object or None if all retries fail
    """
    rate_limiter = get_rate_limiter()

    # Extract model name from the model object
    model_name = model._model_name

    # 1. Check Cache
    if not str(prompt).strip():
        return None

    cached_response = cache.get(str(prompt), model_name)
    if cached_response:
        print(f"Vertex AI: Cache HIT for {model_name}")
        # Create a mock response object with text attribute
        class MockResponse:
            def __init__(self, text):
                self.text = text
        return MockResponse(cached_response["response"])

    # 2. Check daily usage
    daily_usage = rate_limiter.get_daily_usage()
    print(f"Vertex AI: Daily usage: {daily_usage}/{rate_limiter.requests_per_day}")

    # Circuit Breaker: Stop completely if limit reached
    if daily_usage >= rate_limiter.requests_per_day:
        print("XXX CIRCUIT BREAKER TRIPPED: Daily Quota Limit Reached. Stopping API calls. XXX")
        return None

    # 3. Acquire Permission
    if not rate_limiter.acquire(timeout=60):
        print("Vertex AI: Rate limit timeout - could not acquire permission")
        return None

    time.sleep(random.uniform(0.5, 1.5))

    import logging
    logger = logging.getLogger(__name__)

    def log_retry(retry_state):
        print(f"Vertex AI: Retrying in {retry_state.next_action.sleep} seconds... "
              f"(Attempt {retry_state.attempt_number})")

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((
            exceptions.ServiceUnavailable,
            exceptions.InternalServerError,
            exceptions.GoogleAPIError
        )),
        before_sleep=log_retry,
        reraise=True
    )
    def do_call():
        if generation_config:
            return model.generate_content(prompt, generation_config=generation_config)
        return model.generate_content(prompt)

    try:
        response = do_call()
        if response and hasattr(response, 'text') and response.text:
            cache.set(str(prompt), model_name, response.text)
        return response
    except exceptions.ResourceExhausted as e:
        print(f"Vertex AI: QUOTA EXCEEDED (429). Stopping immediately. {e}")
        # Force increment usage to max to trip circuit breaker for next calls
        with rate_limiter.daily_usage_lock:
            rate_limiter.daily_usage = rate_limiter.requests_per_day + 1
            rate_limiter._save_usage_log()
        return None
    except Exception as e:
        print(f"Vertex AI Error after final attempt: {e}")
        return None


def create_vertex_model(model_name: str = "gemini-1.5-flash",
                       project: Optional[str] = None,
                       location: str = "us-central1",
                       use_search_tool: bool = False) -> GenerativeModel:
    """
    Creates a Vertex AI GenerativeModel instance with the specified configuration.

    Args:
        model_name: The model name (e.g., "gemini-2.0-flash-exp", "gemini-1.5-flash")
        project: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        location: GCP region (default: "us-central1")
        use_search_tool: Whether to enable Google Search retrieval tool

    Returns:
        GenerativeModel instance
    """
    load_dotenv()

    # Initialize Vertex AI
    vertexai_init(
        project=project or os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )

    # Configure tools if search is enabled and available
    tools = None
    if use_search_tool:
        if not GOOGLE_SEARCH_AVAILABLE:
            print("WARNING: Google Search tool not available in this Vertex AI SDK version. "
                  "Proceeding without search tool.")
        else:
            google_search = GoogleSearchRetrievalTool()
            tools = [Tool(google_search_retrieval=google_search)]

    return GenerativeModel(model_name, tools=tools)


def get_model_name_from_env(fallback: str = "gemini-1.5-flash") -> str:
    """
    Gets the model name from environment variable with fallback.

    Args:
        fallback: Default model name if env var not set

    Returns:
        Model name string
    """
    load_dotenv()
    return os.getenv("VERTEX_MODEL_NAME", fallback)
