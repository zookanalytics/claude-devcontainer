# Claude DevContainer Base Image Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a reusable Docker base image that provides a secure, Claude Code-ready development environment for any GitHub repository with minimal configuration.

**Architecture:** A Docker image published to ghcr.io containing Node.js tooling, iptables-based firewall with domain allowlisting, and Claude Code managed configuration. Consumer projects reference the base image and extend with project-specific domains and Claude config. Volume naming derived from git remote origin URL.

**Tech Stack:** Docker, iptables/ipset/dnsmasq, Bash, GitHub Actions, Claude Code managed settings

---

## Phase 1: Repository Setup

### Task 1: Initialize Repository

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `LICENSE`

**Step 1: Create repository structure**

```bash
mkdir claude-devcontainer
cd claude-devcontainer
git init
```

**Step 2: Create .gitignore**

```gitignore
# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp
*.swo

# Docker
.docker/

# Logs
*.log
```

**Step 3: Create README.md**

```markdown
# Claude DevContainer

A secure, Claude Code-ready development container base image.

## Features

- Node.js 22 with pnpm
- Firewall with domain allowlisting (iptables/ipset)
- Claude Code managed configuration with bypass permissions
- Security hooks to prevent common mistakes
- ZSH with Powerlevel10k theme

## Quick Start

Add to your project's `.devcontainer/devcontainer.json`:

\`\`\`json
{
  "name": "${localEnv:PROJECT_NAME}-${localWorkspaceFolderBasename}",
  "image": "ghcr.io/OWNER/claude-devcontainer:latest",
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
    "source=pnpm-store,target=/workspace/.pnpm-store,type=volume"
  ],
  "postCreateCommand": "/usr/local/bin/post-create.sh"
}
\`\`\`

## Extending Domain Allowlist

Create `.devcontainer/allowed-domains.txt` in your project:

\`\`\`
# Project-specific domains
api.your-service.com
\`\`\`

## License

MIT
```

**Step 4: Create LICENSE (MIT)**

```
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Step 5: Commit**

```bash
git add .
git commit -m "chore: initialize repository"
```

---

## Phase 2: Dockerfile

### Task 2: Create Base Dockerfile

**Files:**
- Create: `Dockerfile`

**Step 1: Create Dockerfile**

```dockerfile
FROM node:22

ARG TZ
ENV TZ="$TZ"

