# FocusQuest Master Development Plan

## Project Status: INITIATED
**Start Date**: January 6, 2025  
**Target MVP**: 4 weeks  
**Current Phase**: Project Setup

## Vision
Create an ADHD-optimized math learning RPG that automatically processes Hebrew mathematics PDFs from Tel Aviv University courses, analyzes problems using Claude Code, and presents them in a gamified, focus-friendly interface.

## Core Innovation
Using Claude Code as a runtime AI engine for automated mathematical problem analysis without user intervention.

## Development Phases

### Phase 1: Foundation (Week 1) ✅ IN PROGRESS
- [x] Project structure setup
- [x] CLAUDE.md documentation
- [x] Development environment
- [ ] Basic PDF processing pipeline
- [ ] Hebrew text extraction proof-of-concept
- [ ] Database schema design
- [ ] Initial test suite

### Phase 2: Core Processing (Week 2)
- [ ] PDF watcher implementation
- [ ] Hebrew → English translation pipeline
- [ ] Mathematical formula extraction
- [ ] Problem analysis integration with Claude Code
- [ ] Database models with SQLAlchemy
- [ ] Comprehensive test coverage

### Phase 3: Game Engine (Week 3)
- [ ] Problem decomposition algorithm (3-7 steps)
- [ ] Hint generation system (3 tiers)
- [ ] XP and leveling mechanics
- [ ] Achievement system
- [ ] Session tracking
- [ ] Game state persistence

### Phase 4: UI Development (Week 4)
- [ ] PyQt6 main window for i3
- [ ] Problem presentation interface
- [ ] Progress visualization
- [ ] Keyboard navigation optimization
- [ ] Dark theme for focus
- [ ] Responsive layout

### Phase 5: Integration & Polish (Post-MVP)
- [ ] Full Claude Code API integration
- [ ] Performance optimization
- [ ] Error handling refinement
- [ ] User preferences system
- [ ] Export/import functionality
- [ ] Documentation completion

## Technical Milestones

### Milestone 1: PDF Processing Pipeline ⏳
**Target**: End of Week 1
- Successful extraction of Hebrew text from TAU math PDFs
- Mathematical formula preservation
- Automated file watching and processing

### Milestone 2: Problem Analysis System
**Target**: End of Week 2
- Claude Code integration for problem analysis
- Reliable Hebrew → English translation
- Problem difficulty assessment

### Milestone 3: Gamification Core
**Target**: End of Week 3
- Working XP/leveling system
- Achievement unlocking
- Progress persistence

### Milestone 4: Playable MVP
**Target**: End of Week 4
- Complete user flow from PDF → processed problems
- Basic but functional UI
- Core ADHD optimizations implemented

## Success Metrics
- PDF processing accuracy: >95%
- Problem analysis success rate: >90%
- User session length: 15-30 minutes (ADHD-optimal)
- Time to process single problem: <10 seconds
- Memory footprint: <500MB

## Risk Mitigation
1. **Hebrew OCR Challenges**
   - Fallback: Manual correction interface
   - Mitigation: Multiple OCR engines

2. **Mathematical Formula Extraction**
   - Fallback: LaTeX template matching
   - Mitigation: Pre-built formula database

3. **Claude Code API Limits**
   - Fallback: Local caching system
   - Mitigation: Batch processing

4. **i3/PyQt6 Compatibility**
   - Fallback: Terminal UI option
   - Mitigation: Extensive testing on Arch

## Current TODO Priority
1. Complete environment setup
2. Implement basic PDF text extraction
3. Test Hebrew processing capabilities
4. Design database schema
5. Create initial test suite

## Progress Log

### January 6, 2025
- ✅ Created project structure
- ✅ Wrote comprehensive CLAUDE.md
- ✅ Created MASTER_PLAN.md
- 🔄 Setting up development environment

## Next Actions
- Create requirements.txt with all dependencies
- Initialize git repository
- Set up Python virtual environment
- Install required packages
- Create initial test structure
- Implement basic PDF watcher

## Notes
- Focus on TDD approach throughout
- Prioritize ADHD-friendly features
- Keep Hebrew processing pipeline simple initially
- Test with real TAU mathematics materials early