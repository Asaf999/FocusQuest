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
from datetime import datetime, time as time_type
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Error during problem analysis"""
    pass


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
    
    def __init__(self, claude_cmd: str = "claude", cache_enabled: bool = True, timeout: int = 120):
        self.claude_cmd = claude_cmd
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        self._cache = {}
        self.max_retries = 3
        
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
            
        # Check cache
        cache_key = self._get_cache_key(problem, profile)
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
            
        # Build prompt
        prompt = self._build_prompt(problem, profile)
        
        # Call CLI with retries
        max_retries = max_retries or self.max_retries
        timeout = timeout or self.timeout
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
                response = self._run_claude_cli(prompt, timeout)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise AnalysisError(f"Failed after {max_retries} retries: {str(e)}")
                logger.warning(f"CLI call attempt {attempt + 1} failed: {str(e)}")
        
        # Parse response
        try:
            analysis = self._parse_response(response)
        except Exception as e:
            raise AnalysisError(f"Failed parsing response: {str(e)}")
            
        # Cache result
        if self.cache_enabled:
            self._cache[cache_key] = analysis
            
        return analysis
    
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