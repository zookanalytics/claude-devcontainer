---
stepsCompleted: [1, 2, 3, 4, 5]
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

---

## Integration Patterns Analysis

### MCP Architecture Overview

MCP follows a client-server architecture with four core components:

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP HOST                              │
│              (Claude Desktop / Claude Code)                  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Client  │  │  Client  │  │  Client  │   (1:1 mapping)  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼─────────────────────────┘
        │             │             │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │ Discord │   │  GitHub │   │Filesystem│   MCP Servers
   │  Server │   │  Server │   │  Server  │
   └────┬────┘   └─────────┘   └──────────┘
        │
   ┌────▼────┐
   │ Discord │
   │   API   │
   └─────────┘
```

**Protocol Layers:**
- **Data Layer:** JSON-RPC 2.0 based protocol for client-server communication
- **Transport Layer:** Communication mechanisms (stdio or HTTP)

_Source: [Model Context Protocol - Architecture](https://modelcontextprotocol.io/docs/learn/architecture)_

---

### Transport Mechanisms

#### Stdio Transport (Recommended for Local Discord MCP)

The stdio transport is used when client and server run on the same machine. The MCP client launches the MCP server as a subprocess and communicates via stdin/stdout.

**Characteristics:**
- No network overhead - optimal performance
- Security relies on OS user permissions
- Process isolation model
- Best for local integrations

**For Discord MCP servers:** All three evaluated servers use stdio transport, meaning they run as local processes on your machine.

_Source: [MCP Transports Documentation](https://modelcontextprotocol.info/docs/concepts/transports/)_

---

### Claude Code Integration Pattern

**Adding Discord MCP to Claude Code:**

```bash
# Method 1: CLI wizard (recommended)
claude mcp add discord-mcp \
  -e DISCORD_TOKEN=your_bot_token \
  -- npx mcp-discord

# Method 2: JSON configuration in ~/.claude.json
{
  "mcpServers": {
    "discord": {
      "command": "npx",
      "args": ["mcp-discord"],
      "env": {
        "DISCORD_TOKEN": "your_bot_token"
      }
    }
  }
}
```

**Verification:** Run `/mcp` in Claude Code to see connected servers.

_Source: [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)_

---

### Discord Authentication Flow

#### Bot Token Authentication (Required for MCP)

Discord bots authenticate using a **Bot Token** - not OAuth2 user tokens.

**Key Differences:**

| Aspect | Bot Token | OAuth2 User Token |
|--------|-----------|-------------------|
| **Access** | Full API access without bearer tokens | Limited by OAuth2 scopes |
| **Guild Access** | Must be invited to guilds | Can access user's existing guilds |
| **Rate Limits** | Separate bot rate limits | User rate limits |
| **Lifespan** | Permanent until regenerated | 7-day access token + refresh |
| **ToS Compliance** | ✅ Fully compliant | ❌ Automation forbidden |

**Bot Authorization URL Pattern:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=PERMISSIONS_INTEGER
```

