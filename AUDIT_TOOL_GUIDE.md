# ChatGPT Audit Tool (`chatgpt-audit`) — User Guide & Reference

The `chatgpt-audit` CLI tool is an automated, IDE-agnostic self-healing pipeline. It connects your local Git workflow to ChatGPT review sessions and automatically feeds extracted prompts into **Antigravity IDE**.

---

## 🚀 Quick Start

### 1. Installation in Project
To set up `chatgpt-audit` in your project repository (e.g. `F:\QPort`):
```powershell
chatgpt-audit install --project "F:\QPort"
```
This creates:
- `.audit/config.json` (Configuration settings)
- `.git/hooks/post-commit` (Git post-commit hook)
- `reviews/` (Review outputs directory)
- `AUDIT_TOOL_GUIDE.md` (User guide reference)

---

## 🛠️ CLI Commands

| Command | Usage | Description |
| :--- | :--- | :--- |
| **`install`** | `chatgpt-audit install --project .` | Initializes `.audit/config.json` and Git post-commit hook. |
| **`run`** | `chatgpt-audit run --project . --sha HEAD` | Audits the specified commit via Edge automation. |
| **`watch`** | `chatgpt-audit watch --project . --interval 10` | Continuously polls ChatGPT for new responses every N seconds. |
| **`status`** | `chatgpt-audit status --project .` | Displays pending remediation or next task status. |
| **`clear`** | `chatgpt-audit clear --project .` | Clears pending task & remediation state files. |
| **`test-copy`** | `chatgpt-audit test-copy --project .` | Verifies copying implementation.md to Antigravity chatbox without `/goal`. |

---

## ⚙️ Configuration (`.audit/config.json`)

```json
{
  "chatgpt_url": "https://chatgpt.com/...",
  "audit_prompt": "audit code (i need the next task prompt if you are audit success, otherwise give current prompt task)",
  "browser": "edge",
  "model": "gemini-3.6-flash",
  "target_conversation": "read principle.md to get knowledge about our next project to do",
  "output_dir": "reviews",
  "ide": "auto"
}
```

---

## 🔄 Autonomous Workflow & Features

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                        Antigravity                          │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ 1. Code implementation & git commit
                                 ▼
                             post-commit
                                 │ 2. Triggers chatgpt-audit
                                 ▼
                           chatgpt-audit
                                 │ 3. Connects via Edge (port 9222 / dedicated profile)
                                 ▼
                              ChatGPT
                                 │ 4. Extracts prompt from QPORT_MACHINE_BEGIN block
                                 ▼
                     reviews/implementation.md
                                 │ 5. Auto-pastes clean prompt command into Antigravity
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                        Antigravity                          │
  │            (Continues to next task automatically)           │
  └─────────────────────────────────────────────────────────────┘
```

### Key Automation Features:
1. **Sentinel & Machine Block Support**: Parses `QPORT_MACHINE_BEGIN` / `QPORT_MACHINE_END` blocks as well as legacy formats.
2. **Token Optimization**: Compares latest ChatGPT response content with `reviews/review_HEAD.md` and reuses existing reviews when unchanged.
3. **Clean Prompt Auto-Submission**: Saves extracted multi-line prompt to `reviews/implementation.md` and pastes `Please read and implement the specification and instructions from reviews/implementation.md` without using terminal-incompatible `/goal`.
4. **Browser Isolation**: Uses port `9222` or dedicated profile `~/.chatgpt-audit-profile`.
5. **Target Conversation Support**: Synchronizes audit prompts directly into workspace `AGENTS.md` and `reviews/implementation.md` so designated Antigravity conversations automatically ingest the task.
6. **Error Traceback & Process Logging**: Automatically logs every step from start to end in `audit_process.log` and error tracebacks to `reviews/error_trace.log`.
