---
name: implement
description: Simple workflow - Code → Test → Docs. For single tasks like components, functions, or endpoints.
---

# Implement Command

You will implement a simple task using the **simple-workflow** skill.

## Instructions

1. **Read the skill first**:
   ```
   Read .cursor/skills/simple-workflow/SKILL.md
   ```

2. **Follow the workflow exactly**:
   - Call `worker` to create the code
   - Call `test-runner` to run tests (if tests exist in project)
     - If tests fail: call `debugger` (max 2 attempts) → retry test-runner
     - If no tests: skip this step
   - Call `documenter` to create documentation

3. **Execute sequentially**:
   - Wait for each agent to complete before calling the next
   - Handle errors: if worker fails, report and stop
   - Pass context from previous agent to next
   - Track progress and show it to the user

## Example

User: `/implement Create a Button component with onClick handler`

You should:

```markdown
I'll implement this using the simple workflow: Code → Test → Docs

### Step 1: Implementation
[Call Task with subagent_type="worker"]
✅ Code created

### Step 2: Testing
[Check if project has tests]
[Call Task with subagent_type="test-runner"]
- ❌ 2 tests failed
[Call Task with subagent_type="debugger"]
✅ Fixed, all tests passing

### Step 3: Documentation
[Call Task with subagent_type="documenter"]
✅ Documentation created

### Summary
✅ Implementation complete!
- Code: src/components/Button.tsx
- Tests: ✅ 5 passing
- Documentation: docs/components/Button.md
```

## When to Use

Good for:
- Single component or function
- One API endpoint
- Utility function
- Simple feature addition

NOT good for:
- Complex features with multiple parts
- Tasks requiring planning
- Multi-step implementations
→ Use `/orchestrate` instead

## Remember

- Read the `simple-workflow` skill first
- Execute steps: `worker` → `test-runner` (if tests exist) → `documenter`
- Use `debugger` to auto-fix test failures (max 2 attempts)
- If no tests in project, skip test-runner
- Show progress to the user
- Everything in same chat, sequential, visible
