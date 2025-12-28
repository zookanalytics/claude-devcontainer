# Claude DevContainer

A secure, AI-agent-ready development container base image for Claude Code and Gemini CLI.

## Features

- Node.js 22 with pnpm
- Claude Code and Gemini CLI pre-installed
- Firewall with domain allowlisting (iptables/ipset)
- Security hooks to prevent common mistakes
- ZSH with Powerlevel10k theme
- tmux for persistent terminal sessions

## Quick Start

Run this in your project root to initialize:

```bash
curl -fsSL https://raw.githubusercontent.com/zookanalytics/claude-devcontainer/main/scripts/init-project.sh | bash
```

This creates:
- `.devcontainer/devcontainer.json` - configured for the base image
- `.devcontainer/allowed-domains.txt` - template for project-specific domains
- `.devcontainer/post-create-project.sh` - template for project setup

Then open in VS Code and "Reopen in Container".

### Manual Setup

Alternatively, add to your project's `.devcontainer/devcontainer.json`:

```json
{
  "name": "${localEnv:PROJECT_NAME}-${localWorkspaceFolderBasename}",
  "image": "ghcr.io/zookanalytics/claude-devcontainer:latest",
  "runArgs": [
    "--cap-add=NET_ADMIN",
    "--cap-add=NET_RAW",
    "--cap-add=SYSLOG"
  ],
  "remoteUser": "node",
  "workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=delegated",
  "workspaceFolder": "/workspace",
  "mounts": [
    "source=${localEnv:PROJECT_NAME}-node-modules-${localWorkspaceFolderBasename},target=/workspace/node_modules,type=volume",
    "source=${localEnv:PROJECT_NAME}-claude-config,target=/home/node/.claude,type=volume",
    "source=${localEnv:PROJECT_NAME}-gemini-config,target=/home/node/.gemini,type=volume",
    "source=pnpm-store,target=/workspace/.pnpm-store,type=volume"
  ],
  "postCreateCommand": "/usr/local/bin/post-create.sh"
}
```

## Extending Domain Allowlist

The base image includes common domains (npm, GitHub, Anthropic, Google, etc.). Add project-specific domains in `.devcontainer/allowed-domains.txt`:

```
# Project-specific domains
api.your-service.com
your-backend.example.com
```

## Project-Specific Setup

Create `.devcontainer/post-create-project.sh` for project-specific initialization:

```bash
#!/bin/bash
set -e

# Install project dependencies
pnpm install

# Install Playwright browsers
pnpm exec playwright install

# Any other project-specific setup
echo "Project setup complete!"
```

The base `post-create.sh` will automatically call this script if it exists.

## Security Hooks

Both Claude Code and Gemini CLI are configured with security hooks that prevent:

- Pushing directly to main/master branches
- Using `--no-verify` to bypass pre-commit hooks
- Using `--admin` to bypass GitHub branch protection
- Leaking sensitive environment variables
- Accessing sensitive files (.env, credentials, keys)

Hooks are installed at:
- `/etc/claude-code/hooks/` - Claude Code hooks
- `/etc/gemini-code/hooks/` - Gemini CLI hooks (symlinks to Claude hooks)

## Gemini CLI Setup

The base image includes Gemini CLI and security hooks. For project-level Gemini config, create `.gemini/settings.json`:

```json
{
  "tools": {
    "enableHooks": true
  },
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "run_shell_command",
        "hooks": [
          {
            "name": "prevent-main-push",
            "type": "command",
            "command": "/etc/gemini-code/hooks/prevent-main-push.sh",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

See `/etc/gemini-code/settings.json` for the full template.

## Examples

See the `examples/` directory for:
- `devcontainer.json` - Full consumer configuration template
- `allowed-domains.txt` - Example project-specific domain allowlist

## License

MIT
