# Reference Repository Analysis: Majesty v0.3 (macOS) vs Clembot (Windows 10/11)

## 1. Executive Summary

The reference repository (`https://github.com/Kyron-data-tech/Majesty`) is a local-first macOS voice assistant built with Swift and SwiftUI. It uses macOS-specific frameworks (Accessibility API, `NSWorkspace`, `AppKit`, `NSPasteboard`, Apple Speech Framework, AppleScript) and communicates with local Ollama (`qwen3:8b`) to plan and execute desktop actions.

**Clembot** is designed specifically for **Windows 10 and 11**. Rather than directly translating macOS idioms, Clembot extracts Majesty's architectural strengths (fast command routing, screen context capture, safety confirmation policy, intent planning) and completely re-engineers the platform layer for Windows using Python, `pywin32`, Windows UI Automation, native Windows known folders, Windows Recycle Bin, Windows System Tray, and an advanced **VS Code Extension + local IPC architecture** for precise code editing.

---

## 2. Architecture Discovered in Majesty

Majesty is structured around an event-driven loop in `AssistantController.swift`:

```
Microphone (AVAudioEngine)
       │
       ▼
Apple Speech Framework (SFSpeechRecognizer)
       │
       ▼
Wake Phrase Matcher ("Majesty") / Dictation Mode
       │
       ├──────────────────────────────────────────┐
       ▼ [Fast Match]                             ▼ [Complex NLP]
FastCommandRouter                         Capture macOS Accessibility Context
(Deterministic zero-latency)              (AXUIElement, front app, window title,
       │                                   focused element, browser URL, selection)
       │                                          │
       │                                          ▼
       │                                  Ollama Client (Qwen3 8B JSON Plan)
       │                                          │
       └──────────────────┬───────────────────────┘
                          ▼
                  Safety Policy Check
           (requires spoken confirmation for
         trash, move, rename, terminal, send)
                          │
                          ▼
                    ActionExecutor
       ┌──────────────────┼──────────────────────┐
       ▼                  ▼                      ▼
FileService       AccessibilityService      AppCatalog / Shell
(Finder/POSIX)     (CGEvent/AXUIElement)    (NSWorkspace/AppleScript)
```

---

## 3. Main Features & Important Files in Majesty

| File | Purpose | Key Responsibilities |
|---|---|---|
| `Majesty/AssistantController.swift` | Master Coordinator | Manages listening states, confirmation prompts, dictation buffer, and history. |
| `Majesty/FastCommandRouter.swift` | Fast Path Router | Handles ~100 common phrases (tabs, windows, volume, clipboard, standard folders) without calling the LLM. |
| `Majesty/AgentModels.swift` | Data Structures | Defines `AgentPlan`, `AgentAction`, `ScreenContext`, `UIElementSummary`, and error types. |
| `Majesty/ActionExecutor.swift` | Action Runner | Dispatches and executes validated actions (keystrokes, mouse events, shell runs, file moves). |
| `Majesty/FileService.swift` | File Manager | Resolves standard Mac folders (`~/Desktop`, `~/Downloads`), performs bounded fuzzy file search, moves to Trash. |
| `Majesty/AccessibilityService.swift`| UI & Screen Context | Inspects the active window, focused UI controls, pointer element, and browser URL using `AXUIElement`. |
| `Majesty/SafetyPolicy.swift` | Safety Layer | Flags destructive actions (`trash_path`, `terminal_run`, `move_path`, `quit_app`) to require confirmation. |
| `Majesty/OllamaClient.swift` | LLM Planner | Calls local Ollama `api/chat` with structured JSON schema output using `qwen3:8b`. |
| `Majesty/AppCatalog.swift` | App Resolver | Maps spoken app names to bundle identifiers and executable locations. |
| `Majesty/SpeechService.swift` | Speech Recognition | Uses Apple Speech framework for wake word detection and speech-to-text. |
| `Majesty/SpeechOutputService.swift`| Text-to-Speech | Uses `NSSpeechSynthesizer` / `AVSpeechSynthesizer` for voice replies. |

---

## 4. macOS-Specific Parts vs. Windows 10/11 Replacements

