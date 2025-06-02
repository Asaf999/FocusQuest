"""
ADHD-optimized resource monitoring system for preventing performance issues.
Provides gentle, proactive monitoring with non-anxiety-inducing alerts.
"""
import psutil
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import deque

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Resource alert severity levels with ADHD-friendly priorities."""
    INFO = "info"          # General information
    GENTLE = "gentle"      # Gentle suggestion 
    WARNING = "warning"    # Attention needed
    CRITICAL = "critical"  # Immediate action required


@dataclass
class ResourceAlert:
    """Resource alert with ADHD-friendly messaging."""
    timestamp: datetime
    resource_type: str  # memory, cpu, disk, process
    level: AlertLevel
    message: str
    value: float
    threshold: float
    suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for storage/transmission."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'resource_type': self.resource_type,
            'level': self.level.value,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'suggestions': self.suggestions
        }


class ResourceMonitor:
    """
    ADHD-optimized resource monitoring system that prevents performance issues
    from disrupting focus and learning flow.
    """
    
    def __init__(
        self,
        memory_warning_threshold: float = 0.75,    # 75%
        memory_critical_threshold: float = 0.85,   # 85%
        cpu_warning_threshold: float = 0.80,       # 80%
        cpu_critical_threshold: float = 0.90,      # 90%
        disk_warning_threshold: float = 0.85,      # 85%
        disk_critical_threshold: float = 0.95,     # 95%
        check_interval: float = 30.0,              # 30 seconds
        adhd_mode: bool = True,                     # Use ADHD-friendly messaging
        max_history_size: int = 100                # Keep last 100 alerts
    ):
        # Thresholds
        self.memory_warning_threshold = memory_warning_threshold
        self.memory_critical_threshold = memory_critical_threshold
        self.cpu_warning_threshold = cpu_warning_threshold
        self.cpu_critical_threshold = cpu_critical_threshold
        self.disk_warning_threshold = disk_warning_threshold
        self.disk_critical_threshold = disk_critical_threshold
        
        # Configuration
        self.check_interval = check_interval
        self.adhd_mode = adhd_mode
        self.max_history_size = max_history_size
        
        # State
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Managed components (e.g., QueueProcessor)
        self.managed_components: List[Any] = []
        
        # History and tracking
        self.alert_history: deque = deque(maxlen=max_history_size)
        self.memory_samples: deque = deque(maxlen=50)  # Last 50 samples for trend analysis
        self.cpu_samples: deque = deque(maxlen=20)     # Last 20 samples for CPU
        
        # Session tracking
        self.current_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.last_check_time: Optional[datetime] = None
        self.check_durations: deque = deque(maxlen=10)
        
        # Process reference
        self.process = psutil.Process()
        
    def add_managed_component(self, component: Any):
        """Add a component to be managed by resource monitor."""
        if component not in self.managed_components:
            self.managed_components.append(component)
            logger.info(f"Added {type(component).__name__} to resource monitoring")
            
    def remove_managed_component(self, component: Any):
        """Remove a component from resource monitoring."""
        if component in self.managed_components:
            self.managed_components.remove(component)
            logger.info(f"Removed {type(component).__name__} from resource monitoring")
    
    def start_monitoring(self):
        """Start continuous resource monitoring."""
        if self.is_monitoring:
            logger.warning("Resource monitoring already running")
            return
            
        logger.info("Starting resource monitoring for ADHD-optimized performance")
        self.stop_event.clear()
        self.is_monitoring = True
        
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring gracefully."""
        if not self.is_monitoring:
            return
            
        logger.info("Stopping resource monitoring")
        self.stop_event.set()
        self.is_monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
            
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self.stop_event.is_set():
            start_time = time.time()
            
            try:
                # Check all resource thresholds
                alerts = self.check_thresholds()
                
                # Handle any alerts
                if alerts:
                    self._handle_alerts(alerts)
                    
                # Update samples for trend analysis
                self._update_samples()
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                
            # Track monitoring performance
            duration = time.time() - start_time
            self.check_durations.append(duration)
            self.last_check_time = datetime.now()
            
            # Wait for next check
            self.stop_event.wait(timeout=self.check_interval)
    
    def check_thresholds(self) -> List[ResourceAlert]:
        """Check all resource thresholds and return alerts."""
        alerts = []
        
        # Memory check
        memory_info = self.get_memory_usage()
        memory_percent = memory_info['percentage'] / 100.0
        
        if memory_percent >= self.memory_critical_threshold:
            alerts.append(self._create_memory_alert(
                AlertLevel.CRITICAL, memory_percent, "critical memory usage"
            ))
        elif memory_percent >= self.memory_warning_threshold:
            alerts.append(self._create_memory_alert(
                AlertLevel.WARNING, memory_percent, "high memory usage"
            ))
            
        # CPU check
        cpu_info = self.get_cpu_usage()
        cpu_percent = cpu_info['percentage'] / 100.0
        
        if cpu_percent >= self.cpu_critical_threshold:
            alerts.append(self._create_cpu_alert(
                AlertLevel.CRITICAL, cpu_percent, "very high CPU usage"
            ))
        elif cpu_percent >= self.cpu_warning_threshold:
            alerts.append(self._create_cpu_alert(
                AlertLevel.WARNING, cpu_percent, "high CPU usage"
            ))
            
        # Disk check
        disk_info = self.get_disk_usage()
        disk_percent = disk_info['percentage'] / 100.0
        
        if disk_percent >= self.disk_critical_threshold:
            alerts.append(self._create_disk_alert(
                AlertLevel.CRITICAL, disk_percent, "very low disk space"
            ))
        elif disk_percent >= self.disk_warning_threshold:
            alerts.append(self._create_disk_alert(
                AlertLevel.WARNING, disk_percent, "low disk space"
            ))
            
        return alerts
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information."""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percentage': memory.percent
        }
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get current CPU usage information."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Get load average on Unix systems
        load_avg = None
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            # Windows doesn't have getloadavg
            load_avg = [0, 0, 0]
            
        return {
            'percentage': cpu_percent,
            'per_cpu': cpu_per_core,
            'load_average': load_avg
        }
    
    def get_disk_usage(self, path: str = '/') -> Dict[str, Any]:
        """Get disk usage for specified path."""
        try:
            disk = psutil.disk_usage(path)
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percentage': (disk.used / disk.total) * 100
            }
        except Exception as e:
            logger.error(f"Error getting disk usage for {path}: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percentage': 0}
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current FocusQuest process."""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            return {
                'memory_mb': memory_info.rss / (1024 * 1024),  # Convert to MB
                'cpu_percent': cpu_percent,
                'open_files': len(self.process.open_files()),
                'threads': self.process.num_threads(),
                'pid': self.process.pid
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {'memory_mb': 0, 'cpu_percent': 0, 'open_files': 0, 'threads': 0, 'pid': 0}
    
    def estimate_pdf_memory_usage(self, pages: int, avg_page_size_kb: int = 200) -> int:
        """Estimate memory usage for processing a PDF."""
        # Base memory for PDF processing
        base_memory = 50 * 1024 * 1024  # 50MB base
        
        # Memory per page (OCR, text extraction, etc.)
        memory_per_page = avg_page_size_kb * 1024 * 5  # 5x page size for processing
        
        # Claude analysis overhead
        claude_overhead = pages * 2 * 1024 * 1024  # 2MB per problem
        
        total_estimate = base_memory + (memory_per_page * pages) + claude_overhead
        
        return total_estimate
    
    def should_reduce_workers_for_task(self, estimated_memory_mb: int) -> bool:
        """Determine if worker count should be reduced for a task."""
        memory_info = self.get_memory_usage()
        available_mb = memory_info['available'] / (1024 * 1024)
        
        # If estimated memory per worker would use > 80% of available memory, reduce
        safety_factor = 0.8
        safe_memory_per_worker = (available_mb * safety_factor) / max(len(self.managed_components), 1)
        
        return estimated_memory_mb > safe_memory_per_worker
    
    def _create_memory_alert(self, level: AlertLevel, value: float, description: str) -> ResourceAlert:
        """Create ADHD-friendly memory alert."""
        if self.adhd_mode:
            if level == AlertLevel.CRITICAL:
                message = f"Your computer is working really hard and needs a gentle break! 💻 " \
                         f"Memory usage is at {value*100:.1f}%. Let's help it out by reducing some tasks."
                suggestions = [
                    "Take a 5-minute break to let things cool down",
                    "Close any extra browser tabs or applications",
                    "Save your work and consider a gentle restart",
                    "This is normal - computers need breaks too!"
                ]
            else:
                message = f"Just a heads up - memory usage is at {value*100:.1f}%. 🌱 " \
                         f"Everything's fine, but we're gently optimizing things for you."
                suggestions = [
                    "No need to worry - this is just proactive care",
                    "We're automatically adjusting to keep things smooth",
                    "Your learning session will continue uninterrupted"
                ]
        else:
            message = f"Memory usage: {value*100:.1f}% ({description})"
            suggestions = ["Reduce concurrent tasks", "Free up memory"]
            
        return ResourceAlert(
            timestamp=datetime.now(),
            resource_type='memory',
            level=level,
            message=message,
            value=value,
            threshold=self.memory_warning_threshold if level == AlertLevel.WARNING else self.memory_critical_threshold,
            suggestions=suggestions
        )
    
    def _create_cpu_alert(self, level: AlertLevel, value: float, description: str) -> ResourceAlert:
        """Create ADHD-friendly CPU alert."""
        if self.adhd_mode:
            if level == AlertLevel.CRITICAL:
                message = f"Your computer's brain is working extra hard right now! 🧠 " \
                         f"CPU usage is at {value*100:.1f}%. Let's give it a moment to catch up."
                suggestions = [
                    "Take a short break while things settle",
                    "Close any heavy applications you're not using",
                    "This is temporary - your computer is just being thorough!"
                ]
            else:
                message = f"CPU is busy at {value*100:.1f}%, but we've got this! 💪 " \
                         f"We're automatically optimizing for smooth performance."
                suggestions = [
                    "Everything is under control",
                    "We're balancing tasks to keep you focused",
                    "No action needed - just keep learning!"
                ]
        else:
            message = f"CPU usage: {value*100:.1f}% ({description})"
            suggestions = ["Reduce concurrent processes", "Check for background tasks"]
            
        return ResourceAlert(
            timestamp=datetime.now(),
            resource_type='cpu',
            level=level,
            message=message,
            value=value,
            threshold=self.cpu_warning_threshold if level == AlertLevel.WARNING else self.cpu_critical_threshold,
            suggestions=suggestions
        )
    
    def _create_disk_alert(self, level: AlertLevel, value: float, description: str) -> ResourceAlert:
        """Create ADHD-friendly disk space alert."""
        if self.adhd_mode:
            if level == AlertLevel.CRITICAL:
                message = f"Your computer's storage space is getting cozy! 📦 " \
                         f"Disk usage is at {value*100:.1f}%. Time for a gentle cleanup."
                suggestions = [
                    "Let's clear out some old files together",
                    "Check your Downloads folder for things you don't need",
                    "Empty the trash when you're ready",
                    "This is a good excuse for some digital decluttering!"
                ]
            else:
                message = f"Storage is {value*100:.1f}% full - time to think about decluttering! 🧹 " \
                         f"No rush, but it's good to stay organized."
                suggestions = [
                    "Consider cleaning up when you have a moment",
                    "Old PDFs can be archived or deleted",
                    "This is normal maintenance - nothing urgent"
                ]
        else:
            message = f"Disk usage: {value*100:.1f}% ({description})"
            suggestions = ["Free up disk space", "Archive old files"]
            
        return ResourceAlert(
            timestamp=datetime.now(),
            resource_type='disk',
            level=level,
            message=message,
            value=value,
            threshold=self.disk_warning_threshold if level == AlertLevel.WARNING else self.disk_critical_threshold,
            suggestions=suggestions
        )
    
    def _handle_alerts(self, alerts: List[ResourceAlert]):
        """Handle resource alerts with appropriate actions."""
        for alert in alerts:
            # Add to history
            self.alert_history.append(alert.to_dict())
            
            # Log alert
            if alert.level == AlertLevel.CRITICAL:
                logger.warning(f"CRITICAL: {alert.message}")
            elif alert.level == AlertLevel.WARNING:
                logger.info(f"WARNING: {alert.message}")
            else:
                logger.debug(f"INFO: {alert.message}")
                
            # Take automatic actions
            self._take_automatic_action(alert)
    
    def _take_automatic_action(self, alert: ResourceAlert):
        """Take automatic actions based on alert type and severity."""
        if alert.resource_type == 'memory' and alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
            self._reduce_memory_pressure()
        elif alert.resource_type == 'cpu' and alert.level == AlertLevel.CRITICAL:
            self._reduce_cpu_pressure()
    
    def _reduce_memory_pressure(self):
        """Reduce memory pressure by adjusting managed components."""
        for component in self.managed_components:
            if hasattr(component, 'max_workers') and component.max_workers > 1:
                # Reduce worker count by 1
                old_workers = component.max_workers
                component.max_workers = max(1, component.max_workers - 1)
                logger.info(f"Reduced {type(component).__name__} workers from {old_workers} to {component.max_workers}")
                
                # If it has an active executor, apply the change
                if hasattr(component, 'executor') and component.executor:
                    component.executor._max_workers = component.max_workers
    
    def _reduce_cpu_pressure(self):
        """Reduce CPU pressure by slowing down operations."""
        for component in self.managed_components:
            if hasattr(component, 'poll_interval'):
                # Increase polling interval to reduce CPU usage
                old_interval = component.poll_interval
                component.poll_interval = min(30.0, component.poll_interval * 1.5)
                logger.info(f"Increased {type(component).__name__} poll interval from {old_interval} to {component.poll_interval}")
    
    def _attempt_worker_recovery(self):
        """Attempt to restore worker count when resources are available."""
        memory_info = self.get_memory_usage()
        cpu_info = self.get_cpu_usage()
        
        # Only recover if resources are comfortably available
        if (memory_info['percentage'] < self.memory_warning_threshold * 80 and  # 20% below warning
            cpu_info['percentage'] < self.cpu_warning_threshold * 80):           # 20% below warning
            
            for component in self.managed_components:
                if hasattr(component, 'max_workers') and hasattr(component, '_original_max_workers'):
                    if component.max_workers < component._original_max_workers:
                        component.max_workers = min(
                            component._original_max_workers,
                            component.max_workers + 1
                        )
                        logger.info(f"Restored {type(component).__name__} workers to {component.max_workers}")
    
    def _update_samples(self):
        """Update resource usage samples for trend analysis."""
        memory_info = self.get_memory_usage()
        cpu_info = self.get_cpu_usage()
        
        self.memory_samples.append({
            'timestamp': datetime.now(),
            'percentage': memory_info['percentage']
        })
        
        self.cpu_samples.append({
            'timestamp': datetime.now(),
            'percentage': cpu_info['percentage']
        })
    
    def detect_memory_leak_pattern(self) -> bool:
        """Detect potential memory leak patterns."""
        if len(self.memory_samples) < 5:
            return False
            
        # Check for consistent upward trend
        recent_samples = list(self.memory_samples)[-10:]  # Last 10 samples
        percentages = [sample['percentage'] for sample in recent_samples]
        
        # Simple trend detection: are we consistently increasing?
        if len(percentages) >= 5:
            # Check if each sample is higher than previous (with some tolerance)
            increases = 0
            for i in range(1, len(percentages)):
                if percentages[i] > percentages[i-1] + 1.0:  # 1% tolerance
                    increases += 1
                    
            # If 70% of samples show increase, consider it a trend
            return increases / (len(percentages) - 1) > 0.7
            
        return False
    
    def get_leak_mitigation_suggestions(self) -> List[str]:
        """Get ADHD-friendly suggestions for mitigating memory leaks."""
        if self.adhd_mode:
            return [
                "Take a learning break and restart FocusQuest - fresh starts are good! 🌟",
                "Save your progress and give your computer a quick refresh",
                "This isn't a problem with your work - just technology being technology",
                "A restart can be like a deep breath for your computer",
                "Consider it a natural pause in your learning rhythm"
            ]
        else:
            return [
                "Restart the application to clear memory",
                "Check for memory-intensive background processes",
                "Consider reducing concurrent operations"
            ]
    
    def get_cleanup_recommendations(self) -> List[Dict[str, str]]:
        """Get ADHD-friendly cleanup recommendations."""
        recommendations = []
        
        # Check disk usage
        disk_info = self.get_disk_usage()
        if disk_info['percentage'] > 70:
            recommendations.append({
                'action': 'Clear out old PDF files from your inbox folder',
                'benefit': 'Frees up space and keeps things organized',
                'difficulty': 'Easy',
                'time_needed': '5 minutes'
            })
            
        # Check memory usage
        memory_info = self.get_memory_usage()
        if memory_info['percentage'] > 60:
            recommendations.append({
                'action': 'Close extra browser tabs or applications',
                'benefit': 'Gives FocusQuest more room to work smoothly',
                'difficulty': 'Easy',
                'time_needed': '2 minutes'
            })
            
        # Process-specific recommendations
        process_info = self.get_process_info()
        if process_info['memory_mb'] > 200:  # If using more than 200MB
            recommendations.append({
                'action': 'Take a break and restart FocusQuest',
                'benefit': 'Refreshes the app and clears any accumulated data',
                'difficulty': 'Easy',
                'time_needed': '1 minute'
            })
            
        return recommendations
    
    def start_session_monitoring(self, session_name: str) -> str:
        """Start monitoring a specific study session."""
        session_id = f"{session_name}_{datetime.now().isoformat()}"
        
        self.current_sessions[session_id] = {
            'name': session_name,
            'start_time': datetime.now(),
            'start_memory': self.get_memory_usage(),
            'start_cpu': self.get_cpu_usage(),
            'peak_memory': 0,
            'memory_samples': [],
            'cpu_samples': []
        }
        
        logger.info(f"Started session monitoring: {session_name}")
        return session_id
    
    def end_session_monitoring(self, session_id: str) -> Dict[str, Any]:
        """End session monitoring and generate report."""
        if session_id not in self.current_sessions:
            return {}
            
        session = self.current_sessions[session_id]
        end_time = datetime.now()
        duration = end_time - session['start_time']
        
        # Calculate session statistics
        avg_memory = statistics.mean(sample['percentage'] for sample in session['memory_samples']) if session['memory_samples'] else 0
        peak_memory = max(sample['percentage'] for sample in session['memory_samples']) if session['memory_samples'] else 0
        avg_cpu = statistics.mean(sample['percentage'] for sample in session['cpu_samples']) if session['cpu_samples'] else 0
        
        report = {
            'session_name': session['name'],
            'duration': duration.total_seconds(),
            'peak_memory': peak_memory,
            'average_memory': avg_memory,
            'average_cpu': avg_cpu,
            'recommendations': self._generate_session_recommendations(session),
            'insights': self._generate_adhd_insights(session)
        }
        
        # Clean up
        del self.current_sessions[session_id]
        
        return report
    
    def _generate_session_recommendations(self, session: Dict[str, Any]) -> List[str]:
        """Generate session-specific recommendations."""
        recommendations = []
        
        if session.get('peak_memory', 0) > 80:
            recommendations.append("Consider taking breaks during long study sessions")
            
        if len(session.get('memory_samples', [])) > 20:  # Long session
            recommendations.append("Great sustained focus! Remember to hydrate and stretch")
            
        return recommendations
    
    def _generate_adhd_insights(self, session: Dict[str, Any]) -> List[str]:
        """Generate ADHD-specific insights about the session."""
        insights = []
        
        duration_minutes = (datetime.now() - session['start_time']).total_seconds() / 60
        
        if duration_minutes > 60:
            insights.append("Impressive sustained focus! Long sessions show great progress in building concentration.")
        elif duration_minutes > 25:
            insights.append("Perfect session length for maintaining focus without burnout.")
        
        if session.get('peak_memory', 0) < 60:
            insights.append("Your computer stayed happy and responsive throughout - great for maintaining flow!")
            
        return insights
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        return list(self.alert_history)[-limit:]
    
    def get_monitoring_performance(self) -> Dict[str, Any]:
        """Get performance metrics for the monitoring system itself."""
        avg_check_duration = statistics.mean(self.check_durations) if self.check_durations else 0
        
        return {
            'average_check_duration': avg_check_duration,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'total_alerts': len(self.alert_history),
            'managed_components': len(self.managed_components),
            'monitoring_overhead': avg_check_duration * 100 / self.check_interval if self.check_interval > 0 else 0
        }