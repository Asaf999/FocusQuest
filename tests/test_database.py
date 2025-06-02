"""
Comprehensive database tests for FocusQuest
Tests all database models and operations following TDD principles
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.database.models import (
    Base, Problem, ProblemStep, Hint, User, UserProgress,
    Session, Achievement, UserAchievement, ProblemAttempt
)


class TestDatabaseSetup:
    """Test database setup and configuration"""
    
    @pytest.fixture
    def engine(self):
        """Create an in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        """Create a database session for testing"""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_all_tables(self, engine):
        """Test that all tables are created successfully"""
        table_names = Base.metadata.tables.keys()
        expected_tables = {
            'problems', 'problem_steps', 'hints', 'users',
            'user_progress', 'sessions', 'achievements',
            'user_achievements', 'problem_attempts'
        }
        assert expected_tables.issubset(table_names)


class TestProblemModel:
    """Test Problem model and related operations"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_create_problem(self, session):
        """Test creating a basic problem"""
        problem = Problem(
            original_text="מצא את הגבול של x²+3x כאשר x שואף ל-2",
            translated_text="Find the limit of x²+3x as x approaches 2",
            difficulty=3,
            category="calculus",
            pdf_source="calculus_101.pdf",
            page_number=15
        )
        session.add(problem)
        session.commit()
        
        assert problem.id is not None
        assert problem.created_at is not None
        assert problem.difficulty == 3
        assert problem.category == "calculus"
    
    def test_problem_with_steps(self, session):
        """Test creating a problem with multiple steps"""
        problem = Problem(
            original_text="חשב את האינטגרל של sin(x)cos(x)",
            translated_text="Calculate the integral of sin(x)cos(x)",
            difficulty=4,
            category="calculus"
        )
        session.add(problem)
        session.commit()
        
        # Add 5 ADHD-friendly steps
        steps = [
            ProblemStep(
                problem_id=problem.id,
                step_number=1,
                description="Identify the integration technique needed",
                explanation="This is a product of trig functions - consider substitution or identity",
                time_estimate=3
            ),
            ProblemStep(
                problem_id=problem.id,
                step_number=2,
                description="Apply the double angle identity",
                explanation="sin(x)cos(x) = (1/2)sin(2x)",
                time_estimate=5
            ),
            ProblemStep(
                problem_id=problem.id,
                step_number=3,
                description="Integrate (1/2)sin(2x)",
                explanation="Use the basic integral of sin(u) with u=2x",
                time_estimate=5
            ),
            ProblemStep(
                problem_id=problem.id,
                step_number=4,
                description="Apply chain rule in reverse",
                explanation="Don't forget to divide by the derivative of 2x",
                time_estimate=3
            ),
            ProblemStep(
                problem_id=problem.id,
                step_number=5,
                description="Add the constant of integration",
                explanation="Final answer: -(1/4)cos(2x) + C",
                time_estimate=2
            )
        ]
        
        for step in steps:
            session.add(step)
        session.commit()
        
        # Verify steps were created
        assert len(problem.steps) == 5
        assert problem.steps[0].step_number == 1
        assert problem.steps[4].time_estimate == 2
        
        # Test step ordering
        for i, step in enumerate(problem.steps):
            assert step.step_number == i + 1
    
    def test_problem_validation(self, session):
        """Test problem validation constraints"""
        # Test difficulty out of range
        with pytest.raises(ValueError):
            problem = Problem(
                original_text="Test",
                difficulty=6,  # Should be 1-5
                category="test"
            )
            session.add(problem)
            session.commit()


class TestHintSystem:
    """Test the 3-tier Socratic hint system"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def problem_with_step(self, session):
        """Create a problem with one step for hint testing"""
        problem = Problem(
            original_text="מצא את הנגזרת של x³+2x",
            translated_text="Find the derivative of x³+2x",
            difficulty=2,
            category="calculus"
        )
        session.add(problem)
        session.commit()
        
        step = ProblemStep(
            problem_id=problem.id,
            step_number=1,
            description="Apply power rule to each term",
            explanation="Derivative of x^n is nx^(n-1)",
            time_estimate=5
        )
        session.add(step)
        session.commit()
        
        return problem, step
    
    def test_three_tier_hints(self, session, problem_with_step):
        """Test creating 3-tier Socratic hints for a step"""
        problem, step = problem_with_step
        
        hints = [
            Hint(
                step_id=step.id,
                level=1,
                content="What is the general rule for finding derivatives of power functions?",
                xp_penalty=5
            ),
            Hint(
                step_id=step.id,
                level=2,
                content="For x^n, the derivative is nx^(n-1). Apply this to x³ and 2x separately.",
                xp_penalty=10
            ),
            Hint(
                step_id=step.id,
                level=3,
                content="x³ becomes 3x², and 2x becomes 2. The answer is 3x² + 2.",
                xp_penalty=15
            )
        ]
        
        for hint in hints:
            session.add(hint)
        session.commit()
        
        # Verify hints
        assert len(step.hints) == 3
        assert step.hints[0].level == 1
        assert step.hints[0].xp_penalty == 5
        assert step.hints[2].level == 3
        assert step.hints[2].xp_penalty == 15
    
    def test_hint_uniqueness(self, session, problem_with_step):
        """Test that hints must have unique levels per step"""
        problem, step = problem_with_step
        
        hint1 = Hint(step_id=step.id, level=1, content="First hint", xp_penalty=5)
        hint2 = Hint(step_id=step.id, level=1, content="Duplicate level", xp_penalty=5)
        
        session.add(hint1)
        session.commit()
        
        session.add(hint2)
        with pytest.raises(IntegrityError):
            session.commit()