# Install basic development tools and firewall packages
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  curl \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  dnsmasq \
  aggregate \
  jq \
  nano \
  vim \
  ripgrep \
  locales \
  lsof \
  ulogd2 \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install latest GitHub CLI from official repository
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | gpg --dearmor -o /usr/share/keyrings/githubcli-archive-keyring.gpg; \
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null; \
  apt update && apt install -y gh && apt-get clean && rm -rf /var/lib/apt/lists/*

# Generate and set locale
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
  locale-gen
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Setup pnpm via corepack
ENV PNPM_HOME="/pnpm"
RUN mkdir -p "$PNPM_HOME"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

ARG USERNAME=node

# Persist bash history
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set DEVCONTAINER environment variable
ENV DEVCONTAINER=true

# Create workspace
RUN mkdir -p /workspace && \
  chown -R node:node /workspace

WORKDIR /workspace

# Install git-delta
ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Install Playwright system dependencies
RUN pnpm dlx playwright install-deps

# Ensure node user has access to required directories
RUN chown -R node:node /usr/local/share
RUN chown -R node:node /pnpm

# Set up non-root user
USER node

# Create directories for mounted volumes
RUN mkdir -p /home/node/.claude \
             /home/node/.config \
             /home/node/.cache/ms-playwright

# Set default shell and editor
ENV SHELL=/bin/zsh
ENV EDITOR=vim
ENV VISUAL=vim

# Install zsh with powerlevel10k
ARG ZSH_IN_DOCKER_VERSION=1.2.1
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  -x

# Setup pnpm
RUN pnpm setup

# Copy scripts (will be added in later tasks)
# COPY is done after USER root switch below

USER root

# Copy configuration files
COPY config/allowed-domains.txt /etc/allowed-domains.txt
COPY config/dnsmasq.conf /etc/dnsmasq.conf
COPY config/ulogd.conf /etc/ulogd.conf

# Copy scripts
COPY scripts/init-firewall.sh /usr/local/bin/
COPY scripts/start-dnsmasq.sh /usr/local/bin/
COPY scripts/start-ulogd.sh /usr/local/bin/
COPY scripts/read-firewall-logs.sh /usr/local/bin/
COPY scripts/post-create.sh /usr/local/bin/
COPY scripts/derive-project-name.sh /usr/local/bin/

# Make scripts executable and configure sudo
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  chmod +x /usr/local/bin/start-dnsmasq.sh && \
  chmod +x /usr/local/bin/start-ulogd.sh && \
  chmod +x /usr/local/bin/read-firewall-logs.sh && \
  chmod +x /usr/local/bin/post-create.sh && \
  chmod +x /usr/local/bin/derive-project-name.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-commands && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/start-dnsmasq.sh" >> /etc/sudoers.d/node-commands && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/start-ulogd.sh" >> /etc/sudoers.d/node-commands && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/read-firewall-logs.sh" >> /etc/sudoers.d/node-commands && \
  chmod 0440 /etc/sudoers.d/node-commands

# Create log files with proper permissions
RUN touch /var/log/dnsmasq.log && chmod 666 /var/log/dnsmasq.log
RUN touch /var/log/ulogd-firewall.log && chmod 666 /var/log/ulogd-firewall.log

# Copy Claude managed configuration
COPY claude/ /etc/claude-code/

USER node
```

**Step 2: Verify Dockerfile syntax**

```bash
docker build --check .
```

Expected: No syntax errors

**Step 3: Commit**

```bash
git add Dockerfile
git commit -m "build: add base Dockerfile"
```

---

## Phase 3: Configuration Files

### Task 3: Create Base Domain Allowlist

**Files:**
- Create: `config/allowed-domains.txt`

**Step 1: Create config directory and allowlist**

```bash
mkdir -p config
```

**Step 2: Create allowed-domains.txt**

```
# Base allowed domains for Claude DevContainer
# Projects can extend via .devcontainer/allowed-domains.txt

# NPM Registry
registry.npmjs.org

# Node.js
nodejs.org

# Anthropic API (Claude)
api.anthropic.com
statsig.anthropic.com

# GitHub (additional to API ranges fetched dynamically)
raw.githubusercontent.com

# GPG keyservers
keyserver.ubuntu.com
keys.openpgp.org

# Google Fonts
fonts.gstatic.com
fonts.googleapis.com

# VS Code Marketplace
main.vscode-cdn.net

# JSON schema
unpkg.com
json.schemastore.org

# Error tracking
sentry.io

# Certificate validation
crl3.digicert.com
ocsp.digicert.com
```

**Step 3: Commit**

```bash
git add config/allowed-domains.txt
git commit -m "config: add base domain allowlist"
```

---

### Task 4: Create DNS and Logging Configuration

**Files:**
- Create: `config/dnsmasq.conf`
- Create: `config/ulogd.conf`

**Step 1: Create dnsmasq.conf**

```
# dnsmasq configuration for devcontainer
# Logs DNS queries for debugging blocked domains

log-queries
log-facility=/var/log/dnsmasq.log
```

**Step 2: Create ulogd.conf**

```
[global]
logfile="/var/log/ulogd.log"
stack=log1:NFLOG,base1:BASE,ifi1:IFINDEX,ip2str1:IP2STR,print1:PRINTPKT,emu1:LOGEMU

[log1]
group=1

[base1]
[ifi1]
[ip2str1]
[print1]

[emu1]
file="/var/log/ulogd-firewall.log"
sync=1
```

**Step 3: Commit**

```bash
git add config/dnsmasq.conf config/ulogd.conf
git commit -m "config: add dnsmasq and ulogd configuration"
```

---

## Phase 4: Scripts

### Task 5: Create Firewall Initialization Script

**Files:**
- Create: `scripts/init-firewall.sh`

**Step 1: Create scripts directory**

```bash
mkdir -p scripts
```

**Step 2: Create init-firewall.sh**

```bash
#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# SECURITY NOTE: This script temporarily sets ACCEPT policies during execution
# to allow re-runs. If the script fails mid-execution, the error trap handler
# restores DROP policies for defense-in-depth.

# Reset default policies to ACCEPT at the very start to allow re-runs
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Set up error trap to restore DROP policies if script fails
cleanup_on_error() {
    echo "ERROR: Script failed, restoring DROP policies for security"
    iptables -P INPUT DROP 2>/dev/null || true
    iptables -P OUTPUT DROP 2>/dev/null || true
    iptables -P FORWARD DROP 2>/dev/null || true
}
trap cleanup_on_error ERR EXIT

# Extract Docker DNS info BEFORE any flushing
DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

# Flush existing rules and delete existing ipsets
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

# Restore Docker DNS rules
if [ -n "$DOCKER_DNS_RULES" ]; then
    echo "Restoring Docker DNS rules..."
    iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
    iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
    echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
else
    echo "No Docker DNS rules to restore"
fi

# Allow DNS and localhost before any restrictions
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT -p udp --sport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -d 169.254.169.254 -j ACCEPT
iptables -A INPUT -s 169.254.169.254 -j ACCEPT

# Create ipset with CIDR support
ipset create allowed-domains hash:net

# Fetch GitHub meta information and add their IP ranges
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -s https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "ERROR: Failed to fetch GitHub IP ranges"
    exit 1
fi

if ! echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null; then
    echo "ERROR: GitHub API response missing required fields"
    exit 1
fi

echo "Processing GitHub IPs..."
while read -r cidr; do
    if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "ERROR: Invalid CIDR range from GitHub meta: $cidr"
        exit 1
    fi
    echo "Adding GitHub range $cidr"
    ipset add allowed-domains "$cidr"
done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git)[]' | aggregate -q)

# Process domain files
process_domains_file() {
    local domains_file="$1"
    if [ ! -f "$domains_file" ]; then
        return
    fi

    echo "Reading allowed domains from $domains_file..."
    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        domain=$(echo "$line" | xargs)
        echo "Resolving $domain..."
        ips=$(dig +noall +answer A "$domain" | awk '$4 == "A" {print $5}')
        if [ -z "$ips" ]; then
            echo "WARNING: Failed to resolve $domain, skipping"
            continue
        fi

        while read -r ip; do
            if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                echo "WARNING: Invalid IP from DNS for $domain: $ip"
                continue
            fi
            if ! ipset test -q allowed-domains "$ip"; then
                echo "Adding $ip for $domain"
                ipset add allowed-domains "$ip"
            fi
        done < <(echo "$ips")
    done < "$domains_file"
}

# Process base domains (from image)
process_domains_file "/etc/allowed-domains.txt"

# Process project-specific domains (if present)
process_domains_file "/workspace/.devcontainer/allowed-domains.txt"

# Get host IP from default route
HOST_IP=$(ip route | grep default | cut -d" " -f3)
if [ -z "$HOST_IP" ]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi

HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"

# Set up remaining iptables rules
iptables -A INPUT -s "$HOST_NETWORK" -j ACCEPT
iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT

# Log blocked outbound connections
iptables -A OUTPUT -j NFLOG --nflog-group 1 --nflog-prefix "FIREWALL-BLOCK: "
iptables -A OUTPUT -j REJECT --reject-with icmp-net-unreachable

# Set default policies to DROP
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Remove error trap
trap - ERR EXIT

echo "Firewall configuration complete"

# Verify firewall
echo "Verifying firewall rules..."
if curl --connect-timeout 5 https://example.com >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - was able to reach https://example.com"
    exit 1
else
    echo "Firewall verification passed - unable to reach https://example.com as expected"
fi

if ! curl --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - unable to reach https://api.github.com"
    exit 1
else
    echo "Firewall verification passed - able to reach https://api.github.com as expected"
fi
```

**Step 3: Commit**

```bash
git add scripts/init-firewall.sh
git commit -m "feat: add firewall initialization script"
```

---

### Task 6: Create Supporting Scripts

**Files:**
- Create: `scripts/start-dnsmasq.sh`
- Create: `scripts/start-ulogd.sh`
- Create: `scripts/read-firewall-logs.sh`
- Create: `scripts/derive-project-name.sh`

**Step 1: Create start-dnsmasq.sh**

```bash
#!/bin/bash
set -euo pipefail

# Start dnsmasq for DNS logging
dnsmasq --no-daemon &
echo "dnsmasq started"
```

**Step 2: Create start-ulogd.sh**

```bash
#!/bin/bash
set -euo pipefail

# Start ulogd for firewall logging
ulogd -d
echo "ulogd started"
```

**Step 3: Create read-firewall-logs.sh**

```bash
#!/bin/bash
set -euo pipefail

# Read firewall block logs
if [ -f /var/log/ulogd-firewall.log ]; then
    tail -f /var/log/ulogd-firewall.log
else
    echo "No firewall log file found"
    exit 1
fi
```

**Step 4: Create derive-project-name.sh**

```bash
#!/bin/bash
set -euo pipefail

# Derive project name from git remote origin URL
# Usage: derive-project-name.sh [repo-path]
# Output: lowercase project name suitable for Docker naming

REPO_PATH="${1:-.}"

cd "$REPO_PATH"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "ERROR: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || true)

if [ -z "$REMOTE_URL" ]; then
    echo "ERROR: No remote origin configured" >&2
    exit 1
fi

# Extract repo name from URL
# Handles: git@github.com:owner/repo.git, https://github.com/owner/repo.git, https://github.com/owner/repo
PROJECT_NAME=$(echo "$REMOTE_URL" | sed -E 's#.*/([^/]+?)(\.git)?$#\1#' | tr '[:upper:]' '[:lower:]' | tr -s ' _/' '-')

