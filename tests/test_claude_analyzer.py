"""
Tests for Claude AI integration with ADHD-optimized problem analysis
Tests focus on step generation, hint creation, and response parsing
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time

from src.analysis.claude_analyzer import (
    ClaudeAnalyzer, ProblemAnalysis, StepBreakdown,
    HintSet, AnalysisError, ADHDProfile
)


class TestClaudeAnalyzer:
    """Test Claude AI analyzer functionality"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return ClaudeAnalyzer(claude_cmd="echo")
    
    @pytest.fixture
    def sample_problem(self):
        """Sample math problem for testing"""
        return {
            'raw_text': 'מצא את הנגזרת של f(x) = sin(x)cos(x)',
            'translated_text': 'Find the derivative of f(x) = sin(x)cos(x)',
            'formulas': [{'type': 'function', 'latex': 'f(x) = sin(x)cos(x)'}],
            'difficulty': 3
        }
    
    @pytest.fixture
    def adhd_profile(self):
        """ADHD user profile for testing"""
        return ADHDProfile(
            preferred_step_duration=5,  # 5 minutes per step
            energy_level='medium',
            medication_taken=True,
            time_of_day='afternoon',
            streak_days=7
        )
    
    def test_generates_3_to_7_steps(self, analyzer, sample_problem):
        """Test that analyzer generates appropriate number of steps"""
        mock_response = json.dumps({
            'steps': [
                {
                    'number': 1,
                    'description': 'Identify this as a product rule problem',
                    'duration_minutes': 3,
                    'checkpoint_question': 'What rule applies to derivatives of products?'
                },
                {
                    'number': 2,
                    'description': 'Write the product rule formula',
                    'duration_minutes': 2,
                    'checkpoint_question': 'Can you write d/dx[u·v] = ?'
                },
                {
                    'number': 3,
                    'description': 'Identify u = sin(x) and v = cos(x)',
                    'duration_minutes': 2,
                    'checkpoint_question': 'What are u and v in our problem?'
                },
                {
                    'number': 4,
                    'description': 'Find derivatives: u\' = cos(x), v\' = -sin(x)',
                    'duration_minutes': 5,
                    'checkpoint_question': 'What is d/dx of sin(x)? And cos(x)?'
                },
                {
                    'number': 5,
                    'description': 'Apply the formula: f\'(x) = cos²(x) - sin²(x)',
                    'duration_minutes': 4,
                    'checkpoint_question': 'Can you combine using the product rule?'
                }
            ]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem)
            
            assert isinstance(analysis, ProblemAnalysis)
            assert 3 <= len(analysis.steps) <= 7
            assert all(isinstance(step, StepBreakdown) for step in analysis.steps)
    
    def test_adhd_friendly_step_duration(self, analyzer, sample_problem, adhd_profile):
        """Test that step durations are ADHD-appropriate"""
        mock_response = json.dumps({
            'steps': [
                {'number': 1, 'description': 'Step 1', 'duration_minutes': 5},
                {'number': 2, 'description': 'Step 2', 'duration_minutes': 7},
                {'number': 3, 'description': 'Step 3', 'duration_minutes': 3},
            ]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem, adhd_profile)
            
            # All steps should be 3-10 minutes
            for step in analysis.steps:
                assert 3 <= step.duration_minutes <= 10
                
            # Average should be around preferred duration
            avg_duration = sum(s.duration_minutes for s in analysis.steps) / len(analysis.steps)
            assert 3 <= avg_duration <= 7
    
    def test_socratic_hint_generation(self, analyzer, sample_problem):
        """Test generation of 3-tier Socratic hints"""
        mock_response = json.dumps({
            'steps': [{
                'number': 1,
                'description': 'Apply product rule',
                'duration_minutes': 5,
                'hints': {
                    'tier1': 'What rule do we use for derivatives of products?',
                    'tier2': 'The product rule states: d/dx[u·v] = u\'·v + u·v\'',
                    'tier3': 'Here u = sin(x) and v = cos(x). So f\'(x) = cos(x)·cos(x) + sin(x)·(-sin(x))'
                }
            }]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem)
            
            hints = analysis.steps[0].hints
            assert isinstance(hints, HintSet)
            assert hints.tier1  # Gentle nudge
            assert hints.tier2  # More specific
            assert hints.tier3  # Nearly complete answer
            
            # Verify progressive disclosure
            assert len(hints.tier1) < len(hints.tier2) < len(hints.tier3)
    
    def test_checkpoint_questions(self, analyzer, sample_problem):
        """Test that each step has a checkpoint question"""
        mock_response = json.dumps({
            'steps': [
                {
                    'number': 1,
                    'description': 'Identify the differentiation rule',
                    'duration_minutes': 3,
                    'checkpoint_question': 'Which differentiation rule applies here?'
                },
                {
                    'number': 2,
                    'description': 'Apply the rule',
                    'duration_minutes': 5,
                    'checkpoint_question': 'What is the derivative of sin(x)cos(x)?'
                }
            ]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem)
            
            for step in analysis.steps:
                assert step.checkpoint_question
                assert '?' in step.checkpoint_question  # Should be a question
                assert len(step.checkpoint_question) > 10  # Not too short
    
    def test_json_response_parsing(self, analyzer):
        """Test parsing of Claude's JSON responses"""
        valid_json = json.dumps({
            'analysis': {
                'problem_type': 'derivative',
                'difficulty_rating': 3,
                'concepts': ['product rule', 'trigonometry', 'derivatives'],
                'estimated_time': 15
            },
            'steps': [
                {
                    'number': 1,
                    'description': 'Recognize product rule',
                    'duration_minutes': 5,
                    'checkpoint_question': 'What rule?',
                    'hints': {
                        'tier1': 'Think products',
                        'tier2': 'Product rule formula',
                        'tier3': 'u\'v + uv\''
                    }
                }
            ],
            'summary': 'Apply product rule to find derivative'
        })
        
        analysis = analyzer._parse_response(valid_json)
        
        assert analysis.problem_type == 'derivative'
        assert analysis.difficulty_rating == 3
        assert len(analysis.concepts) == 3
        assert analysis.estimated_time == 15
        assert len(analysis.steps) == 1
    
    def test_timeout_handling(self, analyzer, sample_problem):
        """Test handling of CLI timeouts"""
        
        with patch.object(analyzer, '_run_claude_cli', side_effect=AnalysisError("Claude CLI timeout after 30 seconds")):
            with pytest.raises(AnalysisError) as exc_info:
                analyzer.analyze_problem(sample_problem, timeout=0.05)
            
            assert 'timeout' in str(exc_info.value).lower()
    
    def test_retry_logic(self, analyzer, sample_problem):
        """Test retry logic with exponential backoff"""
        call_count = 0
        
        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary error")
            return json.dumps({'steps': [{'number': 1, 'description': 'Success', 'duration_minutes': 5}]})
        
        with patch.object(analyzer, '_run_claude_cli', side_effect=mock_api_call):
            with patch('time.sleep'):  # Don't actually sleep in tests
                analysis = analyzer.analyze_problem(sample_problem, max_retries=3)
                
                assert call_count == 3  # Failed twice, succeeded on third
                assert len(analysis.steps) == 1
    
    def test_energy_level_adaptation(self, analyzer, sample_problem):
        """Test adaptation based on user energy levels"""
        # Low energy profile
        low_energy = ADHDProfile(energy_level='low', time_of_day='evening')
        
        mock_response = json.dumps({
            'steps': [
                {'number': 1, 'description': 'Very simple step', 'duration_minutes': 3},
                {'number': 2, 'description': 'Another simple step', 'duration_minutes': 3},
                {'number': 3, 'description': 'Final simple step', 'duration_minutes': 3},
            ]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem, low_energy)
            
            # Low energy should result in shorter, simpler steps
            assert all(step.duration_minutes <= 5 for step in analysis.steps)
            assert len(analysis.steps) >= 3  # More but smaller steps
    
    def test_medication_consideration(self, analyzer, sample_problem):
        """Test that medication status affects step complexity"""
        # No medication profile
        no_med = ADHDProfile(medication_taken=False, energy_level='medium')
        
        mock_response = json.dumps({
            'steps': [
                {'number': 1, 'description': 'Clear, simple instruction', 'duration_minutes': 4},
                {'number': 2, 'description': 'Another clear step', 'duration_minutes': 4},
            ]
        })
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = analyzer.analyze_problem(sample_problem, no_med)
            
            # Without medication, steps should be clearer and shorter
            assert all(step.duration_minutes <= 5 for step in analysis.steps)
    
    def test_prompt_template_structure(self, analyzer):
        """Test the structure of prompts sent to Claude"""
        problem = {
            'raw_text': 'Test problem',
            'translated_text': 'Test problem in English',
            'difficulty': 3
        }
        
        profile = ADHDProfile(energy_level='high', medication_taken=True)
        
        prompt = analyzer._build_prompt(problem, profile)
        
        # Check key elements are in prompt
        assert 'ADHD' in prompt
        assert '3-7 steps' in prompt
        assert 'Socratic' in prompt
        assert 'checkpoint' in prompt
        assert 'Energy level: high' in prompt
        assert 'Medication: taken' in prompt
        assert 'JSON' in prompt
    
    def test_caching_mechanism(self, analyzer, sample_problem):
        """Test that responses are cached to avoid duplicate API calls"""
        mock_response = json.dumps({'steps': [{'number': 1, 'description': 'Cached', 'duration_minutes': 5}]})
        
        with patch.object(analyzer, '_run_claude_cli', return_value=mock_response) as mock_api:
            # First call
            analysis1 = analyzer.analyze_problem(sample_problem)
            # Second call with same problem
            analysis2 = analyzer.analyze_problem(sample_problem)
            
            # API should only be called once due to caching
            assert mock_api.call_count == 1
            assert analysis1.steps[0].description == analysis2.steps[0].description
    
    def test_error_recovery(self, analyzer, sample_problem):
        """Test graceful error recovery"""
        # Invalid response structure
        invalid_response = json.dumps({'invalid': 'structure'})
        
        with patch.object(analyzer, '_run_claude_cli', return_value=invalid_response):
            with pytest.raises(AnalysisError) as exc_info:
                analyzer.analyze_problem(sample_problem)
            
            assert 'parsing' in str(exc_info.value).lower()


class TestProblemAnalysis:
    """Test ProblemAnalysis data structure"""
    
    def test_problem_analysis_creation(self):
        """Test creation of ProblemAnalysis object"""
        steps = [
            StepBreakdown(
                number=1,
                description="First step",
                duration_minutes=5,
                checkpoint_question="Got it?",
                hints=HintSet(
                    tier1="Hint 1",
                    tier2="Hint 2", 
                    tier3="Hint 3"
                )
            )
        ]
        
        analysis = ProblemAnalysis(
            problem_type="derivative",
            difficulty_rating=3,
            concepts=["calculus", "product rule"],
            estimated_time=15,
            steps=steps,
            summary="Find derivative using product rule"
        )
        
        assert analysis.problem_type == "derivative"
        assert analysis.difficulty_rating == 3
        assert len(analysis.concepts) == 2
        assert analysis.estimated_time == 15
        assert len(analysis.steps) == 1
        assert analysis.summary
    
    def test_step_breakdown_validation(self):
        """Test StepBreakdown validation"""
        # Valid step
        step = StepBreakdown(
            number=1,
            description="Valid step",
            duration_minutes=5,
            checkpoint_question="Question?",
            hints=HintSet(tier1="H1", tier2="H2", tier3="H3")
        )
        assert step.is_valid()
        
        # Invalid duration
        with pytest.raises(ValueError):
            StepBreakdown(
                number=1,
                description="Invalid",
                duration_minutes=15,  # Too long
                checkpoint_question="Question?"
            )
    
    def test_hint_set_progression(self):
        """Test that hints show progressive disclosure"""
        hints = HintSet(
            tier1="What rule?",
            tier2="The product rule: d/dx[uv] = u'v + uv'",
            tier3="Here u=sin(x), v=cos(x), so f'(x) = cos(x)cos(x) + sin(x)(-sin(x))"
        )
        
        assert len(hints.tier1) < len(hints.tier2) < len(hints.tier3)
        assert hints.get_hint(1) == hints.tier1
        assert hints.get_hint(2) == hints.tier2
        assert hints.get_hint(3) == hints.tier3
        assert hints.get_hint(4) == hints.tier3  # Max out at tier 3


class TestADHDProfile:
    """Test ADHD profile handling"""
    
    def test_profile_defaults(self):
        """Test default ADHD profile values"""
        profile = ADHDProfile()
        
        assert profile.preferred_step_duration == 5
        assert profile.energy_level == 'medium'
        assert profile.medication_taken is None
        assert profile.time_of_day == 'afternoon'
        assert profile.streak_days == 0
    
    def test_profile_from_time(self):
        """Test profile creation based on time of day"""
        morning_profile = ADHDProfile.from_current_time(
            current_time=time(9, 0)  # 9 AM
        )
        assert morning_profile.time_of_day == 'morning'
        
        evening_profile = ADHDProfile.from_current_time(
            current_time=time(20, 0)  # 8 PM
        )
        assert evening_profile.time_of_day == 'evening'
    
    def test_profile_adjustments(self):
        """Test profile-based adjustments"""
        # High energy, medicated, long streak
        optimal = ADHDProfile(
            energy_level='high',
            medication_taken=True,
            streak_days=30
        )
        assert optimal.get_complexity_multiplier() > 1.0
        
        # Low energy, no meds, no streak
        suboptimal = ADHDProfile(
            energy_level='low',
            medication_taken=False,
            streak_days=0
        )
        assert suboptimal.get_complexity_multiplier() < 1.0


class TestIntegration:
    """Integration tests for the full analysis pipeline"""
    
    @pytest.fixture
    def full_analyzer(self):
        """Create fully configured analyzer"""
        return ClaudeAnalyzer(
            claude_cmd="echo",
            cache_enabled=True,
            timeout=30
        )
    
    def test_full_analysis_pipeline(self, full_analyzer):
        """Test complete analysis from problem to structured output"""
        problem = {
            'raw_text': 'חשב את האינטגרל ∫₀^π sin²(x)dx',
            'translated_text': 'Calculate the integral ∫₀^π sin²(x)dx',
            'formulas': [{'type': 'integral', 'latex': '\\int_0^\\pi \\sin^2(x)dx'}],
            'difficulty': 4
        }
        
        profile = ADHDProfile(
            energy_level='medium',
            medication_taken=True,
            preferred_step_duration=6,
            streak_days=10
        )
        
        mock_response = json.dumps({
            'analysis': {
                'problem_type': 'definite_integral',
                'difficulty_rating': 4,
                'concepts': ['integration', 'trigonometry', 'power reduction'],
                'estimated_time': 20
            },
            'steps': [
                {
                    'number': 1,
                    'description': 'Recognize this needs the power reduction formula',
                    'duration_minutes': 4,
                    'checkpoint_question': 'What identity can we use for sin²(x)?',
                    'hints': {
                        'tier1': 'Is there a way to rewrite sin²(x)?',
                        'tier2': 'Try the power reduction formula: sin²(x) = (1 - cos(2x))/2',
                        'tier3': 'Substitute sin²(x) = (1 - cos(2x))/2 into the integral'
                    }
                },
                {
                    'number': 2,
                    'description': 'Rewrite using the identity',
                    'duration_minutes': 5,
                    'checkpoint_question': 'Can you rewrite the integral using the identity?',
                    'hints': {
                        'tier1': 'Substitute the power reduction formula',
                        'tier2': '∫₀^π sin²(x)dx = ∫₀^π (1 - cos(2x))/2 dx',
                        'tier3': '= (1/2)∫₀^π dx - (1/2)∫₀^π cos(2x)dx'
                    }
                },
                {
                    'number': 3,
                    'description': 'Integrate each term separately',
                    'duration_minutes': 6,
                    'checkpoint_question': 'What is ∫dx and ∫cos(2x)dx?',
                    'hints': {
                        'tier1': 'These are basic integrals',
                        'tier2': '∫dx = x and ∫cos(2x)dx = (1/2)sin(2x)',
                        'tier3': 'Don\'t forget the bounds: evaluate from 0 to π'
                    }
                },
                {
                    'number': 4,
                    'description': 'Evaluate at the bounds',
                    'duration_minutes': 5,
                    'checkpoint_question': 'What do you get when you plug in π and 0?',
                    'hints': {
                        'tier1': 'Evaluate each term at π and at 0',
                        'tier2': 'sin(2π) = 0 and sin(0) = 0',
                        'tier3': 'Final answer: (1/2)[π - 0] - (1/2)[0 - 0] = π/2'
                    }
                }
            ],
            'summary': 'Use power reduction formula to convert sin²(x), then integrate'
        })
        
        with patch.object(full_analyzer, '_run_claude_cli', return_value=mock_response):
            analysis = full_analyzer.analyze_problem(problem, profile)
            
            # Verify complete analysis
            assert analysis.problem_type == 'definite_integral'
            assert analysis.difficulty_rating == 4
            assert len(analysis.steps) == 4
            assert analysis.estimated_time == 20
            
            # Check ADHD adaptations
            total_time = sum(s.duration_minutes for s in analysis.steps)
            assert 15 <= total_time <= 25  # Reasonable total time
            
            # Verify each step
            for i, step in enumerate(analysis.steps):
                assert step.number == i + 1
                assert step.checkpoint_question
                assert step.hints.tier1
                assert step.hints.tier2
                assert step.hints.tier3