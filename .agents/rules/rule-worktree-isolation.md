# Rule: Multi-Agent Git Branching & Worktree Isolation Flow

## Rule Overview & Scope
Whenever a new user prompt or feature request is received, evaluate the status of the main repository directory:

1. **Main Repository Unused (Idle)**:
   - If no other agent thread or active task is operating in the main repo directory, create a dedicated feature branch directly in the main workspace:
     `git checkout -b feature/<task-name>` (or `git switch -c feature/<task-name>`).

2. **Main Repository In Use (Active Multi-Agent)**:
   - If another agent thread or active task is currently working in the main repo directory, create a dedicated Git worktree for isolated execution:
     `git worktree add -b feature/<task-name> ../<worktree-name> main` (or base branch).

3. **Worktree Directory & Symlink Setup**:
   - When using a worktree, perform all edits, code changes, tool invocations, tests, and dev server runs strictly inside the dedicated worktree directory.
   - Symlink ignored dependencies from the main workspace into the worktree (e.g., `ln -s /path/to/main/frontend/node_modules /path/to/worktree/frontend/node_modules`) so `npm run dev` and test commands work immediately without package lock issues.

4. **Clean Merging Flow**:
   - Isolating each task on its own feature branch (in main or in a worktree) enables clean rebase, PR creation, and conflict-free merging back into `main`. Once work is verified, worktrees can be cleanly removed via `git worktree remove`.

## Rationale & Industry Standard Practice
Branching on idle repos and Worktree Isolation for active parallel AI agents is an industry-standard best practice in modern multi-agent software development:

- **Zero Overlapping Edits**: Prevents uncommitted code overwrites, index lock contention, and dirty state corruption.
- **Concurrent Test & Build Runs**: Allows each agent thread to run test suites (`pytest`, `npm test`) and dev servers independently without artifact collisions.
- **Clean Branch & PR Merges**: Keeps all feature work organized on feature branches ready for review, rebase, and merging back into `main`.