if [ -z "$PROJECT_NAME" ]; then
    echo "ERROR: Could not extract project name from: $REMOTE_URL" >&2
    exit 1
fi

echo "$PROJECT_NAME"
```

**Step 5: Commit**

```bash
git add scripts/start-dnsmasq.sh scripts/start-ulogd.sh scripts/read-firewall-logs.sh scripts/derive-project-name.sh
git commit -m "feat: add supporting scripts"
```

---

### Task 7: Create Post-Create Script

**Files:**
- Create: `scripts/post-create.sh`

**Step 1: Create post-create.sh**

```bash
#!/bin/bash
set -euo pipefail

echo "=== Claude DevContainer Post-Create ==="

# Start firewall logging daemon
echo "Starting ulogd..."
sudo /usr/local/bin/start-ulogd.sh

# Initialize firewall
echo "Initializing firewall..."
sudo /usr/local/bin/init-firewall.sh

# Install pnpm dependencies if package.json exists
if [ -f /workspace/package.json ]; then
    echo "Installing pnpm dependencies..."
    cd /workspace
    pnpm install
fi

# Install Playwright browsers if playwright is a dependency
if [ -f /workspace/package.json ] && grep -q '"@playwright' /workspace/package.json; then
    echo "Installing Playwright browsers..."
    pnpm dlx playwright install
