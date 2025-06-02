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