_Source: [Discord OAuth2 Documentation](https://discord.com/developers/docs/topics/oauth2)_

---

### Data Flow Architecture

**For BMAD Discord Search Use Case:**

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Claude Code   │────▶│  Discord MCP    │────▶│   Discord API    │
│                 │     │     Server      │     │                  │
│  "Search for    │     │                 │     │  GET /channels   │
│   BMAD posts"   │◀────│ discord_search  │◀────│  /{id}/messages  │
│                 │     │   _messages     │     │                  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
        │                       │                       │
        │                       │                       │
   JSON-RPC 2.0             Bot Token             Discord CDN
    via stdio               Auth Header           (attachments)
```

**Message Flow:**
1. User asks Claude to search Discord
2. Claude invokes `discord_search_messages` tool via MCP
3. MCP server authenticates with Discord using bot token
4. Discord API returns matching messages (max 100 per request)
5. Results returned to Claude for analysis

---

### Required Discord Bot Setup

**Step 1: Create Discord Application**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → Name it (e.g., "BMAD Research Bot")
3. Navigate to Bot section → Create Bot

**Step 2: Enable Required Intents**
- ✅ MESSAGE CONTENT INTENT (required to read message content)
- ✅ PRESENCE INTENT (optional)
- ✅ SERVER MEMBERS INTENT (optional)

**Step 3: Generate Bot Token**
- Reset Token → Copy and store securely
- ⚠️ Never commit token to git

**Step 4: Invite Bot to BMAD Discord**
- Generate invite URL with required permissions:
  - Read Message History
  - View Channels
- Requires server admin/mod approval

---

### Claude Desktop Integration Pattern

**Configuration file locations:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Example Configuration:**
```json
{
  "mcpServers": {
    "discord": {
      "command": "npx",
      "args": ["mcp-discord"],
      "env": {
        "DISCORD_TOKEN": "YOUR_BOT_TOKEN"
      }
    }
  }
}
```

_Source: [Claude Desktop MCP Setup Guide](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)_

---

## Security & Compliance Assessment

### Discord ToS Compliance Matrix

| Approach | ToS Compliant | Ban Risk | Scalable |
|----------|---------------|----------|----------|
| Bot Token + MCP | ✅ Yes | None | ✅ Yes |
| User Token / Self-bot | ❌ **No** | **High - account termination** | ✅ Yes |
| OAuth2 Bearer Token | N/A | N/A | Cannot read messages |
| Chrome Extensions | ⚠️ Grey area | Low (manual use) | ❌ Manual only |

### Discord's Official Policy on Self-Bots

> "Automating normal user accounts (generally called 'self-bots') outside of the OAuth2/bot API is forbidden, and can result in an account termination if found."

_Source: [Discord - Automated User Accounts](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots)_

**Key Points:**
- User token automation is explicitly prohibited
- Bot tokens are the only approved method for automation
- Violations result in warnings → temporary bans → permanent termination
- Discord actively detects and enforces this policy

### Chrome Extension Risk Assessment

Extensions like [Discordmate](https://discordmate.com/) and [Discrub](https://github.com/prathercc/discrub-ext) operate by:
- Using your logged-in browser session (your user token)
- Making API calls on your behalf
- Technically automating user account actions

**Practical Risk:**
- Low for occasional manual exports
- Not truly automated or scalable
- Technically violates ToS
- Could trigger detection if used heavily

### MCP Server Security Considerations

**Third-Party Trust:**
- All Discord MCP servers are community-built (not Anthropic-maintained)
- Code should be audited before use
- Bot token is stored in environment variables (never in code)

**Token Security Best Practices:**
- Store token in `.env` file or environment variable
- Never commit tokens to version control
- Regenerate token if potentially exposed
- Use minimal required permissions

_Source: [MCP Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices)_

---

## Critical Blocker Identified

### The Bot Requirement Problem

**All ToS-compliant, scalable solutions require:**
1. Creating a Discord Bot application
2. Getting the bot **invited to the target server by an admin**
3. Server admin approval for bot access

**For BMAD Discord specifically:**
- You would need to request bot access from BMAD server administrators
- This is a prerequisite before any technical implementation
- Without admin approval, no compliant automated solution exists

---

## Viable Alternatives (Without Bot Access)

### Option 1: Manual Chrome Extension Export

**Tools:**
- [Discordmate](https://chromewebstore.google.com/detail/discordmate-discord-chat/ofjlibelpafmdhigfgggickpejfomamk) - Free, exports to CSV/HTML
- [Discrub](https://github.com/prathercc/discrub-ext) - Open source, exports to HTML/CSV/JSON

**Workflow:**
1. Open Discord in browser
2. Navigate to showcase-built-with-bmad channel
3. Use extension to export messages
4. Search exported files manually or with local tools
5. Copy relevant content to Claude

**Pros:** No bot required, works immediately
**Cons:** Manual, not integrated, grey area ToS

### Option 2: Periodic Static Export + Filesystem MCP

**Workflow:**
1. Periodically export channel using extension/DiscordChatExporter
2. Store JSON exports in local folder
3. Use Claude's built-in Filesystem MCP to search exports
4. Claude can read and analyze exported conversations

**Pros:** Semi-automated search once exported
**Cons:** Stale data, requires periodic manual refresh

### Option 3: Request Bot Access

**If feasible:**
1. Reach out to BMAD Discord admins
2. Explain read-only research use case
3. If approved, implement MCP solution with barryyip0625/mcp-discord

**Pros:** Only fully compliant scalable solution
**Cons:** Requires admin approval, may not be granted

---

## Executive Summary

### Research Question
Can Claude be connected to Discord to search BMAD showcase conversations without requiring bot server access?

### Answer
**No.** There is no scalable, ToS-compliant solution that avoids the bot requirement.

### Key Findings

1. **MCP servers exist** for Discord-Claude integration, but all require bot tokens
2. **Bot tokens require server admin approval** to add the bot
3. **User token automation** (self-bots) is explicitly forbidden by Discord ToS
4. **Chrome extensions** work for manual export but are not scalable and technically violate ToS
5. **No official Discord MCP** exists from Anthropic - all are community-built

### Recommendation

**For immediate use:** Chrome extension (Discordmate or Discrub) for manual, occasional exports when researching BMAD showcase content.

**For scalable solution:** Request bot access from BMAD Discord administrators. This is the only path to a compliant, integrated Claude-Discord workflow.

---

## Sources

- [GitHub - modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- [GitHub - barryyip0625/mcp-discord](https://github.com/barryyip0625/mcp-discord)
- [GitHub - v-3/discordmcp](https://github.com/v-3/discordmcp)
- [GitHub - hanweg/mcp-discord](https://github.com/hanweg/mcp-discord)
- [GitHub - Tyrrrz/DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter)
- [Discord OAuth2 Documentation](https://discord.com/developers/docs/topics/oauth2)
- [Discord Self-Bot Policy](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots)
- [Model Context Protocol - Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)
- [Claude Desktop MCP Setup](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)
- [MCP Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices)
