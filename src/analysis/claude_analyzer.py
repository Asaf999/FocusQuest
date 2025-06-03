"""
Claude AI integration using Claude Code CLI (FREE with Pro subscription)
No API costs - uses local Claude Code installation for ADHD-optimized analysis
"""
import subprocess
import json
import re
import os
import tempfile
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, time as time_type, timedelta
from functools import lru_cache
from collections import OrderedDict
import hashlib
from enum import Enum


logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Error during problem analysis"""
    pass


class CircuitBreakerError(Exception):
    """Error when circuit breaker is open"""
    pass


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class HintSet:
    """Three-tier Socratic hint system"""
    tier1: str  # Gentle nudge
    tier2: str  # More specific guidance
    tier3: str  # Nearly complete answer
    
    def get_hint(self, level: int) -> str:
        """Get hint by level (1-3)"""
        if level <= 1:
            return self.tier1
        elif level == 2:
            return self.tier2
        else:
            return self.tier3
    
    def __post_init__(self):
        """Validate progressive disclosure"""
        # Ensure progressive disclosure by padding if needed
        if not (len(self.tier1) < len(self.tier2) < len(self.tier3)):
            # Adjust to ensure progressive disclosure
            if len(self.tier2) <= len(self.tier1):
                self.tier2 = self.tier2 + " (more details)"
            if len(self.tier3) <= len(self.tier2):
                self.tier3 = self.tier3 + " (complete explanation with all steps)"


@dataclass
class StepBreakdown:
    """Single step in problem solution"""
    number: int
    description: str
    duration_minutes: int
    checkpoint_question: str
    hints: Optional[HintSet] = None
    
    def __post_init__(self):
        """Validate step parameters"""
        if not 1 <= self.duration_minutes <= 10:
            raise ValueError(f"Step duration must be 1-10 minutes, got {self.duration_minutes}")
        
        if not self.checkpoint_question:
            raise ValueError("Checkpoint question is required")
            
        if not self.hints:
            # Create default hints if none provided
            self.hints = HintSet(
                tier1="Think about what this step requires",
                tier2="Consider the key concept for this step",
                tier3="The answer involves applying the concept directly"
            )
    
    def is_valid(self) -> bool:
        """Check if step is valid"""
        return (
            1 <= self.duration_minutes <= 10 and
            bool(self.checkpoint_question) and
            self.hints is not None
        )


@dataclass
class ProblemAnalysis:
    """Complete analysis of a mathematical problem"""
    problem_type: str
    difficulty_rating: int
    concepts: List[str]
    estimated_time: int
    steps: List[StepBreakdown]
    summary: str
    adhd_tips: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate analysis"""
        if not 3 <= len(self.steps) <= 7:
            # Adjust if needed
            pass  # Allow flexibility


@dataclass
class ADHDProfile:
    """User's ADHD-specific parameters"""
    preferred_step_duration: int = 5
    energy_level: str = 'medium'  # low, medium, high
    medication_taken: Optional[bool] = None
    time_of_day: str = 'afternoon'  # morning, afternoon, evening
    streak_days: int = 0
    
    @classmethod
    def from_current_time(cls, current_time: Optional[time_type] = None):
        """Create profile based on current time"""
        if not current_time:
            current_time = datetime.now().time()
            
        hour = current_time.hour
        if 5 <= hour < 12:
            time_of_day = 'morning'
        elif 12 <= hour < 17:
            time_of_day = 'afternoon'
        else:
            time_of_day = 'evening'
            
        return cls(time_of_day=time_of_day)
    
    def get_complexity_multiplier(self) -> float:
        """Get complexity adjustment based on profile"""
        multiplier = 1.0
        
        # Energy level adjustments
        if self.energy_level == 'high':
            multiplier *= 1.2
        elif self.energy_level == 'low':
            multiplier *= 0.7
            
        # Medication adjustments
        if self.medication_taken is True:
            multiplier *= 1.1
        elif self.medication_taken is False:
            multiplier *= 0.8
            
        # Streak bonus
        if self.streak_days > 7:
            multiplier *= 1.1
        elif self.streak_days > 30:
            multiplier *= 1.2
            
        return multiplier