| macOS Mechanism in Majesty | Limitations on macOS | Windows 10/11 Native Replacement in Clembot | Clembot Benefit |
|---|---|---|---|
| `AXUIElement` / Accessibility API | Requires system accessibility permissions; fragile on custom web views | `pywin32` (`win32gui`, `win32con`, `win32process`), `ctypes`, and Windows UI Automation (`uiautomation`) | Native Windows OS integration, active window title, handle, process ID, and control tree. |
| `NSWorkspace.shared.runningApplications` & `openApplication` | Tied to `.app` bundles and macOS bundle IDs | Windows App Resolver (`win32api`, Registry App Paths, Start Menu shortcuts, system `PATH`) | Launches both desktop Win32 apps, Microsoft Store apps, and CLI tools seamlessly. |
| `CGEvent` mouse & keyboard synthesis | Subject to macOS security sandboxes and synthetic event blocking | Windows `SendInput` API via `ctypes` and `pyautogui` with safety fail-safes | High reliability across all Windows apps and desktop environments. |
| AppleScript (`osascript`) for volume & scripts | Platform-exclusive scripting language | Windows EndpointVolume API / Core Audio APIs (`pycaw` / `win32api` / multimedia keys) | Direct Windows audio control (mute, unmute, set volume) without shell overhead. |
| `FileManager.default.trashItem` | Moves to macOS `.Trash` | `Send2Trash` (uses Windows `SHFileOperation` / `IFileOperation`) | Safely moves files to the Windows Recycle Bin with full restore capability. |
| Standard paths (`/Applications`, `~/Library`) | Hardcoded macOS directory structure | Windows Known Folders API (`SHGetKnownFolderPath`) + dynamic environment variables | Resolves `%USERPROFILE%`, Desktop, Documents, Downloads, Music, Pictures, Videos, OneDrive, and drive roots (`C:\`, `D:\`). |
| Active Finder inspection | Uses AppleScript or accessibility to inspect Finder tabs | Windows `Shell.Application` COM automation | Directly queries active File Explorer windows to get the currently viewed directory path! |
| SFSpeechRecognizer & NSSpeechSynthesizer | Exclusive to macOS / iOS | Modular Speech Recognition (`SpeechRecognition` / SoundDevice / Vosk / Whisper) & Windows SAPI (`pyttsx3`) | 100% offline SAPI voices on all Windows installations, with optional cloud providers. |

---

## 5. Critical Flaws in Majesty's Code Editor Integration & Clembot's Solution

In Majesty:
- VS Code control was implemented primarily through blind keyboard shortcuts:
  - `vscode_quick_open`: sends `cmd+p` then blindly types a filename.
  - `vscode_search`: sends `cmd+shift+f` then types search query.
  - `vscode_toggle_terminal`: sends `ctrl+\``.
- Majesty **could not read the open file, could not inspect the cursor, could not jump to a specific function reliably, and could not generate or preview code diffs.**

In Clembot:
- We implement a **first-class VS Code Extension** (`clembot-vscode`) communicating with Clembot's backend via local HTTP/WebSocket IPC (`http://127.0.0.1:25362`).
- Provides deep programmatic capabilities:
  1. `get_workspace`: retrieves active project folders.
  2. `get_active_editor`: file name, full path, language, visible range.
  3. `read_document`: full source code or line-range extraction.
  4. `get_selection`: highlighted text and cursor position.
  5. `jump_to_line`: programmatic cursor positioning.
  6. `apply_edit`: surgical range replacement, insertion, or deletion.
  7. `show_diff`: side-by-side diff preview in VS Code or Clembot GUI.
  8. `save_document` & `run_code`: execute current script in terminal.
  9. `undo`: programmatic editor undo.
- When VS Code extension is not installed or editor is closed, Clembot falls back gracefully to safe programmatic file editing with unified diffs and user confirmation.

---

## 6. Features Reused & Features Redesigned

### Reused Architectural Concepts
1. **Two-Tier Router**: Deterministic fast router for common commands (low latency, zero AI cost) paired with an LLM planner for natural language.
2. **Strict Safety Policy**: Protected operations (permanent deletes, large moves, terminal execution) strictly demand user confirmation.
3. **Structured Plan Schema**: LLM outputs a validated JSON plan with typed actions rather than executing raw, unverified shell commands.
4. **Context-Aware Intent Resolution**: Uses active window, active app, and clipboard context to interpret relative instructions ("this", "there", "copy this").

### Redesigned / Brand New in Clembot
1. **Modern Windows Fluent GUI**: Built with PySide6 / modern UI styling, featuring an animated audio pulse, live transcription, activity log, and interactive confirmation modals.
2. **Windows System Tray**: Native tray icon with Start/Stop listening, mute, open dashboard, and launch-on-startup settings.
3. **Explorer Path Detection**: Queries active Windows File Explorer tabs via COM to execute commands in the active folder.
4. **Recycle Bin Integration**: All file deletions default to Windows Recycle Bin via `send2trash`.
5. **Interactive Code Diff Engine**: Side-by-side before/after preview before applying major code modifications.
6. **Multi-Model AI Layer**: Pluggable provider architecture supporting local Ollama, OpenAI, Google Gemini, Anthropic Claude, and offline rule fallback.
7. **Comprehensive Windows Application Resolver**: Scans Start Menu shortcuts, App Paths registry, and PATH.
