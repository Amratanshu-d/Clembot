from app.editor.base import EditorAdapter
from app.editor.vscode_adapter import VSCodeAdapter
from app.editor.generic_adapter import GenericWindowsEditorAdapter
from app.editor.code_intelligence import CodeIntelligenceEngine, CodeEditProposal

__all__ = [
    "EditorAdapter",
    "VSCodeAdapter",
    "GenericWindowsEditorAdapter",
    "CodeIntelligenceEngine",
    "CodeEditProposal",
]
