# Clembot — A Powerful Windows Voice Assistant

**Clembot** is a production-grade, local-first voice assistant engineered specifically for **Windows 10 and Windows 11**. It enables users to operate their PC, navigate directories, control web browsers, manage active windows, and perform surgical, AST-aware code modifications in VS Code entirely through natural speech.

---

## Key Highlights

- 🎙 **Natural Activation & Sleep**: Activate by saying *"Clembot activate yourself"* and deactivate by saying *"Clembot deactivate"*.
- 🔊 **Fuzzy Wake Word**: Phonetic + Levenshtein matching tolerates real-world mishearings — *"clemburt"*, *"clem ber"*, *"clembur"*, *"climbers"* all correctly resolve to *"Clembot"*.
- 🗣 **Speech Normalizer**: Strips filler words and corrects homophones before routing — *"post grey sql"* → `postgresql`, *"vs code"* → `vscode`, *"pi charm"* → `pycharm`.
- 📁 **Native Windows File System**: Dynamic path resolution for Desktop, Downloads, Documents, OneDrive, and drive roots (`C:\`). Active File Explorer tab detection via Windows COM.
- 🗑 **Recycle Bin Protection**: File deletions default to the Windows **Recycle Bin** via `Send2Trash` (fully recoverable), strictly prohibiting silent destructive operations.
- ⚡ **Zero-Latency Offline Mode**: Built-in deterministic fast router and local heuristic NLP planner execute 100+ common commands instantly without requiring external cloud APIs.
- 🧠 **Structured AI Planner**: Gemini and Ollama providers produce Pydantic-validated structured action plans with a 1-retry self-correction loop — no unrecognised free-form actions reach the executor.
- 💬 **Conversational / Hinglish Mode**: Detects Hindi/Hinglish phrasing and routes it directly to the AI reasoning layer, bypassing the deterministic router.
- 🌐 **Automatic Web Fallback**: When Clembot cannot fulfil a request locally, it automatically opens a Google search in the default browser instead of silently failing.
- 📦 **Comprehensive App Resolver**: Persistent disk cache of all Start Menu / UWP / installed apps with background indexing and RapidFuzz fuzzy matching.
- 🔧 **System Self-Check (`--doctor`)**: Run `python -m app.doctor` (or `run_clembot.bat --doctor`) to verify Python version, 12 critical packages, microphone, TTS engine, IPC port, AI provider, and app index.
- 💻 **First-Class VS Code Integration**: Dedicated bidirectional TypeScript extension communicating over local IPC (`http://127.0.0.1:25362`) for precise document inspection, cursor navigation, and surgical edits.
- 🔍 **Interactive Code Diff Previews**: Displays interactive Before/After unified diffs in the GUI and asks for spoken confirmation before applying code changes, with automatic `.bak` backups.
- 🪟 **Native Windows Window Snapping**: Snap windows to Left Half, Right Half, Center, Minimize, Maximize, or Show Desktop using native Win32 User32 APIs.
- 🌐 **Multi-Browser & Web Control**: Launch Chrome, Edge, and Firefox, manage tabs, and execute searches across Google, YouTube, GitHub, Bing, and DuckDuckGo.
- 🎨 **Modern Windows Fluent GUI**: Dark/light themed GUI featuring dynamic audio waveform visualization, live transcripts, activity logs, and system tray integration.
- 🛡 **Thread-Safe Event Bus**: Duplicate-subscription guard and concurrent emit support ensure each listener fires exactly once regardless of race conditions.

---

## Architecture

```
                          ┌────────────────────────┐
                          │   Microphone Audio     │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │ Speech Recognition     │ (Continuous / Push-to-Talk)
                          │ Wake: "Clembot activate"│
                          └───────────┬────────────┘
                                      │ Spoken text
                                      ▼
                          ┌────────────────────────┐
                          │  Context Manager       │ (Active window, process,
                          │  & Conversational Mem  │  Explorer folder, VS Code file)
                          └───────────┬────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
    ┌──────────────────────┐                      ┌──────────────────────┐
    │  FastCommandRouter   │                      │ AI Intent Planner    │
    │  (Instant Offline)   │                      │ (Local Heuristic,    │
    │  - App launch        │                      │  Ollama, Gemini,     │
    │  - Folder open/list  │                      │  OpenAI)             │
    │  - Windows snap      │                      └──────────┬───────────┘
    │  - Browser tabs      │                                 │
    └──────────┬───────────┘                                 │
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      ▼
                          ┌────────────────────────┐
                          │ Safety & Policy Layer  │ (Confirms destructive actions,
                          │ Confirmation Queue     │  diff preview on code edits)
                          └───────────┬────────────┘
                                      │ Approved actions
                                      ▼
                          ┌────────────────────────┐
                          │     Action Router      │
                          └───────────┬────────────┘
           ┌──────────────┬───────────┼──────────────┬──────────────┐
           ▼              ▼           ▼              ▼              ▼
     ┌───────────┐  ┌───────────┐┌───────────┐ ┌───────────┐ ┌───────────────┐
     │FileSystem │  │  Windows  ││  Browser  │ │  Editor   │ │  Automation   │
     │Service    │  │AppCatalog ││Controller │ │Adapter    │ │(Mouse/Keyboard│
     │(Send2Trash│  │& Win32gui ││(Edge/     │ │(VS Code   │ │ fallback)     │
     │ KnownDirs)│  │(Snap/Min) ││Chrome/FF) │ │ IPC/File) │ └───────────────┘
     └───────────┘  └───────────┘└───────────┘ └─────┬─────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │ VS Code Ext IPC │
                                            │(Localhost:25362)│
                                            └─────────────────┘
```

---

## Supported Voice Commands

### 1. Activation & Sleep
- *"Clembot activate yourself"* — Wakes the assistant and enters listening mode.
- *"Clembot deactivate"* — Puts the assistant to sleep (ignores general chatter).
- *"Hey Clembot, open my Downloads folder"* — Direct activation with immediate command execution.

### 2. Files & Directories
- *"Open Downloads"* / *"Open my Documents folder"* / *"Open Desktop"*
- *"What files are in Downloads?"* / *"Show me the files in this folder"*
- *"Create a folder called Projects on Desktop"* / *"Create a folder called AI Projects"*
- *"Create a file called notes.txt"* / *"Create a new Python file"*
- *"Rename this file to resume.pdf"* / *"Rename notes.txt to college_notes.txt"*
- *"Copy this file"* / *"Copy this folder to Desktop"*
- *"Paste it into Documents"*
- *"Move the resume from Downloads to Documents"* / *"Move this file to Downloads"*
- *"Delete this folder"* / *"Delete college_notes.txt"* (Moves to Windows Recycle Bin with confirmation)
- *"Find my resume"* / *"Find all Python files in my project"*

### 3. Application Control
- *"Open Chrome"* / *"Open Edge"* / *"Open Firefox"*
- *"Open VS Code"* / *"Open Notepad"* / *"Open Calculator"*
- *"Open File Explorer"* / *"Open Command Prompt"* / *"Open PowerShell"*
- *"Switch to VS Code"* / *"Close Chrome"* / *"Close Notepad"*

### 4. Window & System Control
- *"Minimize the current window"* / *"Maximize this window"* / *"Restore window"*
- *"Snap window left"* / *"Snap window right"* / *"Center window"*
- *"Show desktop"* / *"Close current application"*
- *"Take a screenshot"* (Saved directly to `Pictures/Screenshots`)
- *"Volume up"* / *"Volume down"* / *"Mute"* / *"Unmute"*

### 5. Web Browsing & Search
- *"Search Google for Python Django tutorials"*
- *"Search YouTube for Python DSA"*
- *"Open GitHub"* / *"Open https://github.com"*
- *"New tab"* / *"Close tab"* / *"Next tab"* / *"Previous tab"* / *"Reload"*

### 6. Coding & VS Code Control
- *"Open app.py"* / *"Open my Django project in VS Code"*
- *"Go to line 25"* / *"Jump to line 50"*
- *"Change the function name calculate_total to calculate_price"*
- *"At line 30, add a try except block around the database call"*
- *"Run this Python program"* / *"Run this Python file"*
- *"Undo code change"*

---

## Safety & Destructive Action Protections

Clembot enforces strict safety policies to prevent accidental data loss:
1. **Recycle Bin Default**: All file and directory deletions use Windows `Send2Trash` rather than permanent removal. Items can be restored from the Windows Recycle Bin at any time.
2. **Deletion Confirmation**: Folders containing multiple items trigger an explicit confirmation dialog and spoken prompt:
   *"Downloads contains 126 files. Do you really want me to delete this folder?"*
3. **Protected System Paths**: Deletions targeting `C:\Windows`, `C:\Windows\System32`, `C:\Program Files`, or the root of `C:\` are strictly blocked.
4. **Dangerous Command Shield**: Commands attempting disk formatting (`format c:`) or recursive root deletions (`rmdir /s /q c:\`) are automatically intercepted.
5. **Code Modification Diff Review**: Major code changes display a side-by-side diff in the GUI for user review before application, with automatic `.bak` backup creation.

---

## Quick Start

### 1. Installation
Ensure Python 3.10+ is installed on Windows, then run:

```powershell
# Clone or navigate to the directory
cd F:\intr\voiceps

# Install dependencies
pip install -r requirements.txt
```

### 2. Launching Clembot
Double-click `run_clembot.bat` or run via terminal:

```powershell
python -m app.main
```

To run in lightweight command-line mode without the GUI:
```powershell
python -m app.main --cli
```

### 3. Running Automated Tests
```powershell
python -m unittest discover -s tests -v
```

---

## Project Structure

```
clembot/
├── app/
│   ├── main.py                    # Application entry point (GUI/CLI/Tray)
│   ├── config/
│   │   └── settings.py            # Pydantic configuration & .env loader
│   ├── core/
│   │   ├── models.py              # Data models (AgentPlan, AgentAction, ScreenContext)
│   │   ├── event_bus.py           # Thread-safe pub/sub event dispatcher
│   │   └── orchestrator.py        # Master assistant state machine
│   ├── ai/
│   │   ├── base.py                # AIProvider abstract base
│   │   ├── local_heuristic.py     # 100% offline rule-based NLP planner
│   │   ├── ollama_provider.py     # Local Ollama integration (Qwen/Llama)
│   │   ├── gemini_provider.py     # Google Gemini API provider
│   │   ├── openai_provider.py     # OpenAI API provider
│   │   └── factory.py             # Provider factory with fallback
│   ├── speech/
│   │   ├── base.py                # SpeechRecognizer base
│   │   ├── engine.py              # Continuous listening & Push-to-Talk
│   │   └── wake_word.py           # "Clembot activate / deactivate" detector
│   ├── tts/
│   │   ├── base.py                # BaseTTSProvider
│   │   ├── sapi_engine.py         # Offline Windows SAPI 5 via pyttsx3
│   │   └── voice_service.py       # Asynchronous non-blocking speech queue
│   ├── commands/
│   │   ├── fast_router.py         # Instant offline deterministic router
│   │   └── router.py              # Subsystem command dispatcher
│   ├── filesystem/
│   │   ├── paths.py               # Windows Known Folders & Explorer COM resolver
│   │   ├── service.py             # Safe file ops & Send2Trash Recycle Bin
│   │   └── search.py              # Bounded user file search
│   ├── windows/
│   │   ├── apps.py                # Start Menu & Registry App Catalog
│   │   ├── window_manager.py      # Win32 window snapping & state control
│   │   └── system.py              # Volume & screenshot controls
│   ├── browser/
│   │   └── controller.py          # Chrome, Edge, Firefox & search engine controller
│   ├── editor/
│   │   ├── base.py                # EditorAdapter base
│   │   ├── vscode_adapter.py      # VS Code IPC client with file fallback
│   │   ├── generic_adapter.py     # Generic text editor adapter
│   │   └── code_intelligence.py   # AST inspection & unified diff engine
│   ├── ipc/
│   │   └── server.py              # FastAPI local server on 127.0.0.1:25362
│   ├── automation/
│   │   └── input_adapter.py       # Controlled keyboard & mouse automation
│   ├── clipboard/
│   │   └── manager.py             # Windows clipboard integration
│   ├── context/
│   │   └── context_manager.py     # Real-time desktop state inspector
│   ├── memory/
│   │   └── conversation.py        # Conversational memory & reference resolver
│   ├── security/
│   │   └── guard.py               # Path validation & dangerous command blocker
│   ├── logging/
│   │   └── logger.py              # Structured logging with credential scrubbing
│   └── ui/
│       ├── main_window.py         # Modern Windows GUI with waveform & diff preview
│       ├── settings_dialog.py     # Settings dialog (Audio, AI, Safety)
│       ├── tray.py                # Windows System Tray manager
│       └── theme.py               # Fluent dark/light design system
├── vscode-extension/              # Dedicated TypeScript VS Code extension
│   ├── src/extension.ts
│   ├── package.json
│   └── tsconfig.json
├── tests/                         # Automated unit test suite (80 passing tests)
├── scripts/
│   └── build_exe.py               # PyInstaller executable builder
├── run_clembot.bat                # Windows launcher batch script
├── requirements.txt               # Verified dependency list
├── .env.example                   # Configuration template
├── INSTALLATION.md                # Installation guide
└── TESTING.md                     # Testing instructions
```

---

## License

MIT License. Designed and engineered for Windows 10 & Windows 11.
