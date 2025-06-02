"""Test circuit breaker pattern for Claude API resilience."""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import subprocess

from src.analysis.claude_analyzer import ClaudeAnalyzer, CircuitBreakerError, CircuitState


class TestCircuitBreakerPattern:
    """Test circuit breaker implementation for Claude API failures."""
    
    @pytest.fixture
    def analyzer(self):
        """Create Claude analyzer with circuit breaker."""
        analyzer = ClaudeAnalyzer(
            circuit_breaker_enabled=True,
            failure_threshold=3,
            recovery_timeout=60,  # 1 minute for testing
            half_open_max_calls=2
        )
        return analyzer
    
    def test_circuit_breaker_initialization(self, analyzer):
        """Test that circuit breaker initializes in closed state."""
        assert analyzer.circuit_state == CircuitState.CLOSED
        assert analyzer.failure_count == 0
        assert analyzer.last_failure_time is None
        assert analyzer.half_open_calls == 0
    
    def test_circuit_remains_closed_on_success(self, analyzer):
        """Test circuit stays closed when Claude calls succeed."""
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "test"}]}'
            
            # Multiple successful calls
            for _ in range(5):
                result = analyzer.analyze_problems("test content")
                assert result is not None
                
            # Circuit should remain closed
            assert analyzer.circuit_state == CircuitState.CLOSED
            assert analyzer.failure_count == 0
    
    def test_circuit_opens_after_failure_threshold(self, analyzer):
        """Test circuit opens after reaching failure threshold."""
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            # Simulate subprocess failures
            mock_claude.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            # Make calls up to failure threshold
            for i in range(analyzer.failure_threshold):
                try:
                    analyzer.analyze_problems("test content")
                except CircuitBreakerError:
                    pass
                
                # Circuit should still be closed until threshold reached
                if i < analyzer.failure_threshold - 1:
                    assert analyzer.circuit_state == CircuitState.CLOSED
                    
            # After threshold, circuit should be open
            assert analyzer.circuit_state == CircuitState.OPEN
            assert analyzer.failure_count == analyzer.failure_threshold
    
    def test_circuit_blocks_calls_when_open(self, analyzer):
        """Test that circuit breaker blocks calls when open."""
        # Force circuit to open state
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.failure_count = analyzer.failure_threshold
        analyzer.last_failure_time = datetime.now()
        
        # Attempt to make call
        with pytest.raises(CircuitBreakerError) as exc_info:
            analyzer.analyze_problems("test content")
            
        assert "Circuit breaker is open" in str(exc_info.value)
        assert "Claude API is temporarily unavailable" in str(exc_info.value)
    
    def test_circuit_transitions_to_half_open(self, analyzer):
        """Test circuit transitions to half-open after recovery timeout."""
        # Force circuit to open state in the past
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.failure_count = analyzer.failure_threshold
        analyzer.last_failure_time = datetime.now() - timedelta(seconds=analyzer.recovery_timeout + 1)
        
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "test"}]}'
            
            # Make a call - should transition to half-open and succeed
            result = analyzer.analyze_problems("test content")
            assert result is not None
            assert analyzer.circuit_state == CircuitState.HALF_OPEN
            assert analyzer.half_open_calls == 1
    
    def test_half_open_returns_to_closed_on_success(self, analyzer):
        """Test half-open circuit returns to closed after successful calls."""
        # Set circuit to half-open
        analyzer.circuit_state = CircuitState.HALF_OPEN
        analyzer.half_open_calls = 0
        
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "test"}]}'
            
            # Make successful calls up to half-open limit
            for i in range(analyzer.half_open_max_calls):
                result = analyzer.analyze_problems("test content")
                assert result is not None
                
            # Circuit should return to closed
            assert analyzer.circuit_state == CircuitState.CLOSED
            assert analyzer.failure_count == 0
            assert analyzer.half_open_calls == 0
    
    def test_half_open_returns_to_open_on_failure(self, analyzer):
        """Test half-open circuit returns to open on failure."""
        # Set circuit to half-open
        analyzer.circuit_state = CircuitState.HALF_OPEN
        analyzer.half_open_calls = 0
        
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            # Make a failing call
            with pytest.raises(CircuitBreakerError):
                analyzer.analyze_problems("test content")
                
            # Circuit should return to open
            assert analyzer.circuit_state == CircuitState.OPEN
            assert analyzer.failure_count == 1
            assert analyzer.last_failure_time is not None
    
    def test_exponential_backoff_timing(self, analyzer):
        """Test exponential backoff increases recovery timeout."""
        initial_timeout = analyzer.recovery_timeout
        
        # Simulate multiple circuit opening cycles
        for cycle in range(1, 4):
            analyzer._calculate_backoff_timeout()
            expected_timeout = initial_timeout * (2 ** (cycle - 1))
            expected_timeout = min(expected_timeout, analyzer.max_recovery_timeout)
            
            assert analyzer.recovery_timeout == expected_timeout
    
    def test_circuit_breaker_metrics_tracking(self, analyzer):
        """Test that circuit breaker tracks metrics for monitoring."""
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            # Simulate mixed success/failure pattern
            mock_claude.side_effect = [
                Mock(returncode=0, stdout='{"problems": []}'),  # success
                subprocess.CalledProcessError(1, 'claude'),     # failure
                Mock(returncode=0, stdout='{"problems": []}'),  # success
                subprocess.CalledProcessError(1, 'claude'),     # failure
            ]
            
            for _ in range(4):
                try:
                    analyzer.analyze_problems("test")
                except CircuitBreakerError:
                    pass
                    
            metrics = analyzer.get_circuit_metrics()
            assert metrics['total_calls'] == 4
            assert metrics['failed_calls'] == 2
            assert metrics['success_rate'] == 0.5
            assert 'current_state' in metrics
            assert 'last_failure_time' in metrics
    
    def test_cached_responses_during_outage(self, analyzer):
        """Test that cached responses are used when circuit is open."""
        # Prime cache with successful response
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "cached problem"}]}'
            
            # Make initial successful call to cache response
            result1 = analyzer.analyze_problems("test content")
            assert result1 is not None
            
        # Force circuit to open
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.last_failure_time = datetime.now()
        
        # Attempt same call - should return cached response
        result2 = analyzer.analyze_problems("test content")
        assert result2 is not None
        assert result2 == result1  # Should be identical cached response
    
    def test_graceful_degradation_messaging(self, analyzer):
        """Test ADHD-friendly error messages during outages."""
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.last_failure_time = datetime.now()
        
        try:
            analyzer.analyze_problems("test content")
        except CircuitBreakerError as e:
            error_msg = str(e)
            
            # Should have ADHD-friendly messaging
            assert "don't worry" in error_msg.lower() or "it's okay" in error_msg.lower()
            assert "temporary" in error_msg.lower()
            assert "continue" in error_msg.lower() or "manual" in error_msg.lower()
            # Should not contain technical jargon
            assert "circuit breaker" not in error_msg.lower()
            assert "subprocess" not in error_msg.lower()
    
    def test_manual_fallback_during_outage(self, analyzer):
        """Test manual problem entry fallback when Claude is unavailable."""
        analyzer.circuit_state = CircuitState.OPEN
        
        # Should provide fallback analysis
        fallback_result = analyzer.get_fallback_analysis("Complex math problem")
        
        assert fallback_result is not None
        assert 'problems' in fallback_result
        assert 'manual_entry' in fallback_result
        assert fallback_result['manual_entry'] is True
        
        # Should provide basic problem structure
        problem = fallback_result['problems'][0]
        assert 'original_text' in problem
        assert 'steps' in problem
        assert len(problem['steps']) >= 1  # At least one step
    
    def test_circuit_recovery_notification(self, analyzer):
        """Test notification when circuit breaker recovers."""
        # Simulate circuit opening and then recovering
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.last_failure_time = datetime.now() - timedelta(seconds=analyzer.recovery_timeout + 1)
        
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "test"}]}'
            
            # Mock the recovery notification
            with patch.object(analyzer, '_notify_recovery') as mock_notify:
                # Make successful call after recovery
                for _ in range(analyzer.half_open_max_calls):
                    analyzer.analyze_problems("test content")
                    
                # Should notify recovery when circuit closes
                mock_notify.assert_called_once()
    
    def test_timeout_handling_separate_from_failures(self, analyzer):
        """Test that timeouts are handled separately from API failures."""
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            # Simulate timeout
            mock_claude.side_effect = subprocess.TimeoutExpired('claude', timeout=30)
            
            try:
                analyzer.analyze_problems("test content", timeout=5)
            except CircuitBreakerError:
                pass
                
            # Timeout should not count toward circuit breaker failure threshold
            # (or count differently than API errors)
            assert analyzer.failure_count <= 1  # Timeout might count as 1, not same as API error
    
    def test_circuit_state_persistence(self, analyzer):
        """Test that circuit state can be persisted across restarts."""
        # Set circuit to open state
        analyzer.circuit_state = CircuitState.OPEN
        analyzer.failure_count = 5
        analyzer.last_failure_time = datetime.now()
        
        # Save state
        state = analyzer.save_circuit_state()
        assert state is not None
        
        # Create new analyzer and restore state
        new_analyzer = ClaudeAnalyzer()
        new_analyzer.restore_circuit_state(state)
        
        assert new_analyzer.circuit_state == CircuitState.OPEN
        assert new_analyzer.failure_count == 5
        assert new_analyzer.last_failure_time is not None
    
    def test_health_check_functionality(self, analyzer):
        """Test periodic health checks to verify Claude availability."""
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            # Simulate health check success
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = 'OK'
            
            health_status = analyzer.perform_health_check()
            assert health_status is True
            
            # Simulate health check failure
            mock_claude.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            health_status = analyzer.perform_health_check()
            assert health_status is False
    
    def test_circuit_breaker_configuration(self, analyzer):
        """Test that circuit breaker can be configured and disabled."""
        # Test with circuit breaker disabled
        analyzer_disabled = ClaudeAnalyzer(circuit_breaker_enabled=False)
        
        with patch.object(analyzer_disabled, '_run_claude_cli') as mock_claude:
            mock_claude.side_effect = subprocess.CalledProcessError(1, 'claude')
            
            # Should raise original exception, not circuit breaker error
            with pytest.raises(subprocess.CalledProcessError):
                analyzer_disabled.analyze_problems("test content")
                
        # Circuit breaker should not be engaged
        assert analyzer_disabled.circuit_state == CircuitState.CLOSED
    
    def test_integration_with_existing_cache(self, analyzer):
        """Test circuit breaker works with existing LRU cache."""
        # This test ensures circuit breaker doesn't interfere with cache
        with patch.object(analyzer, '_run_claude_cli') as mock_claude:
            mock_claude.return_value.returncode = 0
            mock_claude.return_value.stdout = '{"problems": [{"text": "test"}]}'
            
            # Make call to populate cache
            result1 = analyzer.analyze_problems("test content")
            
            # Make same call - should hit cache, not Claude
            result2 = analyzer.analyze_problems("test content")
            
            # Should be identical results
            assert result1 == result2
            
            # Claude should only be called once (cache hit on second call)
            assert mock_claude.call_count == 1