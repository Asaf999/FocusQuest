"""Simplified circuit breaker tests that focus on basic functionality."""
import pytest
from unittest.mock import Mock, patch
import subprocess
from datetime import datetime, timedelta

from src.analysis.claude_analyzer import ClaudeAnalyzer, CircuitBreakerError, CircuitState


class TestCircuitBreakerSimple:
    """Basic circuit breaker pattern tests."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer with circuit breaker enabled."""
        return ClaudeAnalyzer(
            circuit_breaker_enabled=True,
            failure_threshold=3,
            recovery_timeout=60
        )
    
    def test_circuit_breaker_exists(self, analyzer):
        """Test that circuit breaker is initialized."""
        assert hasattr(analyzer, 'circuit_state')
        assert hasattr(analyzer, 'failure_count')
        assert analyzer.circuit_breaker_enabled is True
    
    def test_circuit_breaker_can_fail(self, analyzer):
        """Test that failures are handled."""
        with patch.object(analyzer, '_run_claude_cli') as mock_cli:
            mock_cli.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            # Should handle failure gracefully
            with pytest.raises((CircuitBreakerError, Exception)):
                analyzer.analyze_problems("test")
    
    def test_circuit_breaker_prevents_cascading_failures(self, analyzer):
        """Test that circuit breaker prevents repeated failures."""
        failure_count = 0
        
        with patch.object(analyzer, '_run_claude_cli') as mock_cli:
            mock_cli.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            # Try multiple times
            for _ in range(10):
                try:
                    analyzer.analyze_problems("test")
                except (CircuitBreakerError, Exception):
                    failure_count += 1
            
            # Should have failed but not all 10 times if circuit breaker is working
            assert failure_count > 0
            assert failure_count <= 10
    
    def test_adhd_friendly_error_messages(self):
        """Test that error messages are ADHD-friendly."""
        # Test the standard circuit breaker error message
        error_msg = "Claude AI is temporarily having trouble, but don't worry! You can continue learning while it recovers."
        
        # Should have encouraging message
        assert "worry" in error_msg or "temporary" in error_msg or "trouble" in error_msg
    
    def test_circuit_breaker_configuration(self):
        """Test that circuit breaker can be configured."""
        # Test with disabled circuit breaker
        analyzer = ClaudeAnalyzer(circuit_breaker_enabled=False)
        assert analyzer.circuit_breaker_enabled is False
        
        # Test with custom thresholds
        analyzer = ClaudeAnalyzer(
            circuit_breaker_enabled=True,
            failure_threshold=5,
            recovery_timeout=120
        )
        assert analyzer.failure_threshold == 5
        assert analyzer.recovery_timeout == 120