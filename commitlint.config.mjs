const commitlintConfig = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Types per commit_specification.md
    "type-enum": [
      2,
      "always",
      [
        "build",
        "chore",
        "docs",
        "feat",
        "fix",
        "ops",
        "perf",
        "refactor",
        "revert",
        "security",
        "style",
        "test",
      ],
    ],
    // Scopes for this monorepo (packages/* + cross-cutting concerns)
    "scope-enum": [
      2,
      "always",
      [
        "ai-tools",
        "bmad-dashboard",
        "bmad-orchestrator",
        "ci",
        "claude-instance",
        "deps",
        "devcontainer",
        "docs",
        "git-workflow",
        "tests",
      ],
    ],
    // Scope encouraged but optional per commit_specification.md
    "scope-empty": [1, "never"],
    // Line length limits per commit_specification.md
    "header-max-length": [2, "always", 72],
    "body-max-line-length": [2, "always", 100],
  },
};
export default commitlintConfig;
