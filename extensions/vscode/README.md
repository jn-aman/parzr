# Parzr for VS Code

Offline grammar, spelling and punctuation checks and deliberate tone changes, using the local macOS Parzr engine. Optional: the Parzr app already works in VS Code and Cursor through macOS Accessibility, but only with a review marker. This extension adds real underlines, the Problems panel and quick fixes.

- Markdown, plain text, MDX and commit messages are checked after 180 ms of idle time. Press Cmd+. on an underline for **Change to ...** or **Parzr: Fix all grammar**.
- Select prose and run **Parzr: Improve selected text** (Alt+Space) to pick Fix, Professional, Friendly, Concise or Direct and review the diff before Apply or Copy. Code selections need a prose confirmation.

Install Parzr.app in Applications first, then install [`parzr-vscode.vsix`](https://github.com/jn-aman/parzr/releases/latest/download/parzr-vscode.vsix) from the latest release: Extensions view, "..." menu, **Install from VSIX**. Set `parzr.enginePath` if Parzr is somewhere else. Keep the app's **Check prose in VS Code and Cursor** setting off while you use this extension. Alt+Space is configurable in Keyboard Shortcuts; avoid a conflict with the native macOS shortcut. Local macOS workspaces only. Full steps: [integrations](https://github.com/jn-aman/parzr/blob/main/docs/integrations.md#install-the-optional-extensions).

The engine and extension are open source, Apache-2.0. No network model, runtime account or writing telemetry.
