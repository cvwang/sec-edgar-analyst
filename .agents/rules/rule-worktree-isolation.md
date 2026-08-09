# Rule: Multi-Agent Git Worktree Isolation

## Rule Overview & Scope
Whenever a new user prompt or request is received, and there is already another separate agent thread actively running or operating in the main repository (or primary workspace):

1. **Automatic Worktree Creation**: A new Git worktree MUST be created for the new prompt using `git worktree add -b <branch-name> <worktree-path> main` (or base branch).
2. **Directory Isolation**: The new agent thread must perform all edits, code changes, tool invocations, tests, and execution strictly inside its dedicated worktree directory.
3. **Dependency Symlinking**: Because `.gitignore` excludes binary/package directories like `frontend/node_modules`, the agent MUST automatically create symlinks for ignored dependencies from the main workspace into the worktree (e.g., `ln -s /path/to/main/frontend/node_modules /path/to/worktree/frontend/node_modules`) so commands like `npm run dev` work immediately without `npm install` failures or registry locks.
4. **No Direct Overlapping Edits**: Never perform simultaneous code modifications in the same working directory as another active agent thread to prevent dirty working trees, race conditions, line clashing, or build errors.

## Rationale & Industry Standard Practice
Worktree isolation for parallel AI agents is an industry-standard best practice in modern multi-agent software development:

- **Dirty Tree & Race Condition Prevention**: Simultaneous file writes by multiple agents in one working tree overwrite unstaged changes, corrupt git status, and produce broken intermediate states.
- **Independent Build & Verification**: Each agent can run dev servers, linters, and unit test suites (`pytest`, `npm test`) concurrently without file lock contention or temporary artifact collisions.
- **Clean Branching & Review**: Isolates work onto topic/feature branches, enabling clean rebase, PR creation, and conflict resolution before merging into `main`.
