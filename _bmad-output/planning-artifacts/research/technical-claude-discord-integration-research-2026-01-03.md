---
stepsCompleted: [1, 2]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Claude-Discord Integration for BMAD Research'
research_goals: 'Find existing, well-adopted Claude-Discord integration (MCP server preferred) to access and search Discord conversations for BMAD research purposes'
user_name: 'Node'
date: '2026-01-03'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical - Claude-Discord Integration

**Date:** 2026-01-03
**Author:** Node
**Research Type:** Technical

---

## Research Overview

This technical research evaluates options for connecting Claude to Discord, specifically to enable search and discovery of conversations for BMAD-style research purposes.

---

## Technical Research Scope Confirmation

**Research Topic:** Claude-Discord Integration for BMAD Research
**Research Goals:** Find existing, well-adopted Claude-Discord integration (MCP server preferred) to access and search Discord conversations for BMAD research purposes

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Security Considerations - OAuth flows, token management, 3rd party trust

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-01-03

---

## Technology Stack Analysis

### MCP (Model Context Protocol) Overview

The Model Context Protocol (MCP) is Anthropic's standard for connecting AI assistants to external data sources and tools. MCP servers act as bridges allowing Claude to interact with third-party services through a standardized interface.

**Key Finding:** Discord is **NOT** included in the official MCP reference servers maintained by Anthropic. The official servers include only: Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, and Time.
_Source: [GitHub - modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)_

This means all Discord MCP integrations are **community-built third-party solutions**.

### Available Discord MCP Servers

#### 1. barryyip0625/mcp-discord (RECOMMENDED for Search)

| Attribute | Value |
|-----------|-------|
| **Stars** | 58 |
| **Forks** | 35 |
| **Language** | TypeScript (92.7%) |
| **Last Release** | v1.3.5 (October 2025) |
| **License** | Not specified |

**Key Feature:** Includes explicit `discord_search_messages` tool for searching messages within a server.

**Available Tools:**
- `discord_search_messages` - Search messages in a server
- `discord_login` - Bot authentication
- `discord_list_servers` - List accessible servers
- `discord_read_messages` - Read channel messages
- `discord_send_message` - Send messages
- Forum post creation/management
- Webhook management

**Installation:** `npx mcp-discord --config ${DISCORD_TOKEN}` or Docker
_Source: [GitHub - barryyip0625/mcp-discord](https://github.com/barryyip0625/mcp-discord)_

---

#### 2. v-3/discordmcp (Most Popular)

| Attribute | Value |
|-----------|-------|
| **Stars** | 162 |
| **Forks** | 61 |
| **Language** | TypeScript (100%) |
| **Commits** | 2 |
| **License** | MIT |

**Features:**
- `send-message` - Send messages to channels
- `read-messages` - Retrieve up to 100 recent messages
- Automatic server/channel discovery
- Simple setup

**Limitation:** No explicit search functionality - only reads recent messages.
_Source: [GitHub - v-3/discordmcp](https://github.com/v-3/discordmcp)_

---

#### 3. hanweg/mcp-discord (Python Option)

| Attribute | Value |
|-----------|-------|
| **Stars** | 136 |
| **Forks** | 43 |
| **Language** | Python (94.5%) |
| **Commits** | 25 |
| **License** | MIT |

**Features:**
- `read_messages` - Read message history
- Server/channel management
- Role management
- Moderation tools

**Best for:** Users preferring Python ecosystem
_Source: [GitHub - hanweg/mcp-discord](https://github.com/hanweg/mcp-discord)_

---

### Discord API Constraints

**Rate Limits:**
- Maximum 100 messages per API request
- Heavy fetching (10,000+ messages) requires ~100 requests and triggers rate limiting
- Libraries implement automatic backoff but fetching is slow for large histories

**Permissions Required:**
- `READ_MESSAGE_HISTORY`
- `VIEW_CHANNEL`
- Bot must be invited to target server with appropriate permissions

**Message Content Intent:**
- Discord requires enabling "Message Content Intent" in Developer Portal
- Without this, bot cannot read message content (only metadata)

_Source: [Discord API Documentation](https://discord.com/developers/docs/resources/channel#get-channel-messages)_

---

### Alternative Approach: Static Export

#### DiscordChatExporter

**What:** Open-source tool to export Discord chat history to files (HTML, JSON, CSV, TXT).

| Attribute | Value |
|-----------|-------|
| **Repository** | Tyrrrz/DiscordChatExporter |
| **Platforms** | Windows, Linux, macOS, Docker |
| **Output Formats** | HTML, JSON, CSV, Plain Text |

**Workflow:**
1. Export channel/server to JSON files using CLI or GUI
2. Use DiscordChatExporter-frontend to search/browse exports
3. Manually provide relevant context to Claude

**⚠️ Important Warning:** Using personal account tokens for automation violates Discord ToS and risks account termination. Bot tokens are the approved approach.

_Source: [GitHub - Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter)_

---

### Technology Comparison Matrix

| Solution | Search Capability | Real-time | Setup Complexity | Trust Level |
|----------|------------------|-----------|------------------|-------------|
| barryyip0625/mcp-discord | ✅ Native search | ✅ Yes | Medium | Community |
| v-3/discordmcp | ❌ Recent only | ✅ Yes | Low | Community |
| hanweg/mcp-discord | ❌ Recent only | ✅ Yes | Medium | Community |
| DiscordChatExporter | ✅ Offline search | ❌ No | Low | Well-established |

<!-- Content will be appended sequentially through research workflow steps -->
