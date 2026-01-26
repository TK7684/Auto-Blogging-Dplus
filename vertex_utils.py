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

    def __init__(self, requests_per_minute=5, requests_per_day=1500):
        """
        Initialize rate limiter with more conservative defaults.

        Note: Vertex AI has a limit of ~60 requests/minute for gemini-experimental base model.
        We use 5 requests/minute to stay well under the limit and allow for bursts.

        Args:
            requests_per_minute: Maximum requests per minute (default: 5, conservative)
            requests_per_day: Maximum requests per day (default: 1500, reduced from 2500)
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
        # Conservative limits to avoid 429 errors for gemini-experimental base model
        _rate_limiter = VertexRateLimiter(
            requests_per_minute=5,
            requests_per_day=1500
        )
    return _rate_limiter


def call_vertex_with_retry(model: GenerativeModel, prompt: str, max_retries: int = 3,
                          generation_config: Optional[GenerationConfig] = None) -> Optional[Any]:
    """
    Calls Vertex AI API with rate limiting, exponential backoff, and regional fallbacks.
    """
    rate_limiter = get_rate_limiter()
    # Extract base model name from full resource path (e.g., "publishers/google/models/gemini-2.0-flash-exp" -> "gemini-2.0-flash-exp")
    initial_model_name = model._model_name
    if "/" in initial_model_name:
        initial_model_name = initial_model_name.split("/")[-1]
    
    # Check Cache first
    if not str(prompt).strip():
        return None
    cached_response = cache.get(str(prompt), initial_model_name)
    if cached_response:
        print(f"Vertex AI: Cache HIT for {initial_model_name}")
        class MockResponse:
            def __init__(self, text): self.text = text
        return MockResponse(cached_response["response"])

    # Daily usage check with buffer
    daily_usage = rate_limiter.get_daily_usage()
    if daily_usage >= (rate_limiter.requests_per_day * 0.95):  # Stop at 95% to leave buffer
        print("XXX CIRCUIT BREAKER TRIPPED: Daily Quota Limit Reached. XXX")
        return None

    # Fallback lists - Updated with currently available models (as of 2025)
    # Note: Model IDs must match exactly what's available in your Vertex AI project/region
    models_to_try = [initial_model_name]
    if "flash" in initial_model_name or "2.0" in initial_model_name:
        # Updated list with models known to work in Vertex AI
        models_to_try.extend([
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-thinking-exp",
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-001",
            "gemini-1.5-pro-002",
            "gemini-1.5-pro-001"
        ])
    elif "pro" in initial_model_name:
        models_to_try.extend(["gemini-1.5-pro-002", "gemini-1.5-pro-001", "gemini-2.0-flash-exp"])
    
    # Remove duplicates but keep order
    models_to_try = list(dict.fromkeys(models_to_try))
    
    regions_to_try = ["us-central1", "us-east1", "europe-west1", "asia-southeast1"]
    current_region = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if current_region in regions_to_try:
        regions_to_try.remove(current_region)
    regions_to_try.insert(0, current_region)

    for region in regions_to_try:
        print(f"Vertex AI: Attempting calls in region {region}...")
        try:
            vertexai_init(
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=region
            )
        except Exception as e:
            print(f"Vertex AI: Initialization failed for {region}: {e}")
            continue

        for m_name in models_to_try:
            # Re-create model for each name/region
            try:
                # Re-check tools availability
                tools = None
                if GOOGLE_SEARCH_AVAILABLE:
                    try:
                        google_search = GoogleSearchRetrievalTool()
                        tools = [Tool(google_search_retrieval=google_search)]
                    except: pass
                
                temp_model = GenerativeModel(m_name, tools=tools)
            except Exception as e:
                print(f"Vertex AI: Could not create model {m_name} in {region}: {e}")
                continue

            print(f"Vertex AI: Trying {m_name} (Usage: {rate_limiter.get_daily_usage()}/{rate_limiter.requests_per_day})")
            
            # Acquire rate limit permission
            if not rate_limiter.acquire(timeout=30):
                continue

            def do_call():
                if generation_config:
                    return temp_model.generate_content(prompt, generation_config=generation_config)
                return temp_model.generate_content(prompt)

            try:
                # Manual retry logic for standard transient errors
                for attempt in range(max_retries):
                    try:
                        response = do_call()
                        if response and hasattr(response, 'text') and response.text:
                            cache.set(str(prompt), m_name, response.text)
                            return response
                        break # Success but empty? stop
                    except (exceptions.ServiceUnavailable, exceptions.InternalServerError, exceptions.GoogleAPIError) as transient_e:
                        wait = 2 ** attempt
                        print(f"Vertex AI: Transient error, retrying in {wait}s... ({transient_e})")
                        time.sleep(wait)
                    except exceptions.ResourceExhausted:
                        print(f"Vertex AI: 429 Resource Exhausted for {m_name}")
                        break # Try next model
                    except exceptions.NotFound as e:
                        print(f"Vertex AI: 404 Not Found for {m_name} in {region}")
                        break # Try next model
            except Exception as e:
                print(f"Vertex AI: Unexpected error for {m_name}: {e}")
                continue

    print("Vertex AI: All regions and models failed.")
    return None


def create_vertex_model(model_name: str = "gemini-2.0-flash-exp",
                       project: Optional[str] = None,
                       location: str = "us-central1",
                       use_search_tool: bool = False) -> GenerativeModel:
    """
    Creates a Vertex AI GenerativeModel instance with the specified configuration.
    Note: call_vertex_with_retry will handle re-init if needed.
    """
    load_dotenv()
    vertexai_init(
        project=project or os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    tools = None
    if use_search_tool and GOOGLE_SEARCH_AVAILABLE:
        google_search = GoogleSearchRetrievalTool()
        tools = [Tool(google_search_retrieval=google_search)]
    return GenerativeModel(model_name, tools=tools)


def get_model_name_from_env(fallback: str = "gemini-2.0-flash-exp") -> str:
    """Gets the model name from environment variable with fallback."""
    load_dotenv()
    return os.getenv("VERTEX_MODEL_NAME", fallback)

