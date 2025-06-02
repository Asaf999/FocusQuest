# FocusQuest Development Guidelines

## Build Commands
- Run: `python src/main.py`
- Test: `pytest tests/ -v`
- Process PDF: Auto-handled by watcher

## Mathematical Analysis Preferences
- Break problems into 3-7 ADHD-friendly steps
- Each step: 3-10 minutes max
- Single checkbox focus
- 3-tier Socratic hints

## Code Standards
- Type hints required
- Tests BEFORE implementation
- Hebrew → English translation pipeline
- SQLAlchemy for database

## GitHub Workflow
- After completing EACH phase or major feature:
  1. Run all tests: `pytest tests/ -v`
  2. Stage changes: `git add .`
  3. Commit with descriptive message:
     ```bash
     git commit -m "Phase X complete: [specific accomplishments]
     
     - List specific features implemented
     - Note test coverage added
     - Document any architecture decisions"
     ```
  4. Push to GitHub: `git push origin main`
  5. Update MASTER_PLAN.md progress before moving to next phase
- NEVER proceed to next phase without committing current work
- Each commit should be a working state with passing tests

## Claude Code Runtime Integration
- File watcher on /inbox
- Automatic prompt generation
- No user intervention during runtime
- Uses Claude Code CLI (FREE with Pro) instead of API
- Subprocess-based integration with `claude` command
- CLAUDE_AUTO_ACCEPT=true for autonomous operation
- No API costs - saves $45/month

## Project Overview
FocusQuest is an ADHD-optimized math learning RPG designed for Tel Aviv University students. The system automatically processes Hebrew PDFs containing mathematical content, analyzes problems using Claude Code as a runtime AI engine, and presents them in a gamified, focus-friendly interface.

## Technical Stack
- **OS**: Arch Linux with i3 window manager
- **Language**: Python 3.10+
- **GUI**: PyQt6 (optimized for i3 compatibility)
- **PDF Processing**: pdfplumber + pytesseract
- **Database**: SQLAlchemy
- **Testing**: pytest
- **AI Integration**: Claude Code CLI for problem analysis (FREE with Pro subscription)

## Directory Structure
```
focusquest/
├── CLAUDE.md (this file - persistent context)
├── MASTER_PLAN.md (progress tracking)
├── requirements.txt
├── .gitignore
├── src/
│   ├── main.py
│   ├── pdf_processor.py
│   ├── problem_analyzer.py
│   ├── game_engine.py
│   ├── ui/
│   └── models/
├── tests/
├── inbox/ (watched folder for PDFs)
├── processed/ (archived PDFs)
└── data/ (SQLite database and assets)
```

## Key Features
1. **Automatic PDF Processing**
   - Watch /inbox directory for new PDFs
   - Extract Hebrew text and mathematical formulas
   - Preserve formula structure and layout
   - Move processed files to /processed

2. **Problem Analysis Pipeline**
   - Hebrew to English translation
   - Mathematical notation preservation
   - Problem decomposition into ADHD-friendly steps
   - Difficulty assessment and categorization

3. **ADHD Optimizations**
   - Chunked content (3-7 steps per problem)
   - Time-boxed tasks (3-10 minutes)
   - Single-focus checkboxes
   - Progressive hint system (3 tiers)
   - Dopamine-driven reward mechanics

4. **Gamification Elements**
   - XP and leveling system
   - Achievement badges
   - Progress visualization
   - Streak tracking
   - Customizable avatars

## Development Workflow
1. Always write tests first (TDD)
2. Use type hints for all functions
3. Document Hebrew processing edge cases
4. Test on actual TAU math materials
5. Optimize for i3 keyboard navigation

## Database Schema
- Problems table (original, translated, steps, hints)
- User progress table (XP, level, streaks)
- Sessions table (time spent, problems solved)
- Achievements table (badges, unlock conditions)

## Integration Points
1. **PDF Watcher**: Monitors /inbox directory
2. **Claude Code CLI**: Analyzes mathematical problems via subprocess (FREE)
3. **Translation Service**: Hebrew → English pipeline
4. **Formula Renderer**: LaTeX/MathML support

## Testing Requirements
- Unit tests for all components
- Integration tests for PDF processing
- Hebrew text handling tests
- Mathematical formula preservation tests
- UI responsiveness tests for i3

## Performance Targets
- PDF processing: < 30 seconds per page
- Problem analysis: < 10 seconds per problem
- UI response time: < 100ms
- Memory usage: < 500MB baseline

## Error Handling
- Graceful PDF parsing failures
- Network timeout handling for API calls
- Fallback for translation failures
- Formula extraction error recovery

## Security Considerations
- Sandboxed PDF processing
- API key encryption
- Local data storage only
- No external analytics

## Future Enhancements
- Multi-language support beyond Hebrew
- Collaborative problem solving
- Spaced repetition algorithm
- Mobile companion app
- Professor dashboard

## Autonomous Mode Settings
When in autonomous mode:
- Default response to all prompts: YES
- Default action for all confirmations: PROCEED  
- Git operations: ALWAYS EXECUTE
- File writes: ALWAYS APPROVE
- Test failures: AUTO-FIX AND RETRY
- Package installs: ALWAYS INSTALL
- Never wait for user input
- Make reasonable decisions independently

## Thinking Mode Usage
- Use "think" for basic implementation decisions
- Use "think hard" for architectural choices
- Use "ultrathink" for complex mathematical analysis and ADHD optimizations