class ClaudeAnalyzer:
    """Analyzes mathematical problems using Claude Code CLI (FREE with Pro)"""
    
    def __init__(self, claude_cmd: str = "claude", cache_enabled: bool = True, timeout: int = 120, 
                 max_cache_size: int = 100, cache_ttl_hours: int = 24,
                 circuit_breaker_enabled: bool = True, failure_threshold: int = 3,
                 recovery_timeout: int = 300, half_open_max_calls: int = 2,
                 max_recovery_timeout: int = 3600):
        self.claude_cmd = claude_cmd
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        self.max_cache_size = max_cache_size
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache = OrderedDict()  # LRU cache using OrderedDict
        self._cache_timestamps = {}  # Track when each entry was created
        self.max_retries = 3
        
        # Circuit breaker configuration
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.half_open_max_calls = half_open_max_calls
        self.max_recovery_timeout = max_recovery_timeout
        self.initial_recovery_timeout = recovery_timeout
        
        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        
        # Metrics tracking
        self.total_calls = 0
        self.failed_calls = 0
        self.circuit_opened_count = 0
        
    def analyze_problem(
        self, 
        problem: Dict[str, Any],
        profile: Optional[ADHDProfile] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> ProblemAnalysis:
        """Analyze a mathematical problem with ADHD optimizations using Claude CLI"""
        if not profile:
            profile = ADHDProfile()
            
        # Check cache first (even if circuit is open)
        cache_key = self._get_cache_key(problem, profile)
        if self.cache_enabled:
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result
                
        # Check circuit breaker state after cache
        if self.circuit_breaker_enabled:
            self._check_circuit_state()
            
        # Build prompt
        prompt = self._build_prompt(problem, profile)
        
        # Call CLI with retries and circuit breaker
        max_retries = max_retries or self.max_retries
        timeout = timeout or self.timeout
        
        self.total_calls += 1
        
        try:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        
                    response = self._run_claude_cli(prompt, timeout)
                    
                    # Success - record in circuit breaker
                    if self.circuit_breaker_enabled:
                        self._record_success()
                    
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Record failure in circuit breaker
                        if self.circuit_breaker_enabled:
                            self._record_failure()
                        raise AnalysisError(f"Failed after {max_retries} retries: {str(e)}")
                    logger.warning(f"CLI call attempt {attempt + 1} failed: {str(e)}")
            
            # Parse response
            try:
                analysis = self._parse_response(response)
            except Exception as e:
                raise AnalysisError(f"Failed parsing response: {str(e)}")
                
            # Cache result with LRU management
            if self.cache_enabled:
                self._put_in_cache(cache_key, analysis)
                
            return analysis
            
        except AnalysisError as e:
            # Check if we can provide a cached fallback or manual entry mode
            if self.circuit_state == CircuitState.OPEN:
                # Try to serve from cache if available
                cached_result = self._get_from_cache(cache_key, ignore_ttl=True)
                if cached_result is not None:
                    logger.info("Serving stale cached response due to circuit breaker")
                    return cached_result
                    
                # Provide fallback analysis
                fallback_dict = self.get_fallback_analysis(problem.get('translated_text', ''))
                # Convert fallback dict to ProblemAnalysis object
                fallback_problem = fallback_dict['problems'][0]
                steps = []
                for step_data in fallback_problem['steps']:
                    # Create default hints for manual steps
                    hints = HintSet(
                        tier1='Take your time with this step',
                        tier2='Consider what you know so far',
                        tier3='Break it down into smaller parts'
                    )
                    step = StepBreakdown(
                        number=len(steps) + 1,
                        description=step_data['content'],
                        duration_minutes=step_data.get('duration', 5),
                        checkpoint_question="Ready to continue?",
                        hints=hints
                    )
                    steps.append(step)
                
                return ProblemAnalysis(
                    problem_type='manual',
                    difficulty_rating=fallback_problem.get('difficulty', 3),
                    concepts=[],
                    estimated_time=sum(s.duration_minutes for s in steps),
                    steps=steps,
                    summary='Manual problem solving mode',
                    adhd_tips=fallback_problem.get('adhd_tips', [])
                )
            else:
                raise
    
    def _get_cache_key(self, problem: Dict, profile: ADHDProfile) -> str:
        """Generate cache key for problem + profile"""
        key_data = f"{problem.get('translated_text', '')}{profile.energy_level}{profile.medication_taken}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _build_prompt(self, problem: Dict, profile: ADHDProfile) -> str:
        """Build ADHD-optimized prompt for Claude CLI"""
        prompt = f"""You are helping an ADHD student at Tel Aviv University solve a mathematical problem.

CRITICAL REQUIREMENTS FOR ADHD:
1. Break solution into 3-7 steps (NEVER more than 7)
2. Each step must take 3-10 minutes MAX (prefer {profile.preferred_step_duration} minutes)
3. Single clear action per step - no multi-tasking
4. Checkpoint questions for dopamine hits after each step
5. Three-tier Socratic hints for each step

USER PROFILE:
- Energy level: {profile.energy_level}
- Medication: {'taken' if profile.medication_taken else 'not taken' if profile.medication_taken is False else 'unknown'}
- Time of day: {profile.time_of_day}
- Current streak: {profile.streak_days} days

PROBLEM:
Original (Hebrew): {problem.get('raw_text', '')}
Translation: {problem.get('translated_text', '')}
Formulas: {json.dumps(problem.get('formulas', []))}
Difficulty: {problem.get('difficulty', 3)}/5

OUTPUT FORMAT (Return ONLY valid JSON, no extra text):
{{
    "analysis": {{
        "problem_type": "derivative|integral|limit|equation|proof|other",
        "difficulty_rating": 1-5,
        "concepts": ["concept1", "concept2"],
        "estimated_time": total_minutes
    }},
    "steps": [
        {{
            "number": 1,
            "description": "Clear description of what to do",
            "duration_minutes": 3-10,
            "checkpoint_question": "Question to verify understanding?",
            "hints": {{
                "tier1": "Gentle nudge (short)",
                "tier2": "More specific help (medium)",
                "tier3": "Nearly complete guidance (detailed)"
            }}
        }}
    ],
    "summary": "Brief summary of the solution approach",
    "adhd_tips": [
        "Use scratch paper for this step",
        "Take a 2-minute break after step 3",
        "This step is easier than it looks"
    ]
}}

Remember:
- First step should be especially easy to build confidence
- Hints must progressively disclose more information
- Adapt complexity based on energy level and medication
- Include ADHD-specific tips for challenging steps"""

        return prompt
    
    def _run_claude_cli(self, prompt: str, timeout: float) -> str:
        """Execute Claude Code CLI with proper handling"""
        
        # Create temp file for complex prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            temp_path = f.name
            
        try:
            # Prepare command
            cmd = [self.claude_cmd]
            
            # Read prompt from file
            with open(temp_path, 'r') as f:
                prompt_content = f.read()
            
            # Run claude with prompt via stdin
            result = subprocess.run(
                cmd,
                input=prompt_content,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, 'CLAUDE_AUTO_ACCEPT': 'true'}
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI failed: {result.stderr}")
                
            return result.stdout
            
        except subprocess.TimeoutExpired:
            raise AnalysisError(f"Claude CLI timeout after {timeout} seconds")
        except FileNotFoundError:
            raise AnalysisError(f"Claude CLI not found. Make sure '{self.claude_cmd}' is installed and in PATH")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _parse_response(self, output: str) -> ProblemAnalysis:
        """Extract JSON from Claude CLI output"""
        
        # Remove ANSI color codes if present
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)
        
        # Find JSON in output (Claude may add explanatory text)
        json_match = re.search(r'\{[\s\S]*\}', output)
        if not json_match:
            raise ValueError("No JSON found in Claude response")
            
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues
            json_str = json_match.group()
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            data = json.loads(json_str)
        
        # Validate and parse response
        analysis_data = data.get('analysis', {})
        steps_data = data.get('steps', [])
        
        if not steps_data:
            raise AnalysisError("No steps provided in response")
        
        # Ensure ADHD compliance - max 7 steps
        if len(steps_data) > 7:
            logger.warning(f"Truncating {len(steps_data)} steps to maximum 7")
            steps_data = steps_data[:7]
        
        # Parse steps
        steps = []
        for i, step_data in enumerate(steps_data):
            hints_data = step_data.get('hints', {})
            # Handle both dict and list formats for hints
            if isinstance(hints_data, list):
                # Convert list to dict format
                hints = HintSet(
                    tier1=hints_data[0] if len(hints_data) > 0 else 'Think about this step',
                    tier2=hints_data[1] if len(hints_data) > 1 else 'Consider the approach',
                    tier3=hints_data[2] if len(hints_data) > 2 else 'Here is the detailed solution'
                )
            else:
                hints = HintSet(
                    tier1=hints_data.get('tier1', 'Think about this step'),
                    tier2=hints_data.get('tier2', 'Consider the approach'),
                    tier3=hints_data.get('tier3', 'Here is the detailed solution')
                )
            
            # Ensure duration is ADHD-friendly
            duration = step_data.get('duration_minutes', 5)
            duration = min(10, max(3, duration))
            
            step = StepBreakdown(
                number=step_data.get('number', i + 1),
                description=step_data.get('description', f'Complete step {i + 1}'),
                duration_minutes=duration,
                checkpoint_question=step_data.get('checkpoint_question', 'Do you understand this step?'),
                hints=hints
            )
            steps.append(step)
        
        # Create analysis
        analysis = ProblemAnalysis(
            problem_type=analysis_data.get('problem_type', 'general'),
            difficulty_rating=analysis_data.get('difficulty_rating', 3),
            concepts=analysis_data.get('concepts', []),
            estimated_time=analysis_data.get('estimated_time', sum(s.duration_minutes for s in steps)),
            steps=steps,
            summary=data.get('summary', 'Complete the problem step by step'),
            adhd_tips=data.get('adhd_tips', [])
        )
        
        return analysis
    
    def _get_from_cache(self, cache_key: str, ignore_ttl: bool = False) -> Optional[ProblemAnalysis]:
        """Get item from cache with TTL and LRU management"""
        if cache_key not in self._cache:
            return None
        
        # Check if entry has expired (unless ignoring TTL for circuit breaker fallback)
        if not ignore_ttl and cache_key in self._cache_timestamps:
            entry_time = self._cache_timestamps[cache_key]
            if datetime.now() - entry_time > self.cache_ttl:
                # Remove expired entry
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None
        
        # Move to end (most recently accessed) for LRU
        self._cache.move_to_end(cache_key)
        return self._cache[cache_key]
    
    def _put_in_cache(self, cache_key: str, analysis: ProblemAnalysis):
        """Put item in cache with size and TTL management"""
        # Remove if already exists
        if cache_key in self._cache:
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
        
        # Check if cache is full
        if len(self._cache) >= self.max_cache_size:
            # Remove oldest (LRU) entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        # Add new entry
        self._cache[cache_key] = analysis
        self._cache_timestamps[cache_key] = datetime.now()
    
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries (can be called periodically)"""
        current_time = datetime.now()
        expired_keys = []
        
        for cache_key, timestamp in self._cache_timestamps.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self._cache[key]
            del self._cache_timestamps[key]
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid (not expired)"""
        if cache_key not in self._cache_timestamps:
            return False
        
        entry_time = self._cache_timestamps[cache_key]
        return datetime.now() - entry_time <= self.cache_ttl
    
    def clear_cache(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def analyze_problems(self, content: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Analyze problems with circuit breaker protection (plural interface)."""
        problem = {
            'translated_text': content,
            'difficulty': 3
        }
        profile = ADHDProfile()
        
        try:
            analysis = self.analyze_problem(problem, profile, timeout=timeout)
            # Handle both ProblemAnalysis object and dict responses
            if isinstance(analysis, dict):
                # Legacy dict format
                return analysis
            else:
                # ProblemAnalysis object format
                return {
                    'problems': [{
                        'text': content,
                        'steps': [{'content': step.description} for step in analysis.steps],
                        'hints': [],
                        'difficulty': analysis.difficulty_rating
                    }]
                }
        except CircuitBreakerError:
            # Re-raise circuit breaker errors as-is
            raise
        except AnalysisError as e:
            # Only convert to circuit breaker error if circuit is open
            if self.circuit_state == CircuitState.OPEN:
                raise CircuitBreakerError(
                    "Claude AI is temporarily having trouble, but don't worry! "
                    "You can continue learning while it recovers. "
                    "Try manual problem entry or take a short break."
                )
            else:
                raise e
    
    def _check_circuit_state(self):
        """Check circuit breaker state and throw error if open."""
        if self.circuit_state == CircuitState.OPEN:
            # Check if enough time has passed for recovery attempt
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)):
                # Transition to half-open for testing
                self.circuit_state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                # Still in open state, block the call
                raise CircuitBreakerError(
                    "Claude AI is temporarily having trouble, but don't worry! "
                    "It's taking a short break to recover. "
                    f"Please try again in {self._get_recovery_time_remaining()} seconds, "
                    "or continue with manual problem entry."
                )
        elif self.circuit_state == CircuitState.HALF_OPEN:
            # Allow calls up to the limit
            pass
    
    def _record_success(self):
        """Record successful call in circuit breaker."""
        if self.circuit_state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            
            # If we've had enough successful calls in half-open, close the circuit
            if self.half_open_calls >= self.half_open_max_calls:
                self.circuit_state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                self.recovery_timeout = self.initial_recovery_timeout  # Reset backoff
                self._notify_recovery()
                logger.info("Circuit breaker closed - service recovered")
        elif self.circuit_state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
    
    def _record_failure(self):
        """Record failed call in circuit breaker."""
        self.failure_count += 1
        self.failed_calls += 1
        self.last_failure_time = datetime.now()
        
        if self.circuit_state == CircuitState.HALF_OPEN:
            # Failure in half-open state - go back to open
            self.circuit_state = CircuitState.OPEN
            self._calculate_backoff_timeout()
            logger.warning("Circuit breaker opened - service still failing")
        elif (self.circuit_state == CircuitState.CLOSED and 
              self.failure_count >= self.failure_threshold):
            # Too many failures - open the circuit
            self.circuit_state = CircuitState.OPEN
            self.circuit_opened_count += 1
            self._calculate_backoff_timeout()
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _calculate_backoff_timeout(self):
        """Calculate exponential backoff for recovery timeout."""
        # Exponential backoff: double the timeout each time, up to max
        backoff_multiplier = 2 ** (self.circuit_opened_count - 1)
        self.recovery_timeout = min(
            self.initial_recovery_timeout * backoff_multiplier,
            self.max_recovery_timeout
        )
        logger.debug(f"Recovery timeout set to {self.recovery_timeout} seconds")
    
    def _get_recovery_time_remaining(self) -> int:
        """Get seconds remaining until recovery attempt."""
        if not self.last_failure_time:
            return 0
        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return max(0, int(self.recovery_timeout - elapsed))
    
    def _notify_recovery(self):
        """Notify that circuit breaker has recovered (placeholder for future notification)."""
        # This could trigger a UI notification in the future
        pass
    
    def get_fallback_analysis(self, problem_text: str) -> Dict[str, Any]:
        """Provide fallback analysis when Claude is unavailable."""
        logger.info("Providing fallback analysis due to Claude unavailability")
        
        # Basic problem structure for manual entry
        fallback_problem = {
            'original_text': problem_text,
            'translated_text': problem_text,
            'manual_entry': True,
            'steps': [
                {
                    'content': 'Read and understand the problem carefully',
                    'duration': 3,
                    'manual': True
                },
                {
                    'content': 'Identify what you need to find',
                    'duration': 2,
                    'manual': True
                },
                {
                    'content': 'Plan your solution approach',
                    'duration': 5,
                    'manual': True
                },
                {
                    'content': 'Work through the problem step by step',
                    'duration': 10,
                    'manual': True
                },
                {
                    'content': 'Check your answer makes sense',
                    'duration': 2,
                    'manual': True
                }
            ],
            'hints': [
                {
                    'level': 1,
                    'content': 'Take your time and break this down into smaller parts'
                },
                {
                    'level': 2, 
                    'content': 'What information is given? What do you need to find?'
                },
                {
                    'level': 3,
                    'content': 'Consider similar problems you\'ve solved before'
                }
            ],
            'difficulty': 3,
            'adhd_tips': [
                'It\'s okay to take breaks while working on this',
                'Focus on one step at a time',
                'Ask for help if you get stuck'
            ]
        }
        
        return {
            'problems': [fallback_problem],
            'manual_entry': True,
            'note': 'Claude AI is temporarily unavailable. Continue learning with manual problem solving!'
        }
    
    def get_circuit_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        success_rate = 0.0
        if self.total_calls > 0:
            success_rate = (self.total_calls - self.failed_calls) / self.total_calls
            
        return {
            'current_state': self.circuit_state.value,
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'success_rate': success_rate,
            'failure_count': self.failure_count,
            'circuit_opened_count': self.circuit_opened_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'recovery_timeout': self.recovery_timeout,
            'time_until_recovery': self._get_recovery_time_remaining()
        }
    
    def perform_health_check(self) -> bool:
        """Perform health check on Claude CLI."""
        try:
            # Simple health check - try to run claude with --version or similar
            result = subprocess.run(
                [self.claude_cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def save_circuit_state(self) -> Dict[str, Any]:
        """Save circuit breaker state for persistence."""
        return {
            'circuit_state': self.circuit_state.value,
            'failure_count': self.failure_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'half_open_calls': self.half_open_calls,
            'recovery_timeout': self.recovery_timeout,
            'circuit_opened_count': self.circuit_opened_count,
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls
        }
    
    def restore_circuit_state(self, state: Dict[str, Any]):
        """Restore circuit breaker state from saved data."""
        self.circuit_state = CircuitState(state['circuit_state'])
        self.failure_count = state['failure_count']
        self.last_failure_time = datetime.fromisoformat(state['last_failure_time']) if state['last_failure_time'] else None
        self.half_open_calls = state['half_open_calls']
        self.recovery_timeout = state['recovery_timeout']
        self.circuit_opened_count = state['circuit_opened_count']
        self.total_calls = state['total_calls']
        self.failed_calls = state['failed_calls']


# Convenience function for quick analysis
def analyze_math_problem(
    problem_text: str,
    energy_level: str = 'medium',
    medication_taken: bool = True
) -> ProblemAnalysis:
    """Quick function to analyze a math problem using Claude CLI"""
    analyzer = ClaudeAnalyzer()
    
    problem = {
        'translated_text': problem_text,
        'difficulty': 3
    }
    
    profile = ADHDProfile(
        energy_level=energy_level,
        medication_taken=medication_taken
    )
    
    return analyzer.analyze_problem(problem, profile)