class TestUserProgress:
    """Test user progress tracking and gamification"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def user(self, session):
        """Create a test user"""
        user = User(
            username="test_student",
            email="student@tau.ac.il",
            medication_reminder=True,
            preferred_session_length=25  # minutes
        )
        session.add(user)
        session.commit()
        return user
    
    def test_user_progress_initialization(self, session, user):
        """Test initial user progress creation"""
        progress = UserProgress(
            user_id=user.id,
            total_xp=0,
            level=1,
            current_streak=0,
            longest_streak=0,
            problems_solved=0,
            total_time_minutes=0
        )
        session.add(progress)
        session.commit()
        
        assert progress.id is not None
        assert progress.level == 1
        assert progress.total_xp == 0
    
    def test_xp_and_leveling(self, session, user):
        """Test XP gain and automatic leveling"""
        progress = UserProgress(user_id=user.id)
        session.add(progress)
        session.commit()
        
        # Simulate solving problems and gaining XP
        progress.add_xp(50)  # First problem
        assert progress.total_xp == 50
        assert progress.level == 1
        
        progress.add_xp(60)  # Second problem
        assert progress.total_xp == 110
        assert progress.level == 2  # Should level up at 100 XP
        
        progress.add_xp(200)  # Big problem
        assert progress.total_xp == 310
        assert progress.level == 4  # Should be level 4 (310 // 100 + 1)
    
    def test_streak_tracking(self, session, user):
        """Test streak tracking for consecutive days"""
        progress = UserProgress(user_id=user.id)
        session.add(progress)
        session.commit()
        
        # Day 1
        progress.update_streak(datetime.now())
        assert progress.current_streak == 1
        assert progress.longest_streak == 1
        
        # Day 2 (consecutive)
        progress.update_streak(datetime.now() + timedelta(days=1))
        assert progress.current_streak == 2
        assert progress.longest_streak == 2
        
        # Day 4 (break in streak)
        progress.update_streak(datetime.now() + timedelta(days=3))
        assert progress.current_streak == 1
        assert progress.longest_streak == 2  # Longest remains 2


class TestSessionTracking:
    """Test study session tracking and analytics"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def user(self, session):
        user = User(username="test_user")
        session.add(user)
        session.commit()
        return user
    
    def test_session_creation(self, session, user):
        """Test creating and tracking a study session"""
        study_session = Session(
            user_id=user.id,
            start_time=datetime.now(),
            medication_taken=True,
            initial_focus_level=4  # 1-5 scale
        )
        session.add(study_session)
        session.commit()
        
        assert study_session.id is not None
        assert study_session.medication_taken is True
        assert study_session.end_time is None  # Not ended yet
    
    def test_session_completion(self, session, user):
        """Test completing a session with metrics"""
        start = datetime.now()
        study_session = Session(
            user_id=user.id,
            start_time=start,
            medication_taken=False
        )
        session.add(study_session)
        session.commit()
        
        # Simulate session end
        end = start + timedelta(minutes=25)
        study_session.end_session(
            end_time=end,
            problems_attempted=5,
            problems_solved=4,
            xp_earned=85,
            final_focus_level=3
        )
        session.commit()
        
        assert study_session.end_time == end
        assert study_session.duration_minutes == 25
        assert study_session.problems_solved == 4
        assert study_session.success_rate == 0.8  # 4/5


