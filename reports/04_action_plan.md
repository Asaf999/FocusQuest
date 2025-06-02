# Phase 6.5 Comprehensive Action Plan

## Critical Fixes (Block Phase 7)

### Fix 1: ADHD Panic Button Implementation
- **Files**: src/ui/main_window.py, src/ui/styles.py
- **Issue**: No escape route when overwhelmed, forces crash-quit
- **Fix**: Global ESC+P shortcut, calming overlay screen, pause all timers
- **Tests**: tests/test_panic_button.py
- **Time**: 2 hours
- **Validation**: Trigger panic mode, verify timers pause, test resume

### Fix 2: Thread Safety in FileWatcher
- **Files**: src/core/file_watcher.py
- **Issue**: Race condition when multiple PDFs processed, can lose files
- **Fix**: Add queue between watchdog thread and processors, proper synchronization
- **Tests**: tests/test_file_watcher_concurrency.py
- **Time**: 2 hours  
- **Validation**: Upload 10 PDFs simultaneously, verify none lost

### Fix 3: Graceful Shutdown & Crash Recovery
- **Files**: src/main.py, src/ui/session_manager.py
- **Issue**: Data loss on Ctrl+C, no recovery after crash
- **Fix**: Signal handlers, periodic state snapshots, startup recovery
- **Tests**: tests/test_crash_recovery.py
- **Time**: 3 hours
- **Validation**: Kill -9 process, restart, verify state restored

### Fix 4: Memory Leak Prevention
- **Files**: src/analysis/pdf_processor.py, src/analysis/claude_analyzer.py, src/main.py
- **Issue**: Unbounded growth in long sessions
- **Fix**: Explicit PIL cleanup, LRU cache, cleanup old QThreads
- **Tests**: tests/test_memory_management.py
- **Time**: 2 hours
- **Validation**: 4-hour stress test, monitor memory usage

### Fix 5: Break Notification System
- **Files**: src/ui/session_manager.py, src/ui/main_window.py
- **Issue**: Timer exists but no actual notifications
- **Fix**: QSystemTrayIcon notifications, popup dialog, enforce breaks
- **Tests**: tests/test_break_notifications.py
- **Time**: 2 hours
- **Validation**: Work 25 minutes, verify notification appears

### Fix 6: Skip Problem Feature
- **Files**: src/ui/problem_widget.py, src/ui/main_window.py
- **Issue**: Getting stuck causes anxiety spirals
- **Fix**: "Skip for now" button, problem queue management
- **Tests**: tests/test_skip_problem.py
- **Time**: 1.5 hours
- **Validation**: Skip problem, verify queued, can return later

### Fix 7: Circuit Breaker for Claude
- **Files**: src/analysis/claude_analyzer.py
- **Issue**: Repeated failures waste resources
- **Fix**: Circuit breaker pattern with exponential backoff
- **Tests**: tests/test_circuit_breaker.py
- **Time**: 2 hours
- **Validation**: Simulate Claude failures, verify circuit opens

### Fix 8: Resource Monitoring
- **Files**: src/core/queue_processor.py
- **Issue**: Can spawn workers until OOM
- **Fix**: psutil monitoring, dynamic worker adjustment
- **Tests**: tests/test_resource_monitoring.py
- **Time**: 1.5 hours
- **Validation**: Simulate high memory, verify worker reduction

## Implementation Order

1. **Day 1 - Safety First** (5 hours)
   - Fix 1: ADHD Panic Button (CRITICAL for user safety)
   - Fix 3: Graceful Shutdown (prevents data loss)

2. **Day 2 - Core Stability** (4 hours)
   - Fix 2: Thread Safety (prevents PDF loss)
   - Fix 4: Memory Leaks (prevents degradation)

3. **Day 3 - User Experience** (3.5 hours)
   - Fix 5: Break Notifications (ADHD support)
   - Fix 6: Skip Problem (reduce anxiety)

4. **Day 4 - Resilience** (3.5 hours)
   - Fix 7: Circuit Breaker (system stability)
   - Fix 8: Resource Monitoring (prevent OOM)

## Quick Wins (Implement First)
1. Add encouraging error messages (30 min)
2. Implement medication reminder UI (45 min)
3. Add pause within steps (30 min)

## Testing Strategy

### Unit Tests
- Each fix gets dedicated test file
- Mock external dependencies
- Test edge cases and error conditions

### Integration Tests
- Test interactions between fixes
- Verify no regressions
- End-to-end user flows

### Stress Tests
- Concurrent PDF uploads
- Long session memory monitoring
- Crash and recovery scenarios

## Validation Checklist

### Pre-Implementation
- [ ] All test files created
- [ ] Existing tests still pass
- [ ] Development environment ready

### Per Fix
- [ ] Tests written first (TDD)
- [ ] Implementation complete
- [ ] All tests passing
- [ ] No memory leaks
- [ ] No performance regression

### Post-Implementation  
- [ ] All critical fixes implemented
- [ ] Stress tests passing
- [ ] ADHD features validated
- [ ] Documentation updated
- [ ] Ready for Phase 7

## Risk Mitigation

### Backup Plans
- If panic button complex: Simple "pause all" first
- If thread safety hard: Queue all PDFs first
- If circuit breaker complex: Simple retry limit first

### Rollback Strategy
- Git tags before each fix
- Feature flags for major changes
- Ability to disable new features

## Success Metrics

### Technical
- Zero PDFs lost under concurrent load
- Memory stable under 500MB baseline
- Crash recovery < 5 seconds
- All tests passing

### User Experience  
- Panic button response < 100ms
- Break notifications appear reliably
- Skip feature reduces reported anxiety
- No data loss on shutdown

## Post-Launch Improvements (Document for Later)

### Medium Priority
- Energy level adaptation
- Bad day mode
- Theme customization
- Progress analytics

### Low Priority
- Social features
- Advanced hint system
- Multi-device sync
- Plugin architecture