"""
AI service abstraction layer.

Provides unified interface for multiple AI providers:
- OpenAI
- Anthropic
- Local models
- Azure OpenAI

Per EMR Rules:
- All AI interactions are visit-scoped
- PHI sanitization before sending to AI
- Audit logging for all requests
- Rate limiting and cost tracking
"""
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import AIRequest, AIProvider, AIFeatureType, AIConfiguration, AICache


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class RateLimitExceeded(AIServiceError):
    """Raised when rate limit is exceeded."""
    pass


class AIServiceBase:
    """Base class for AI service providers."""
    
    def __init__(self, provider: AIProvider, model: str, api_key: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key or self._get_api_key()
    
    def _get_api_key(self) -> str:
        """Get API key from environment variables."""
        key_map = {
            AIProvider.OPENAI: 'OPENAI_API_KEY',
            AIProvider.ANTHROPIC: 'ANTHROPIC_API_KEY',
            AIProvider.AZURE_OPENAI: 'AZURE_OPENAI_API_KEY',
        }
        env_key = key_map.get(self.provider)
        if env_key:
            import os
            return os.environ.get(env_key, '')
        return ''
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate AI response. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement generate()")
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Calculate cost based on token usage. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement calculate_cost()")


class OpenAIService(AIServiceBase):
    """OpenAI service implementation (openai>=1.0 client API)."""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using OpenAI API."""
        try:
            from openai import OpenAI
            
            if not self.api_key:
                raise AIServiceError("OpenAI API key not configured")
            
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": kwargs.get('system_prompt', 'You are a helpful medical assistant.')},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get('max_tokens', 4000),
                temperature=kwargs.get('temperature', 0.7),
            )
            
            content = response.choices[0].message.content if response.choices else ""
            usage = getattr(response, 'usage', None)
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            
            return {
                'content': content or "",
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
            }
        except ImportError:
            raise AIServiceError("OpenAI library not installed. Install with: pip install openai")
        except Exception as e:
            raise AIServiceError(f"OpenAI API error: {str(e)}")
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Calculate cost based on OpenAI pricing."""
        # GPT-4 pricing (example, update based on actual pricing)
        pricing = {
            'gpt-4': {'prompt': Decimal('0.03'), 'completion': Decimal('0.06')},
            'gpt-4-turbo': {'prompt': Decimal('0.01'), 'completion': Decimal('0.03')},
            'gpt-3.5-turbo': {'prompt': Decimal('0.0015'), 'completion': Decimal('0.002')},
        }
        
        model_pricing = pricing.get(self.model, pricing['gpt-3.5-turbo'])
        cost = (
            (prompt_tokens / 1000) * model_pricing['prompt'] +
            (completion_tokens / 1000) * model_pricing['completion']
        )
        return cost


class AnthropicService(AIServiceBase):
    """Anthropic (Claude) service implementation."""
    
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Anthropic API."""
        try:
            import anthropic
            
            if not self.api_key:
                raise AIServiceError("Anthropic API key not configured")
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.model,
                max_tokens=kwargs.get('max_tokens', 4000),
                temperature=kwargs.get('temperature', 0.7),
                system=kwargs.get('system_prompt', 'You are a helpful medical assistant.'),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                'content': response.content[0].text,
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
            }
        except ImportError:
            raise AIServiceError("Anthropic library not installed. Install with: pip install anthropic")
        except Exception as e:
            raise AIServiceError(f"Anthropic API error: {str(e)}")
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """Calculate cost based on Anthropic pricing."""
        # Claude pricing (example, update based on actual pricing)
        pricing = {
            'claude-3-opus': {'prompt': Decimal('0.015'), 'completion': Decimal('0.075')},
            'claude-3-sonnet': {'prompt': Decimal('0.003'), 'completion': Decimal('0.015')},
            'claude-3-haiku': {'prompt': Decimal('0.00025'), 'completion': Decimal('0.00125')},
        }
        
        model_pricing = pricing.get(self.model, pricing['claude-3-sonnet'])
        cost = (
            (prompt_tokens / 1000) * model_pricing['prompt'] +
            (completion_tokens / 1000) * model_pricing['completion']
        )
        return cost


class AIServiceFactory:
    """Factory for creating AI service instances."""
    
    @staticmethod
    def create_service(provider: AIProvider, model: str, api_key: Optional[str] = None) -> AIServiceBase:
        """Create an AI service instance based on provider."""
        service_map = {
            AIProvider.OPENAI: OpenAIService,
            AIProvider.ANTHROPIC: AnthropicService,
            # Add more providers as needed
        }
        
        service_class = service_map.get(provider)
        if not service_class:
            raise AIServiceError(f"Unsupported provider: {provider}")
        
        return service_class(provider, model, api_key)


class AIServiceManager:
    """
    Main manager for AI services.
    
    Handles:
    - Provider selection
    - Rate limiting
    - Caching
    - Cost tracking
    - Audit logging
    """
    
    def __init__(self, visit, user, feature_type: AIFeatureType):
        self.visit = visit
        self.user = user
        self.feature_type = feature_type
        self.config = self._get_configuration()
    
    def _get_configuration(self) -> AIConfiguration:
        """Get configuration for the feature type."""
        config, _ = AIConfiguration.objects.get_or_create(
            feature_type=self.feature_type,
            defaults={
                'default_provider': AIProvider.OPENAI,
                'default_model': 'gpt-3.5-turbo',
                'enabled': True,
            }
        )
        return config
    
    def _check_rate_limit(self):
        """Check if user has exceeded rate limit."""
        cache_key = f"ai_rate_limit:{self.user.id}:{self.feature_type}"
        requests_count = cache.get(cache_key, 0)
        
        if requests_count >= self.config.rate_limit_per_minute:
            raise RateLimitExceeded(
                f"Rate limit exceeded. Maximum {self.config.rate_limit_per_minute} requests per minute."
            )
        
        cache.set(cache_key, requests_count + 1, 60)  # 60 seconds
    
    def _get_cached_response(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        try:
            cache_entry = AICache.objects.get(
                feature_type=self.feature_type,
                prompt_hash=prompt_hash,
                expires_at__gt=timezone.now()
            )
            cache_entry.hit_count += 1
            cache_entry.save(update_fields=['hit_count'])
            return cache_entry.response
        except AICache.DoesNotExist:
            return None
    
    def _cache_response(self, prompt: str, response: Dict[str, Any], ttl: int = 3600):
        """Cache AI response."""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        AICache.objects.update_or_create(
            feature_type=self.feature_type,
            prompt_hash=prompt_hash,
            defaults={
                'response': response,
                'expires_at': timezone.now() + timezone.timedelta(seconds=ttl),
            }
        )
    
    def _sanitize_phi(self, text: str) -> str:
        """
        Sanitize PHI (Protected Health Information) from text.
        
        This is a basic implementation. In production, use a proper PHI detection library.
        """
        # Basic PHI removal (replace with proper library in production)
        import re
        # Remove potential phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Remove potential SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        # Remove potential email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        return text
    
    def generate(
        self,
        prompt: str,
        use_cache: bool = True,
        cache_ttl: int = 3600,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate AI response with full tracking and logging.
        
        Args:
            prompt: The prompt to send to AI
            use_cache: Whether to use cached responses
            cache_ttl: Cache time-to-live in seconds
            **kwargs: Additional parameters for AI service
        
        Returns:
            Dict containing AI response and metadata
        """
        if not self.config.enabled:
            raise AIServiceError(f"AI feature {self.feature_type} is disabled")
        
        # Check rate limit
        self._check_rate_limit()
        
        # Sanitize PHI from prompt
        sanitized_prompt = self._sanitize_phi(prompt)
        
        # Check cache
        if use_cache:
            cached_response = self._get_cached_response(sanitized_prompt)
            if cached_response:
                return cached_response
        
        # Create AI service
        service = AIServiceFactory.create_service(
            provider=AIProvider(self.config.default_provider),
            model=self.config.default_model
        )
        
        # Generate response
        start_time = time.time()
        try:
            response = service.generate(
                sanitized_prompt,
                max_tokens=self.config.max_tokens,
                temperature=float(self.config.temperature),
                **kwargs
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost
            cost = service.calculate_cost(
                response['prompt_tokens'],
                response['completion_tokens']
            )
            
            # Log request
            ai_request = AIRequest.objects.create(
                visit=self.visit,
                user=self.user,
                user_role=getattr(self.user, 'role', 'UNKNOWN'),
                feature_type=self.feature_type,
                provider=self.config.default_provider,
                model=self.config.default_model,
                prompt_tokens=response['prompt_tokens'],
                completion_tokens=response['completion_tokens'],
                total_tokens=response['total_tokens'],
                cost_usd=cost,
                request_payload={'prompt_length': len(sanitized_prompt)},
                response_payload={'response_length': len(response['content'])},
                success=True,
                response_time_ms=response_time_ms,
                ip_address=None,  # Will be set by view
            )
            
            # Cache response
            if use_cache:
                self._cache_response(sanitized_prompt, response, cache_ttl)
            
            return {
                'content': response['content'],
                'request_id': ai_request.id,
                'tokens_used': response['total_tokens'],
                'cost_usd': float(cost),
                'cached': False,
            }
            
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log failed request
            AIRequest.objects.create(
                visit=self.visit,
                user=self.user,
                user_role=getattr(self.user, 'role', 'UNKNOWN'),
                feature_type=self.feature_type,
                provider=self.config.default_provider,
                model_name=self.config.default_model,
                success=False,
                error_message=str(e),
                response_time_ms=response_time_ms,
            )
            
            raise