fi

echo "=== Post-Create Complete ==="
```

**Step 2: Commit**

```bash
git add scripts/post-create.sh
git commit -m "feat: add post-create script"
```

---

## Phase 5: Claude Managed Configuration

### Task 8: Create Claude Managed Settings

**Files:**
- Create: `claude/managed-settings.json`

**Step 1: Create claude directory**

```bash
mkdir -p claude/hooks
```

**Step 2: Create managed-settings.json**

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions",
    "allow": [
      "Bash(gh pr list:*)",
      "Bash(gh pr show:*)",
      "Bash(gh pr view:*)",
      "Bash(git branch:--show-current)",
      "Bash(git branch:-vv)",
      "Bash(git branch:--merged:*)",
      "Bash(git branch:-d:*)",
      "Bash(git diff:*)",
      "Bash(git fetch:*)",
      "Bash(git log:*)",
      "Bash(git merge-base:--is-ancestor:*)",
      "Bash(git rev-list:*)",
      "Bash(git stash:list)",
      "Bash(git status:*)",
      "Bash(mkdir:*)",
      "Bash(pnpm build)",
      "Bash(pnpm check)",
      "Bash(pnpm fix)",
      "Bash(pnpm fix:staged)",
      "Bash(pnpm install)",
      "Bash(pnpm lint:*)",
      "Bash(pnpm list)",
      "Bash(pnpm test:*)",
      "Bash(pnpm type-check)",
      "Bash(pnpm run build:*)",
      "Bash(pnpm run lint)",
      "Bash(pnpm run test:*)",
      "Bash(pnpm dlx playwright test:*)",
      "Edit",
      "Glob",
      "Grep",
      "LS",
      "MultiEdit",
      "Read",
      "WebFetch",
      "WebSearch",
      "Write"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/etc/claude-code/hooks/prevent-main-push.sh",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "/etc/claude-code/hooks/prevent-no-verify.sh",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "/etc/claude-code/hooks/prevent-env-leakage.py",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "/etc/claude-code/hooks/prevent-bash-sensitive-args.py",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "Read|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "/etc/claude-code/hooks/prevent-sensitive-files.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**Step 3: Commit**

```bash
git add claude/managed-settings.json
git commit -m "feat: add Claude managed settings"
```

---

### Task 9: Create Security Hooks

**Files:**
- Create: `claude/hooks/prevent-main-push.sh`
- Create: `claude/hooks/prevent-no-verify.sh`
- Create: `claude/hooks/prevent-env-leakage.py`
- Create: `claude/hooks/prevent-bash-sensitive-args.py`
- Create: `claude/hooks/prevent-sensitive-files.py`
- Create: `claude/hooks/lib/patterns.py`

**Step 1: Create hooks directory structure**

```bash
mkdir -p claude/hooks/lib
```

**Step 2: Create prevent-main-push.sh**

```bash
#!/bin/bash
set -euo pipefail

