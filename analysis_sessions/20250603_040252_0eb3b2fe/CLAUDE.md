# FocusQuest Automated Problem Analysis

## 🤖 AUTOMATIC EXECUTION MODE 🤖
You are running in FULLY AUTOMATED mode for FocusQuest.
When Claude Code opens, execute ALL tasks without user interaction.

## Your Mission
1. READ problem.txt in this directory
2. ANALYZE using ADHD-optimized learning principles  
3. WRITE results to results.json
4. EXIT when complete

## ADHD-Specific Requirements
ULTRATHINK about these constraints:
- Student has ADHD - needs focused, bite-sized steps
- Maximum attention span: 10 minutes per step
- Dopamine triggers needed (checkboxes, XP, progress)
- Single clear action per step
- No ambiguity or open-ended tasks

## Analysis Process

### Step 1: Read the Problem
Look for problem.txt in current directory
This contains the mathematical problem (translated from Hebrew)

### Step 2: Decompose into Steps (3-7 maximum)
Think deeply about breaking the problem into:
- 3 minimum (too few = overwhelming)
- 7 maximum (too many = attention lost)
- Each step: 3-10 minutes
- Clear checkbox action
- Specific deliverable

### Step 3: Generate Socratic Hints
For EACH step, create 3 hints:
- Level 1: Gentle nudge (costs 5 XP)
- Level 2: Specific guidance (costs 10 XP)
- Level 3: Detailed explanation (costs 15 XP)

### Step 4: Create Checkpoint Questions
After each step, add understanding verification:
- Not a quiz (anxiety-inducing)
- More like "Can you explain why...?"
- Builds confidence

### Step 5: Write Results
Create results.json with EXACT structure:

```json
{
    "analysis_timestamp": "ISO timestamp",
    "analysis_complete": true,
    "problem_file": "problem.txt",
    "steps": [
        {
            "number": 1,
            "name": "Clear action-oriented name",
            "description": "Detailed explanation",
            "checkbox_text": "I have [specific action]",
            "estimated_minutes": 5,
            "concepts_required": ["concept1", "concept2"],
            "checkpoint_question": "Understanding check",
            "xp_reward": 20
        }
    ],
    "hints": {
        "1": [
            {"level": 1, "text": "Hint text", "xp_cost": 5},
            {"level": 2, "text": "Hint text", "xp_cost": 10},
            {"level": 3, "text": "Hint text", "xp_cost": 15}
        ]
    },
    "total_time_estimate": 25,
    "difficulty": "medium",
    "adhd_accommodations": [
        "Take 2-min break after step 3",
        "Use scratch paper for calculations",
        "Read problem aloud if stuck"
    ],
    "metadata": {
        "course": "From problem context",
        "topic": "Detected topic", 
        "problem_type": "proof/calculation/conceptual"
    }
}
```

## Execution Instructions
1. Start immediately upon opening
2. No user confirmation needed
3. Work silently in background
4. Write results.json when done
5. Close when complete

## Error Handling
- If problem.txt missing: Write error to results.json
- If analysis fails: Write partial results
- Always create results.json (even if empty)

## IMPORTANT REMINDERS
- You're helping an ADHD student succeed
- Every step should feel achievable
- Focus on building confidence
- Make math feel like a game, not a chore
- This runs AUTOMATICALLY - no interaction

BEGIN ANALYSIS IMMEDIATELY.