class TestAchievementSystem:
    """Test achievement/badge system"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_achievement_creation(self, session):
        """Test creating achievements"""
        achievements = [
            Achievement(
                name="First Steps",
                description="Complete your first problem",
                icon="🎯",
                xp_reward=10,
                requirement_type="problems_solved",
                requirement_value=1
            ),
            Achievement(
                name="Week Warrior",
                description="Maintain a 7-day streak",
                icon="🔥",
                xp_reward=50,
                requirement_type="streak_days",
                requirement_value=7
            ),
            Achievement(
                name="Calculus Master",
                description="Solve 50 calculus problems",
                icon="∫",
                xp_reward=100,
                requirement_type="category_problems",
                requirement_value=50,
                category="calculus"
            )
        ]
        
        for achievement in achievements:
            session.add(achievement)
        session.commit()
        
        assert len(session.query(Achievement).all()) == 3
        calc_achievement = session.query(Achievement).filter_by(
            name="Calculus Master"
        ).first()
        assert calc_achievement.category == "calculus"


class TestProblemAttempts:
    """Test problem attempt tracking for analytics"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def setup_data(self, session):
        """Create user and problem for testing"""
        user = User(username="test_user")
        problem = Problem(
            original_text="Test problem",
            difficulty=3,
            category="algebra"
        )
        session.add_all([user, problem])
        session.commit()
        return user, problem
    
    def test_problem_attempt_tracking(self, session, setup_data):
        """Test tracking individual problem attempts"""
        user, problem = setup_data
        
        attempt = ProblemAttempt(
            user_id=user.id,
            problem_id=problem.id,
            session_id=None,  # Can be null if not in a session
            started_at=datetime.now(),
            completed=False,
            hints_used=0
        )
        session.add(attempt)
        session.commit()
        
        # Complete the attempt
        attempt.complete_attempt(
            success=True,
            time_spent=timedelta(minutes=8),
            hints_used=2,
            xp_earned=25
        )
        session.commit()
        
        assert attempt.completed is True
        assert attempt.success is True
        assert attempt.time_spent_seconds == 480  # 8 minutes
        assert attempt.hints_used == 2
        assert attempt.xp_earned == 25


class TestDatabaseIntegration:
    """Integration tests for complex database operations"""
    
    @pytest.fixture
    def engine(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def session(self, engine):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    def test_full_problem_solving_flow(self, session):
        """Test the complete flow of a user solving a problem"""
        # Create user
        user = User(username="integration_test", email="test@tau.ac.il")
        session.add(user)
        session.commit()
        
        # Create user progress
        progress = UserProgress(user_id=user.id, total_xp=50, level=1)
        session.add(progress)
        session.commit()
        
        # Create problem with steps
        problem = Problem(
            original_text="אינטגרל מורכב",
            translated_text="Complex integral",
            difficulty=4,
            category="calculus"
        )
        session.add(problem)
        session.commit()
        
        # Add a step
        step = ProblemStep(
            problem_id=problem.id,
            step_number=1,
            description="Set up the integral",
            time_estimate=5
        )
        session.add(step)
        session.commit()
        
        # Start a session
        study_session = Session(
            user_id=user.id,
            start_time=datetime.now(),
            medication_taken=True
        )
        session.add(study_session)
        session.commit()
        
        # Create problem attempt
        attempt = ProblemAttempt(
            user_id=user.id,
            problem_id=problem.id,
            session_id=study_session.id,
            started_at=datetime.now()
        )
        session.add(attempt)
        session.commit()
        
        # Complete attempt successfully
        attempt.complete_attempt(
            success=True,
            time_spent=timedelta(minutes=12),
            hints_used=1,
            xp_earned=35
        )
        
        # Update user progress
        progress.add_xp(35)
        progress.problems_solved += 1
        progress.total_time_minutes += 12
        
        session.commit()
        
        # Verify final state
        assert progress.total_xp == 85
        assert progress.problems_solved == 1
        assert attempt.success is True
        assert attempt.xp_earned == 35