# Prevent pushing directly to main/master branches
# Input: JSON with tool_input.command

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if echo "$COMMAND" | grep -qE 'git\s+push.*\s+(origin\s+)?(main|master)(\s|$)'; then
    echo '{"decision": "block", "reason": "Direct push to main/master branch is not allowed. Create a PR instead."}'
    exit 0
fi

echo '{"decision": "allow"}'
```

**Step 3: Create prevent-no-verify.sh**

```bash
#!/bin/bash
set -euo pipefail

# Prevent using --no-verify flag with git commands
# Input: JSON with tool_input.command

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if echo "$COMMAND" | grep -qE '\s--no-verify(\s|$)'; then
    echo '{"decision": "block", "reason": "The --no-verify flag is not allowed. Pre-commit hooks must run."}'
    exit 0
fi

echo '{"decision": "allow"}'
```

**Step 4: Create lib/patterns.py**

```python
"""Shared patterns for security hooks."""

import re

# Sensitive environment variable patterns
SENSITIVE_ENV_PATTERNS = [
    r'[A-Z_]*(?:SECRET|TOKEN|KEY|PASSWORD|CREDENTIAL|AUTH)[A-Z_]*',
    r'[A-Z_]*(?:API_KEY|PRIVATE_KEY|ACCESS_KEY)[A-Z_]*',
    r'(?:AWS|AZURE|GCP|GITHUB|OPENAI|ANTHROPIC)_[A-Z_]+',
]

# Sensitive file patterns
SENSITIVE_FILE_PATTERNS = [
    r'\.env(?:\.[^/]*)?$',
    r'\.pem$',
    r'\.key$',
    r'credentials\.json$',
    r'secrets\.json$',
    r'\.secrets/',
]

def is_sensitive_env_var(name: str) -> bool:
    """Check if environment variable name looks sensitive."""
    for pattern in SENSITIVE_ENV_PATTERNS:
        if re.match(pattern, name, re.IGNORECASE):
            return True
    return False

def is_sensitive_file(path: str) -> bool:
    """Check if file path looks sensitive."""
    for pattern in SENSITIVE_FILE_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True
    return False
```

**Step 5: Create prevent-env-leakage.py**

```python
#!/usr/bin/env python3
"""Prevent leaking sensitive environment variables in commands."""

import json
import re
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))
from patterns import is_sensitive_env_var

def main():
    input_data = json.load(sys.stdin)
    command = input_data.get("tool_input", {}).get("command", "")

    # Look for $VAR or ${VAR} patterns
    env_refs = re.findall(r'\$\{?([A-Z_][A-Z0-9_]*)\}?', command, re.IGNORECASE)

    for var in env_refs:
        if is_sensitive_env_var(var):
            print(json.dumps({
                "decision": "block",
                "reason": f"Command references sensitive environment variable: ${var}"
            }))
            return

    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
```

**Step 6: Create prevent-bash-sensitive-args.py**

```python
#!/usr/bin/env python3
"""Prevent sensitive data in bash command arguments."""

import json
import re
import sys
import shlex

