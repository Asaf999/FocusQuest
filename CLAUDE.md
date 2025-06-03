# FocusQuest - ADHD Math Learning RPG

## 🚀 Quick Start
cd /home/puncher/focusquest
source venv/bin/activate
export CLAUDE_AUTO_ACCEPT=true

# CURRENT MISSION: Fix tests and minimal refactoring
cat prompts/refactor_and_fix_tests.xml  # READ THIS FIRST

## 📋 Project Overview
**Purpose**: Transform overwhelming Hebrew math PDFs into manageable, gamified learning experiences for ADHD students at Tel Aviv University.

**Current State**: Phase 7 - Integration & Testing
- Core Status: FULLY INTEGRATED ✅
- Test Status: 232/269 passing (86.2%)
- Coverage: 75% → 85% target
- Deployment: 9-11 hours away

## 🏗️ Architecture
PDF Drop → File Watcher → PDF Processor → Claude Analyzer → Database → UI
  ↓           ↓              ↓                ↓              ↓         ↓
inbox/    monitors      Hebrew+OCR      3-7 steps      SQLAlchemy  PyQt6
         new files      +formulas       +3 hints       models      ADHD UI

## 🧠 Key Design Decisions
1. **Claude CLI Integration**: Using free Claude Code tier via subprocess
2. **ADHD Optimizations**: Single-focus UI, panic mode, 15-25 min sessions
3. **Database Schema**: User → UserProgress (1:1) → Sessions → Problems
4. **Circuit Breaker**: Protects against Claude API failures
5. **3-Tier Hints**: Socratic method for progressive learning

## 📁 Project Structure
src/
├── analysis/         # PDF processing + Claude AI integration
├── core/            # Business logic, file watching, state sync
├── database/        # SQLAlchemy models and persistence
├── ui/              # PyQt6 windows and widgets
└── utils/           # Shared utilities

tests/
├── unit/            # Pure logic tests (fast)
├── integration/     # Database/file system tests
├── e2e/            # Full workflow and GUI tests
└── conftest.py     # Shared fixtures

## 🎯 Current Focus: Fix Tests & Minimal Refactoring

### Test Failures Root Causes:
1. **Database UI Sync (11 errors)**: Tests expect User.level, actual uses User.progress.level
2. **Circuit Breaker (8 failures)**: Tests expect dict, actual returns ProblemAnalysis object  
3. **Skip Problem (8 failures)**: Tests use old API (current_problem_id vs current_problem)
4. **GUI Tests (4 failures)**: Segfaults without proper Qt lifecycle
5. **State Sync (8 failures)**: Direct User field access instead of User.progress

### Quick Fix Commands:
# Fix one test at a time
pytest --lf -x -vs

# Run specific test category
pytest tests/test_database_ui_sync.py -xvs
pytest tests/test_circuit_breaker.py -xvs

# Check coverage
pytest --cov=src --cov-report=term-missing | grep TOTAL

# GUI tests with proper setup
xvfb-run -a pytest tests/e2e -m gui -v

## 🛠️ Common Tasks

### Adding New Problem Type
1. Update src/analysis/pdf_processor.py for extraction
2. Modify src/analysis/claude_analyzer.py prompts
3. Add database migration if needed
4. Create tests in tests/unit/

### Debugging Failed PDF
1. Check logs in data/failed/
2. Run manual extraction: python -m src.analysis.pdf_processor <pdf_path>
3. Test Claude analysis: python -m src.analysis.claude_analyzer <problem_text>

### Testing ADHD Features
# Panic mode
python -m focusquest  # Then press Ctrl+Shift+P

# Session timing
pytest tests/integration/test_session_manager.py -v

# Skip functionality  
pytest tests/e2e/test_skip_problem.py -v

## 🔧 Configuration
All settings in src/config.py (or create one):
- ADHD: session_duration_min, break_duration_min, panic_mode_key
- Claude: timeout_seconds, max_retries, circuit_breaker_threshold
- Processing: inbox_dir, processed_dir, failed_dir

Environment variables:
- ADHD_SESSION_MIN (default: 20)
- ADHD_DARK_THEME (default: true)
- DEBUG (default: false)
- DATABASE_URL (default: sqlite:///data/focusquest.db)

## 📊 Performance Targets
- Startup: <3 seconds ✅
- UI Response: <100ms ✅  
- PDF Processing: ~30s/page ✅
- Memory Usage: <500MB ✅
- Test Coverage: 85% ⚠️
- All Tests Pass: 100% ❌

## 🚦 Deployment Checklist
□ All 269 tests passing
□ Coverage ≥ 85%
□ 4-hour stability test passed
□ Memory leak verification done
□ User documentation complete
□ Installation guide written
□ GitHub release prepared

## 🎮 ADHD Features Checklist
✅ Single-focus interface (one problem visible)
✅ Session timers (15-25 minutes)
✅ Break enforcement system
✅ Panic mode (Ctrl+Shift+P)
✅ Progressive hint system (3 tiers)
✅ Minimal UI chrome
✅ Keyboard navigation
✅ Quick feedback loops
✅ Progress persistence
✅ Skip with spaced repetition

## 📚 Key Files Reference
- Entry point: src/__main__.py (needs creation)
- Config: src/config.py (needs creation)
- Main window: src/ui/main_window.py (needs consolidation)
- Test fixtures: tests/conftest.py (needs update)
- Claude analyzer: src/analysis/claude_analyzer.py
- PDF processor: src/analysis/pdf_processor.py
- Database models: src/database/models.py

## 🔍 Research Commands
# Understand current structure
find src/ -name "*.py" | grep -E "(main|window)" | sort
find tests/ -name "test_fix*.py" | xargs wc -l

# Check test failures
pytest tests/test_database_ui_sync.py -k "initializes" -xvs
pytest tests/test_circuit_breaker.py -k "transitions" -xvs

# Find scattered config
grep -r "session_duration\|break_duration" src/ --include="*.py"

# Memory profiling
mprof run python -m focusquest --headless
mprof plot

## 💡 Implementation Notes
1. The code is MORE mature than the tests - don't refactor working code
2. UserProgress separation is GOOD architecture, tests need updating
3. Circuit breaker returning objects is CORRECT, tests are wrong
4. GUI needs proper Qt app lifecycle in tests
5. Keep PDF processing, Claude analyzer, and ADHD features AS IS

## 🎯 Mission Prompts
For complex tasks, read the appropriate prompt file:
- Refactoring & Test Fixes: cat prompts/refactor_and_fix_tests.xml
- Architecture Analysis: cat prompts/analyze_architecture.xml
- Deployment Prep: cat prompts/prepare_deployment.xml
- Performance Optimization: cat prompts/optimize_performance.xml

## 📞 Quick Actions
# Start fresh
git checkout -b fix/test-infrastructure
source venv/bin/activate

# Run the app
python src/main_with_watcher.py  # Current working entry

# Quick test
pytest tests/test_pdf_processor.py -v  # This one works

# See what's failing
pytest --lf --tb=short

# After fixing tests
git add -A && git commit -m "Test: Fix [specific issue]"
git push origin fix/test-infrastructure