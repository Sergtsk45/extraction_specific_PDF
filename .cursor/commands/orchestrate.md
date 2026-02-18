---
name: orchestrate
description: Full orchestration - Plan → Task Loop (Code → Test → Review → Verify with auto-fixing) → Docs. For complex features and systems.
---

# Orchestrate Command

You will orchestrate a complete implementation cycle using the **orchestration** skill.

## Instructions

1. **Read the orchestration skill first**:
   ```
   Read .cursor/skills/orchestration/SKILL.md
   ```

2. **Follow the orchestration workflow**:
   
   **Phase 1: Planning**
   - Call `planner` subagent to break down the task into subtasks
   - Extract the list of tasks from the plan
   
   **Phase 2: Task Loop (Repeat for EACH task from Planner)**
   
   For EACH task from the plan, execute this cycle:
   
   - Call `worker` subagent to write code for current task
   - Call `test-runner` subagent to run tests (if tests exist in project)
     - If tests fail: call `debugger` subagent (max 3 attempts) → retry test-runner
   - Call `security-auditor` subagent if code handles:
     - Authentication/Authorization
     - API endpoints
     - User input/data handling
     - Secrets/credentials
     - File uploads
     - Payments
   - Call `reviewer` subagent to check code quality
     - If issues found: call `debugger` subagent (max 3 attempts) → retry reviewer
   - Final verification is done by `test-runner` (already validates acceptance criteria)
   - Mark task complete, move to next
   
   **Phase 3: Documentation**
   - Call `documenter` subagent with full context of all changes
   - Create comprehensive documentation

3. **Track progress**:
   - Show which task is current (e.g., "Task 2/5")
   - Show what each agent is doing
   - Use status indicators (✅ ❌ ⚠️)
   - Report final summary

## Example

User: `/orchestrate Build authentication system with JWT`

You should:

```markdown
I'll orchestrate the full implementation cycle for this complex task.

**Task**: Build authentication system with JWT

### Phase 1: Planning

[Call planner to create task breakdown]

**Plan created with 4 tasks:**
1. User model and database schema
2. JWT token generation and validation
3. Login/register endpoints
4. Protected route middleware

### Phase 2: Implementation Loop

**Task 1/4: User model and database schema**
  → worker: Creating models... ✅
  → test-runner: Running tests & verifying... ✅ All passed & verified
  → security-auditor: Checking sensitive data... ✅ Approved
  → reviewer: Checking quality... ✅ Approved

**Task 2/4: JWT token generation**
  → worker: Creating JWT utils... ✅
  → test-runner: Running tests & verifying... ❌ 2 failed
  → debugger: Fixing token expiry... ✅
  → test-runner: Re-running... ✅ All passed & verified
  → security-auditor: Checking secrets... ⚠️ Hardcoded secret found
  → debugger: Moving to env vars... ✅
  → security-auditor: Re-checking... ✅ Approved
  → reviewer: Checking quality... ✅ Approved

[Continue for remaining tasks...]

### Phase 3: Documentation

[Call documenter with all changes]

### Summary

✅ All 4 tasks completed
✅ 23 tests passing
✅ Code reviewed and approved
✅ Documentation created

**Files changed:**
- src/models/User.ts
- src/utils/jwt.ts
- src/routes/auth.ts
- src/middleware/auth.ts
```

## When to Use

Good for:
- Full features (auth, payments, admin panel, etc.)
- Systems with multiple modules
- Tasks requiring planning and breakdown
- Complex refactors
- When you need code review and auto-fixing

NOT good for:
- Simple, single-purpose tasks
- Quick changes
→ Use `/implement` instead

## Limits & Controls

### Retry Limits
- **Max 3 retry attempts per stage** (test/security/review)
- `debugger` is called automatically when:
  - `test-runner` fails (tests, lints, or verification incomplete)
  - `security-auditor` finds vulnerabilities
  - `reviewer` finds problems
- If max attempts reached: report to user, ask for guidance

### Task Limits
- **Recommended max: 10 tasks per cycle**
- If plan has more than 10 tasks:
  - Process first 10
  - Report progress
  - Ask user before continuing
- Monitor context window usage
- Can pause/resume at any task boundary

## Remember

- Read the `orchestration` skill first
- Execute sequentially: Planning → Loop → Documentation
- Track and report progress for each task
- Use debugger for auto-fixing errors
- Create comprehensive final documentation