def looks_like_secret(value: str) -> bool:
    """Heuristic check for secret-like values."""
    # Skip short values and common patterns
    if len(value) < 16:
        return False

    # Check for high entropy (mix of cases, numbers, special chars)
    has_upper = bool(re.search(r'[A-Z]', value))
    has_lower = bool(re.search(r'[a-z]', value))
    has_digit = bool(re.search(r'[0-9]', value))
    has_special = bool(re.search(r'[^A-Za-z0-9]', value))

    entropy_score = sum([has_upper, has_lower, has_digit, has_special])

    # Looks like base64 or hex encoded secret
    if re.match(r'^[A-Za-z0-9+/=]{20,}$', value) or re.match(r'^[a-fA-F0-9]{32,}$', value):
        return True

    # High entropy string
    if entropy_score >= 3 and len(value) >= 24:
        return True

    return False

def main():
    input_data = json.load(sys.stdin)
    command = input_data.get("tool_input", {}).get("command", "")

    try:
        tokens = shlex.split(command)
    except ValueError:
        # Malformed command, let it through for bash to handle
        print(json.dumps({"decision": "allow"}))
        return

    for token in tokens:
        # Check for inline secrets in common patterns
        if '=' in token:
            key, _, value = token.partition('=')
            if looks_like_secret(value):
                print(json.dumps({
                    "decision": "block",
                    "reason": f"Command appears to contain a hardcoded secret in argument: {key}=..."
                }))
                return
        elif looks_like_secret(token):
            print(json.dumps({
                "decision": "block",
                "reason": "Command appears to contain a hardcoded secret value"
            }))
            return

    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
