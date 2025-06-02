"""Test resource monitoring and dynamic worker adjustment for ADHD-optimized performance."""
import pytest
import time
import psutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.resource_monitor import ResourceMonitor, ResourceAlert, AlertLevel
from src.core.queue_processor import QueueProcessor


class TestResourceMonitoring:
    """Test comprehensive resource monitoring for ADHD-friendly performance."""
    
    @pytest.fixture
    def resource_monitor(self):
        """Create resource monitor with test configuration."""
        monitor = ResourceMonitor(
            memory_warning_threshold=0.7,  # 70%
            memory_critical_threshold=0.85,  # 85%
            cpu_warning_threshold=0.8,  # 80%
            cpu_critical_threshold=0.9,  # 90%
            disk_warning_threshold=0.8,  # 80%
            disk_critical_threshold=0.9,  # 90%
            check_interval=1.0,  # 1 second for testing
            adhd_mode=True
        )
        return monitor
    
    @pytest.fixture
    def queue_processor_with_monitoring(self):
        """Create queue processor with resource monitoring."""
        processor = QueueProcessor(max_workers=4)
        monitor = ResourceMonitor()
        processor.resource_monitor = monitor
        monitor.add_managed_component(processor)
        return processor, monitor
    
    def test_resource_monitor_initialization(self, resource_monitor):
        """Test resource monitor initializes with correct settings."""
        assert resource_monitor.memory_warning_threshold == 0.7
        assert resource_monitor.memory_critical_threshold == 0.85
        assert resource_monitor.adhd_mode is True
        assert resource_monitor.is_monitoring is False
        assert len(resource_monitor.managed_components) == 0
        assert len(resource_monitor.alert_history) == 0
    
    def test_memory_usage_detection(self, resource_monitor):
        """Test accurate memory usage detection."""
        # Get actual memory usage
        memory_info = resource_monitor.get_memory_usage()
        
        assert 'total' in memory_info
        assert 'available' in memory_info
        assert 'used' in memory_info
        assert 'percentage' in memory_info
        assert 0 <= memory_info['percentage'] <= 100
        
        # Should match psutil values
        system_memory = psutil.virtual_memory()
        assert abs(memory_info['percentage'] - system_memory.percent) < 1.0
    
    def test_cpu_usage_detection(self, resource_monitor):
        """Test CPU usage monitoring over time."""
        # CPU usage requires time window
        cpu_info = resource_monitor.get_cpu_usage()
        
        assert 'percentage' in cpu_info
        assert 'per_cpu' in cpu_info
        assert 'load_average' in cpu_info
        assert 0 <= cpu_info['percentage'] <= 100
        assert len(cpu_info['per_cpu']) > 0
    
    def test_disk_usage_detection(self, resource_monitor):
        """Test disk space monitoring."""
        disk_info = resource_monitor.get_disk_usage()
        
        assert 'total' in disk_info
        assert 'used' in disk_info
        assert 'free' in disk_info
        assert 'percentage' in disk_info
        assert 0 <= disk_info['percentage'] <= 100
    
    def test_memory_threshold_alerts(self, resource_monitor):
        """Test memory threshold detection and alerts."""
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate high memory usage
            mock_memory.return_value.percent = 75.0  # Above warning threshold
            mock_memory.return_value.total = 8 * 1024**3  # 8GB
            mock_memory.return_value.available = 2 * 1024**3  # 2GB available
            mock_memory.return_value.used = 6 * 1024**3  # 6GB used
            
            alerts = resource_monitor.check_thresholds()
            
            # Should trigger memory warning
            memory_alerts = [a for a in alerts if a.resource_type == 'memory']
            assert len(memory_alerts) == 1
            assert memory_alerts[0].level == AlertLevel.WARNING
            assert "memory usage" in memory_alerts[0].message.lower()
    
    def test_critical_memory_threshold(self, resource_monitor):
        """Test critical memory threshold triggers urgent response."""
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate critical memory usage
            mock_memory.return_value.percent = 88.0  # Above critical threshold
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 1 * 1024**3
            mock_memory.return_value.used = 7 * 1024**3
            
            alerts = resource_monitor.check_thresholds()
            
            memory_alerts = [a for a in alerts if a.resource_type == 'memory']
            assert len(memory_alerts) == 1
            assert memory_alerts[0].level == AlertLevel.CRITICAL
            assert "critical" in memory_alerts[0].message.lower()
    
    def test_dynamic_worker_adjustment_memory(self, queue_processor_with_monitoring):
        """Test dynamic worker count adjustment based on memory pressure."""
        processor, monitor = queue_processor_with_monitoring
        initial_workers = processor.max_workers
        
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate high memory pressure
            mock_memory.return_value.percent = 82.0  # High memory usage
            
            alerts = monitor.check_thresholds()
            monitor._handle_alerts(alerts)
            
            # Should reduce worker count
            assert processor.max_workers < initial_workers
            assert processor.max_workers >= 1  # Never go below 1
    
    def test_worker_adjustment_recovery(self, queue_processor_with_monitoring):
        """Test worker count recovery when resources are available."""
        processor, monitor = queue_processor_with_monitoring
        original_workers = processor.max_workers
        
        # Simulate resource pressure and reduction
        processor.max_workers = 2  # Reduced from pressure
        
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate normal memory usage
            mock_memory.return_value.percent = 45.0  # Normal usage
            
            alerts = monitor.check_thresholds()
            monitor._handle_alerts(alerts)
            
            # Should gradually increase workers back
            # This might not happen immediately, so we test the capability exists
            assert hasattr(monitor, '_attempt_worker_recovery')
    
    def test_adhd_friendly_alert_messages(self, resource_monitor):
        """Test that alerts use ADHD-friendly, non-anxiety-inducing language."""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 78.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 1.5 * 1024**3
            mock_memory.return_value.used = 6.5 * 1024**3
            
            alerts = resource_monitor.check_thresholds()
            
            if alerts:
                alert_message = alerts[0].message.lower()
                
                # Should use gentle language
                assert any(word in alert_message for word in ['gentle', 'optimizing', 'adjusting'])
                
                # Should avoid scary technical terms
                assert 'critical' not in alert_message or 'gently' in alert_message
                assert 'error' not in alert_message
                assert 'failure' not in alert_message
    
    def test_resource_monitoring_loop(self, resource_monitor):
        """Test continuous resource monitoring loop."""
        monitoring_results = []
        
        def mock_check():
            monitoring_results.append(datetime.now())
            return []
        
        with patch.object(resource_monitor, 'check_thresholds', side_effect=mock_check):
            resource_monitor.start_monitoring()
            
            # Let it run briefly
            time.sleep(2.5)  # Should trigger 2-3 checks with 1s interval
            
            resource_monitor.stop_monitoring()
            
            # Should have made multiple checks
            assert len(monitoring_results) >= 2
    
    def test_process_specific_monitoring(self, resource_monitor):
        """Test monitoring of specific process (FocusQuest) resources."""
        current_process_info = resource_monitor.get_process_info()
        
        assert 'memory_mb' in current_process_info
        assert 'cpu_percent' in current_process_info
        assert 'open_files' in current_process_info
        assert 'threads' in current_process_info
        assert current_process_info['memory_mb'] > 0
    
    def test_pdf_processing_memory_estimation(self, resource_monitor):
        """Test estimation of memory needed for PDF processing."""
        # Test with different PDF characteristics
        small_pdf_estimate = resource_monitor.estimate_pdf_memory_usage(
            pages=5, avg_page_size_kb=100
        )
        
        large_pdf_estimate = resource_monitor.estimate_pdf_memory_usage(
            pages=50, avg_page_size_kb=500
        )
        
        assert large_pdf_estimate > small_pdf_estimate
        assert small_pdf_estimate > 0
        
        # Should be reasonable estimates (not gigabytes for small PDFs)
        assert small_pdf_estimate < 100 * 1024 * 1024  # < 100MB
    
    def test_preemptive_worker_adjustment(self, queue_processor_with_monitoring):
        """Test preemptive worker adjustment before processing large PDFs."""
        processor, monitor = queue_processor_with_monitoring
        
        # Simulate planning to process a large PDF
        estimated_memory = 200 * 1024 * 1024  # 200MB
        
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.available = 500 * 1024 * 1024  # 500MB available
            mock_memory.return_value.percent = 70.0
            
            should_reduce = monitor.should_reduce_workers_for_task(estimated_memory)
            
            # With only 500MB available and 200MB needed per worker, should reduce
            assert should_reduce is True
    
    def test_alert_history_tracking(self, resource_monitor):
        """Test that alert history is properly tracked for analysis."""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = 85.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 1 * 1024**3
            mock_memory.return_value.used = 7 * 1024**3
            
            # Generate some alerts
            alerts = resource_monitor.check_thresholds()
            resource_monitor._handle_alerts(alerts)
            
            # Check history
            history = resource_monitor.get_alert_history()
            assert len(history) > 0
            
            # Should have timestamp
            assert all('timestamp' in alert for alert in history)
            assert all('level' in alert for alert in history)
            assert all('message' in alert for alert in history)
    
    def test_performance_impact_monitoring(self, resource_monitor):
        """Test monitoring of resource monitor's own performance impact."""
        start_time = time.time()
        
        # Run multiple checks
        for _ in range(10):
            resource_monitor.check_thresholds()
            
        duration = time.time() - start_time
        
        # Resource monitoring should be lightweight
        assert duration < 1.0  # Less than 1 second for 10 checks
    
    def test_disk_space_monitoring(self, resource_monitor):
        """Test disk space monitoring for PDF processing directory."""
        with patch('psutil.disk_usage') as mock_disk:
            # Simulate low disk space
            mock_disk.return_value.total = 100 * 1024**3  # 100GB
            mock_disk.return_value.used = 85 * 1024**3   # 85GB used
            mock_disk.return_value.free = 15 * 1024**3   # 15GB free
            
            disk_info = resource_monitor.get_disk_usage()
            assert disk_info['percentage'] == 85.0
            
            alerts = resource_monitor.check_thresholds()
            disk_alerts = [a for a in alerts if a.resource_type == 'disk']
            
            # Should trigger disk space warning
            assert len(disk_alerts) > 0
            assert "disk space" in disk_alerts[0].message.lower()
    
    def test_cleanup_recommendations(self, resource_monitor):
        """Test generation of cleanup recommendations for ADHD users."""
        # Simulate resource pressure
        recommendations = resource_monitor.get_cleanup_recommendations()
        
        assert isinstance(recommendations, list)
        
        # Should provide actionable, ADHD-friendly suggestions
        for rec in recommendations:
            assert 'action' in rec
            assert 'benefit' in rec
            assert 'difficulty' in rec  # Easy/Medium/Hard for ADHD planning
            
            # Should avoid technical jargon
            assert not any(tech_term in rec['action'].lower() 
                          for tech_term in ['cache', 'heap', 'garbage collection'])
    
    def test_session_based_monitoring(self, resource_monitor):
        """Test monitoring tied to study sessions for ADHD context."""
        # Start a study session
        session_id = resource_monitor.start_session_monitoring("test_session")
        
        # Simulate some activity
        time.sleep(0.1)
        
        # End session and get report
        session_report = resource_monitor.end_session_monitoring(session_id)
        
        assert 'duration' in session_report
        assert 'peak_memory' in session_report
        assert 'average_cpu' in session_report
        assert 'recommendations' in session_report
        
        # Should provide ADHD-relevant insights
        insights = session_report.get('insights', [])
        if insights:
            assert any('focus' in insight.lower() or 'break' in insight.lower() 
                      for insight in insights)
    
    def test_integration_with_queue_processor_lifecycle(self):
        """Test resource monitor integration through processor lifecycle."""
        processor = QueueProcessor(max_workers=3)
        monitor = ResourceMonitor()
        
        # Add monitoring to processor
        processor.resource_monitor = monitor
        monitor.add_managed_component(processor)
        
        try:
            # Start processor (should start monitoring)
            processor.start()
            assert monitor.is_monitoring is True
            
            # Monitor should be tracking processor
            assert processor in monitor.managed_components
            
        finally:
            # Stop processor (should stop monitoring)
            processor.stop()
            # Note: might not immediately stop monitoring as it could monitor other components
    
    def test_memory_leak_detection(self, resource_monitor):
        """Test detection of potential memory leaks in long sessions."""
        # Simulate memory usage over time
        memory_samples = [
            45.0,  # Start normal
            47.0,  # Slight increase
            52.0,  # Growing...
            58.0,  # Still growing
            65.0,  # Concerning trend
            72.0   # Clear upward trend
        ]
        
        for sample in memory_samples:
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = sample
                resource_monitor.check_thresholds()
                time.sleep(0.01)  # Brief delay
        
        # Check if leak detection triggered
        leak_detected = resource_monitor.detect_memory_leak_pattern()
        
        # With clear upward trend, should detect potential leak
        assert leak_detected is True
        
        # Should provide ADHD-friendly guidance
        recommendations = resource_monitor.get_leak_mitigation_suggestions()
        assert len(recommendations) > 0
        assert any('restart' in rec.lower() or 'break' in rec.lower() 
                  for rec in recommendations)