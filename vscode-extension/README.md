# Clembot VS Code Extension

The **Clembot VS Code Bridge** allows Clembot to inspect and modify code in real-time through voice commands.

## Features
- Reads active editor document and selection
- Jumps to requested line numbers ("Go to line 45")
- Applies surgical code modifications without blind keyboard typing
- Displays unified diffs before applying changes
- Runs scripts directly in the integrated terminal ("Run this Python file")
- Triggers undo/redo safely

## How it works
The extension connects via local HTTP requests to Clembot's IPC server (`127.0.0.1:25362`). No external cloud connection is required.

## Installation into VS Code
1. Open VS Code.
2. Open this folder `vscode-extension/`.
3. Press `F5` to launch Extension Development Host, or run:
   ```bash
   npm install
   npm run compile
   npx vsce package
   code --install-extension clembot-vscode-1.0.0.vsix
   ```