```

**Step 7: Create prevent-sensitive-files.py**

```python
#!/usr/bin/env python3
"""Prevent reading/writing sensitive files."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from patterns import is_sensitive_file

def main():
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})

    # Handle different tool input structures
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    if is_sensitive_file(file_path):
        print(json.dumps({
            "decision": "block",
            "reason": f"Access to sensitive file is not allowed: {file_path}"
        }))
        return

    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
```

**Step 8: Make hooks executable and commit**

```bash
chmod +x claude/hooks/*.sh claude/hooks/*.py
git add claude/hooks/
git commit -m "feat: add Claude security hooks"
```

---

## Phase 6: CI/CD

### Task 10: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/publish.yml`

**Step 1: Create workflows directory**

```bash
mkdir -p .github/workflows
```

**Step 2: Create publish.yml**

```yaml
name: Publish Docker Image

on:
  release:
    types: [published]
  push:
    branches: [main]
    paths:
      - 'Dockerfile'
      - 'scripts/**'
      - 'config/**'
      - 'claude/**'
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=sha,prefix=
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            TZ=Etc/UTC
```

**Step 3: Commit**

```bash
git add .github/workflows/publish.yml
git commit -m "ci: add Docker image publish workflow"
```

---

## Phase 7: Consumer Template

### Task 11: Create Example Consumer Configuration

**Files:**
- Create: `examples/devcontainer.json`
- Create: `examples/allowed-domains.txt`

**Step 1: Create examples directory**

```bash
mkdir -p examples
```

**Step 2: Create example devcontainer.json**

```json
{
  "name": "${localEnv:PROJECT_NAME}-${localWorkspaceFolderBasename}",
  "image": "ghcr.io/OWNER/claude-devcontainer:latest",
  "runArgs": [
    "--name=${localEnv:PROJECT_NAME}-${localWorkspaceFolderBasename}",
    "--cap-add=NET_ADMIN",
    "--cap-add=NET_RAW",
    "--cap-add=SYSLOG",
    "--label=dev.orbstack.domains=${localWorkspaceFolderBasename}.${localEnv:PROJECT_NAME}.local",
    "--label=dev.orbstack.http-port=3000"
  ],
  "remoteUser": "node",
  "workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=delegated",
  "workspaceFolder": "/workspace",
  "mounts": [
    "source=${localEnv:PROJECT_NAME}-bashhistory-${localWorkspaceFolderBasename},target=/commandhistory,type=volume",
    "source=${localEnv:PROJECT_NAME}-claude-config,target=/home/node/.claude,type=volume",
    "source=${localEnv:PROJECT_NAME}-shared-config,target=/home/node/.config,type=volume",
    "source=${localEnv:PROJECT_NAME}-playwright-cache,target=/home/node/.cache/ms-playwright,type=volume",
    "source=pnpm-store,target=/workspace/.pnpm-store,type=volume",
    "source=${localEnv:PROJECT_NAME}-node-modules-${localWorkspaceFolderBasename},target=/workspace/node_modules,type=volume"
  ],
  "containerEnv": {
    "PROJECT_NAME": "${localEnv:PROJECT_NAME}",
    "CLAUDE_INSTANCE": "${localWorkspaceFolderBasename}",
    "NODE_OPTIONS": "--max-old-space-size=4096",
    "CLAUDE_CONFIG_DIR": "/home/node/.claude",
    "PNPM_HOME": "/pnpm",
    "npm_config_store_dir": "/workspace/.pnpm-store",
    "npm_config_virtual_store_dir": ".pnpm-store/container/${localWorkspaceFolderBasename}"
  },
  "postCreateCommand": "/usr/local/bin/post-create.sh"
}
```

**Step 3: Create example allowed-domains.txt**

```
# Project-specific domains
# Add your API endpoints, services, etc.

# Example: Convex backend
# api.convex.dev
# your-project.convex.cloud

# Example: Authentication provider
# clerk.com
# api.clerk.com

# Example: Additional APIs
# api.your-service.com
```

**Step 4: Update README with examples reference**

Append to README.md:

```markdown

## Examples

See the `examples/` directory for:
- `devcontainer.json` - Full consumer configuration template
- `allowed-domains.txt` - Example project-specific domain allowlist

## Host-Side Setup

Before opening a devcontainer, set the `PROJECT_NAME` environment variable:

\`\`\`bash
# Derive from git remote (recommended)
export PROJECT_NAME=$(git config --get remote.origin.url | sed -E 's#.*/([^/]+?)(\.git)?$#\1#' | tr '[:upper:]' '[:lower:]')

# Or set manually
export PROJECT_NAME=my-project
\`\`\`

Then open with VS Code or devcontainer CLI:

\`\`\`bash
devcontainer open .
\`\`\`
```

**Step 5: Commit**

```bash
git add examples/ README.md
git commit -m "docs: add consumer examples and setup instructions"
```

---

## Phase 8: Final Verification

### Task 12: Local Build Test

**Step 1: Build the image locally**

```bash
docker build -t claude-devcontainer:local .
```

Expected: Build completes successfully

**Step 2: Verify image contents**

```bash
# Check scripts are present
docker run --rm claude-devcontainer:local ls -la /usr/local/bin/

# Check claude config is present
docker run --rm claude-devcontainer:local ls -la /etc/claude-code/

# Check allowed domains
docker run --rm claude-devcontainer:local cat /etc/allowed-domains.txt
```

Expected: All files present with correct permissions

**Step 3: Test derive-project-name script**

```bash
# In a git repo
docker run --rm -v $(pwd):/workspace claude-devcontainer:local /usr/local/bin/derive-project-name.sh /workspace
```

Expected: Outputs the project name derived from git remote

---

### Task 13: Create Initial Release

**Step 1: Create git tag**

```bash
git tag -a v1.0.0 -m "Initial release"
```

**Step 2: Push to GitHub**

```bash
git remote add origin git@github.com:OWNER/claude-devcontainer.git
git push -u origin main
git push origin v1.0.0
```

**Step 3: Create GitHub release**

```bash
gh release create v1.0.0 --title "v1.0.0" --notes "Initial release of Claude DevContainer base image"
```

Expected: GitHub Actions workflow triggers and publishes image to ghcr.io

---

## Summary

After completing all tasks, you will have:

1. **Repository**: `claude-devcontainer` with full source
2. **Published image**: `ghcr.io/OWNER/claude-devcontainer:latest`
3. **Consumer template**: Ready-to-copy devcontainer.json
4. **Security**: Firewall + Claude hooks enforced by default
5. **Extensibility**: Projects add domains via `.devcontainer/allowed-domains.txt`

**To use in any project:**

1. Copy `examples/devcontainer.json` to `.devcontainer/devcontainer.json`
2. Update `OWNER` to your GitHub username/org
3. Optionally add `.devcontainer/allowed-domains.txt`
4. Set `PROJECT_NAME` env var and open in devcontainer
