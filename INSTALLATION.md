# Clembot Installation & Setup Guide

This guide provides step-by-step instructions for installing and running **Clembot** on **Windows 10 and Windows 11**.

---

## 1. System Requirements

- **Operating System**: Windows 10 (64-bit) or Windows 11
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14
- **Microphone & Speakers**: Built-in or external USB/Bluetooth headset
- **Optional**: VS Code (for code editing integration), Ollama (for offline local LLM)

---

## 2. Step-by-Step Installation

### Step 1: Open PowerShell or Command Prompt
Open PowerShell (or CMD) and navigate to the project directory:

```powershell
cd F:\intr\voiceps
```

### Step 2: Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate in PowerShell
.\.venv\Scripts\Activate.ps1

# (Or if using CMD)
# .\.venv\Scripts\activate.bat
```

> **Note for PowerShell execution policy**: If script execution is restricted on your system, run:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### Step 3: Install Required Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables (Optional)
Clembot is designed to operate **100% offline out-of-the-box** using its local deterministic fast router and heuristic NLP planner.

If you wish to use Google Gemini, OpenAI, or local Ollama for advanced conversational reasoning:
1. Copy the sample environment file:
   ```powershell
   copy .env.example .env
   ```
2. Edit `.env` in Notepad:
   ```powershell
   notepad .env
   ```
3. Set your preferred provider and API key:
   ```ini
   CLEMBOT_AI_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSyYourKeyHere
   ```

---

## 3. Install the VS Code Extension (Recommended)

To enable first-class bidirectional code editing inside VS Code:

1. Open the `vscode-extension/` folder inside VS Code:
   ```powershell
   code vscode-extension
   ```
2. Press `F5` to start the extension in Development Host mode.
3. Or compile and install as a permanent `.vsix` package:
   ```powershell
   cd vscode-extension
   npm install
   npm run compile
   npx vsce package
   code --install-extension clembot-vscode-1.0.0.vsix
   cd ..
   ```

---

## 4. Running Clembot

### Method A: Using the Windows Launcher Batch Script
Double-click `run_clembot.bat` or run in terminal:
```powershell
.\run_clembot.bat
```

### Method B: Directly with Python
```powershell
# Launch with Modern GUI and System Tray
python -m app.main

# Or run in interactive terminal / CLI mode (without GUI)
python -m app.main --cli

# Or run with Push-to-Talk only
python -m app.main --push-to-talk
```

---

## 5. Building the Standalone Executable (Clembot.exe)

You can package Clembot into a standalone Windows executable that runs without requiring a separate Python installation:

```powershell
# Ensure pyinstaller is installed
pip install pyinstaller

# Run build automation script
python scripts\build_exe.py
```

The compiled binary will be located at:
`dist\Clembot.exe`

---

## 6. Optional: Start Clembot Automatically with Windows

To have Clembot start whenever you log into Windows:
1. Press `Win + R`, type `shell:startup`, and press Enter.
2. Create a shortcut to `run_clembot.bat` (or `dist\Clembot.exe`) inside that folder.

---

## 7. Pre-Flight Health Check (Recommended)

Before the first launch, run the built-in **System Doctor** to verify your environment:

```powershell
python -m app.doctor
```

Or use the launcher flag:
```powershell
.\run_clembot.bat --doctor
```

The doctor checks:
| Check | What it validates |
|---|---|
| Python version | ≥ 3.10 required |
| Critical packages | 12 packages including `rapidfuzz`, `jellyfish`, `psutil`, `pycaw`, `sounddevice` |
| Microphone | At least one audio input device found |
| TTS engine | Windows SAPI5 engine (`pyttsx3`) initialises correctly |
| IPC port 25362 | Not blocked by another process |
| AI provider | Gemini/Ollama reachable, or local heuristic mode confirmed |
| App index | Start Menu cache at `%LOCALAPPDATA%\Clembot\app_index.json` |

All checks passing looks like:
```
[PASS] Python 3.14.3 (>= 3.10)
[PASS] rapidfuzz installed
[PASS] jellyfish installed
...
[PASS] AI Provider: GeminiProvider
[PASS] App index: 312 apps indexed
```

---

## 8. Configuring the AI Provider

Clembot works fully **offline out-of-the-box** (local heuristic planner + deterministic fast router). For open-ended questions, Hinglish support, and smarter intent resolution, configure one of the following providers in `.env`:

### Google Gemini (Cloud)
```ini
CLEMBOT_AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyYourActualKeyHere
```

### Ollama (100% Local, Privacy-First)
```ini
CLEMBOT_AI_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```
Install Ollama from [ollama.ai](https://ollama.ai) and pull the model:
```powershell
ollama pull qwen2.5:7b
```
