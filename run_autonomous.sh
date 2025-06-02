#!/bin/bash
# FocusQuest Test Validation - Claude Code Instructions
# Following 4-step workflow: Research → Plan → Implement → Integrate

set -e
cd /home/puncher/focusquest
source venv/bin/activate

# Environment setup
export CLAUDE_AUTO_ACCEPT=true

#=============================================================================
# RESEARCH PHASE
#=============================================================================
cat << 'INSTRUCTIONS' > current_task.md
<research_phase>
ultrathink about the current test suite:
- Read all files in tests/ directory
- Analyze existing test coverage
- Identify which fixes 1-8 have proper tests
- Map test files to their corresponding features
- Find gaps in test coverage
- Consider ADHD-specific testing needs
</research_phase>

<data_collection>
Execute these discovery commands:
- find tests/ -name "test_*.py" | sort
- grep -l "class Test" tests/*.py
- pytest --collect-only --quiet
- Check if each fix has corresponding test file
</data_collection>
INSTRUCTIONS

# Execute research
bash -c "$(grep -E '^-' current_task.md | sed 's/^- //')"

#=============================================================================
# SECTION 1: Fix Test Validation
#=============================================================================
cat << 'SECTION1' >> current_task.md

<section_1_planning>
For each fix test (1-8), plan validation approach:
- Map fix number to correct test file name
- Design retry strategy for failures
- Plan auto-repair for common issues
- Consider ADHD impact of test failures
</section_1_planning>

<section_1_implementation>
For fixes 1-8, execute this pattern:
1. Identify correct test file from existing tests
2. Run pytest with verbose output
3. If test fails:
   - think about failure reason
   - Apply common fixes (PyQt5→PyQt6, assertEquals→assertEqual)
   - Retry test
4. Document result in validation report
5. Only proceed if critical tests pass
</section_1_implementation>

<fix_mapping>
Use these mappings:
Fix 1 → test_panic_button.py (ADHD emergency feature)
Fix 2 → test_thread_safety.py (Concurrent operations)
Fix 3 → test_crash_recovery.py (Session persistence)
Fix 4 → test_memory_management.py (Performance)
Fix 5 → test_break_notifications.py (ADHD breaks)
Fix 6 → test_skip_problem.py (Overwhelm management)
Fix 7 → test_circuit_breaker.py (Claude resilience)
Fix 8 → test_resource_monitor.py (System health)
</fix_mapping>

<commit_criteria>
Only commit if:
- At least 6/8 fixes passing
- All ADHD-critical features working (1,3,5,6)
- No regression in existing functionality
</commit_criteria>
SECTION1

# Clear context
echo "/clear" >> current_task.md

#=============================================================================
# SECTION 2: Unit Test Expansion
#=============================================================================
cat << 'SECTION2' >> current_task.md

<section_2_planning>
ultrathink about unit test gaps:
- What edge cases are untested?
- Which components lack isolation tests?
- What ADHD scenarios need coverage?
- How to test Hebrew PDF processing?
</section_2_planning>

<section_2_implementation>
Create enhanced unit tests for:
1. PDF edge cases:
   - Corrupted PDF handling
   - Hebrew/English mixed content
   - Empty PDF graceful failure
   - Memory efficiency with large files

2. Database integrity:
   - Concurrent write safety
   - Transaction rollback behavior
   - Connection pool management
   
3. ADHD-specific units:
   - Focus timer accuracy
   - Break notification timing
   - Anxiety detection thresholds
</section_2_implementation>

<test_structure>
Each test file should follow:
- Descriptive class names (TestPDFEdgeCases)
- Clear test method names (test_corrupted_pdf_handling)
- ADHD-relevant assertions
- Proper fixtures and mocks
- Skip decorators if dependencies missing
</test_structure>
SECTION2

echo "/clear" >> current_task.md

#=============================================================================
# SECTION 3: Integration Tests
#=============================================================================
cat << 'SECTION3' >> current_task.md

<section_3_planning>
think hard about integration points:
- PDF → Processing → Database flow
- GUI ↔ Backend synchronization
- File watcher → Queue → Processor chain
- Circuit breaker → Fallback behavior
</section_3_planning>

<section_3_implementation>
Design integration tests that verify:
1. Complete PDF processing pipeline
2. Multi-component failure scenarios
3. ADHD user journey (2-hour session)
4. Recovery from system crashes
5. Performance under concurrent load
</section_3_implementation>

<integration_scenarios>
Critical paths to test:
- User uploads PDF → sees problem in UI
- Multiple PDFs processing simultaneously
- Claude fails → circuit breaker → fallback
- System crash → recovery → session restored
- 4-hour hyperfocus session stability
</integration_scenarios>
SECTION3

echo "/clear" >> current_task.md

#=============================================================================
# SECTION 4: ADHD Workflow Tests
#=============================================================================
cat << 'SECTION4' >> current_task.md

<section_4_research>
ultrathink about real ADHD usage patterns:
- Hyperfocus sessions (2-4 hours)
- Medication effectiveness curves
- Anxiety-triggered skip patterns
- Break snoozing during flow states
- Distraction recovery needs
- Overwhelm indicators
</section_4_research>

<section_4_implementation>
Create comprehensive ADHD workflow tests:
1. Hyperfocus session simulation
2. Medication timing adaptations
3. Anxiety intervention triggers
4. Break flexibility testing
5. Skip pattern analysis
6. Recovery from interruptions
</section_4_implementation>

<adhd_fixtures>
Create fixtures that model:
- ADHD user profiles
- Medication schedules
- Focus/distraction patterns
- Anxiety thresholds
- Break compliance rates
</adhd_fixtures>
SECTION4

echo "/clear" >> current_task.md

#=============================================================================
# SECTION 5: Performance Benchmarks
#=============================================================================
cat << 'SECTION5' >> current_task.md

<section_5_planning>
Define ADHD-critical performance metrics:
- Startup time (frustration threshold)
- UI response (focus maintenance)
- Memory usage (system stability)
- PDF processing (patience limits)
</section_5_planning>

<section_5_benchmarks>
Establish and verify benchmarks:
1. Startup: < 3 seconds
2. UI response: < 100ms
3. Memory baseline: < 300MB
4. PDF processing: < 30s/page
5. CPU idle: < 5%
6. Session stability: 4+ hours
</section_5_benchmarks>

<performance_report>
Generate performance baseline document with:
- Current measurements
- Target thresholds
- ADHD impact analysis
- Optimization recommendations
</performance_report>
SECTION5

echo "/clear" >> current_task.md

#=============================================================================
# SECTION 6: Final Validation & TODO
#=============================================================================
cat << 'SECTION6' >> current_task.md

<section_6_integration>
Compile comprehensive validation report:
1. Run full test suite with coverage
2. Generate coverage HTML report
3. Count total/passed/failed tests
4. Identify critical gaps
</section_6_integration>

<todo_generation>
think hard about Phase 7 prerequisites:
- What must be fixed before integration?
- Which features need documentation?
- What ADHD accommodations are missing?
- Performance optimizations needed?
</todo_generation>

<final_report>
Create pre_phase7_todo.md with:
- Test suite health summary
- Coverage metrics
- Critical fixes needed
- Documentation gaps
- ADHD feature checklist
- Integration readiness assessment
</final_report>

<completion_criteria>
Mark Phase 7 ready only if:
- Core functionality tests passing
- ADHD features validated
- Performance within targets
- No critical bugs
- Documentation current
</completion_criteria>
SECTION6

#=============================================================================
# EXECUTION
#=============================================================================
echo "" >> current_task.md
echo "<autonomous_execution>" >> current_task.md
echo "Execute all sections sequentially" >> current_task.md
echo "Commit after each successful section" >> current_task.md
echo "Use thinking modes as specified" >> current_task.md
echo "Clear context between sections" >> current_task.md
echo "No human intervention required" >> current_task.md
echo "</autonomous_execution>" >> current_task.md

# Final instruction
echo "EXECUTE TASK: Follow all instructions in current_task.md autonomously"