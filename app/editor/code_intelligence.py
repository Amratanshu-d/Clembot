import ast
import difflib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from app.logging.logger import logger


@dataclass
class CodeEditProposal:
    file_path: Path
    start_line: int
    end_line: int
    original_code: str
    proposed_code: str
    diff: str
    explanation: str
    is_major: bool = False


class CodeIntelligenceEngine:
    """
    Intelligent code reasoning, AST inspection, diff generation, and safe code editing.
    Ensures targeted, non-destructive modifications with backup and user confirmation.
    """

    @staticmethod
    def generate_unified_diff(original_text: str, modified_text: str, filename: str = "file") -> str:
        """Generates a standard unified diff between original and modified code."""
        orig_lines = original_text.splitlines(keepends=True)
        mod_lines = modified_text.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "".join(diff)

    @staticmethod
    def find_python_function_range(source_code: str, function_name: str) -> Optional[Tuple[int, int, str]]:
        """
        Locates the line range (start_line, end_line) of a function in Python code using AST.
        Returns (start_line, end_line, function_source) (1-indexed).
        """
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.lower() == function_name.lower():
                        start_line = node.lineno
                        end_line = getattr(node, 'end_lineno', start_line + 10)
                        lines = source_code.splitlines(keepends=True)
                        func_code = "".join(lines[start_line - 1:end_line])
                        return start_line, end_line, func_code
        except Exception as e:
            logger.debug(f"AST parse failed, fallback to regex search: {e}")

        # Regex fallback
        pattern = rf'^(?:async\s+)?def\s+{re.escape(function_name)}\s*\('
        lines = source_code.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                start_line = i + 1
                # Find end of indented block
                base_indent = len(line) - len(line.lstrip())
                end_line = start_line
                for j in range(i + 1, len(lines)):
                    sub_line = lines[j]
                    if not sub_line.strip():
                        continue
                    indent = len(sub_line) - len(sub_line.lstrip())
                    if indent <= base_indent:
                        break
                    end_line = j + 1
                func_code = "".join(lines[start_line - 1:end_line])
                return start_line, end_line, func_code

        return None

    @classmethod
    def propose_function_rename(
        cls,
        file_path: Path,
        old_name: str,
        new_name: str
    ) -> Optional[CodeEditProposal]:
        """
        Proposes renaming a function definition and its calls within the file.
        """
        if not file_path.is_file():
            return None

        original = file_path.read_text(encoding="utf-8")
        # Replace occurrences as identifier
        pattern = rf'\b{re.escape(old_name)}\b'
        modified, count = re.subn(pattern, new_name, original)

        if count == 0:
            return None

        diff = cls.generate_unified_diff(original, modified, file_path.name)
        return CodeEditProposal(
            file_path=file_path,
            start_line=1,
            end_line=len(original.splitlines()),
            original_code=original,
            proposed_code=modified,
            diff=diff,
            explanation=f"Rename function '{old_name}' to '{new_name}' ({count} occurrence{'s' if count != 1 else ''}).",
            is_major=count > 3
        )

    @classmethod
    def propose_exception_handling_at_line(
        cls,
        file_path: Path,
        target_line: int,
        line_count: int = 1
    ) -> Optional[CodeEditProposal]:
        """
        Wraps code lines around target_line in a try...except Exception block.
        """
        if not file_path.is_file():
            return None

        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        if target_line < 1 or target_line > len(lines):
            return None

        idx_start = target_line - 1
        idx_end = min(len(lines), idx_start + line_count)

        target_chunk = "".join(lines[idx_start:idx_end])
        # Detect indentation
        first_line = lines[idx_start]
        indent = " " * (len(first_line) - len(first_line.lstrip()))
        extra_indent = "    "

        indented_lines = []
        for line in lines[idx_start:idx_end]:
            if line.strip():
                indented_lines.append(f"{extra_indent}{line}")
            else:
                indented_lines.append(line)

        wrapped = (
            f"{indent}try:\n"
            f"{''.join(indented_lines)}"
            f"{indent}except Exception as e:\n"
            f"{indent}    logger.error(f'Error at line {target_line}: {{e}}')\n"
        )

        mod_lines = list(lines)
        mod_lines[idx_start:idx_end] = [wrapped]
        modified_full = "".join(mod_lines)

        diff = cls.generate_unified_diff("".join(lines), modified_full, file_path.name)
        return CodeEditProposal(
            file_path=file_path,
            start_line=target_line,
            end_line=idx_end,
            original_code=target_chunk,
            proposed_code=wrapped,
            diff=diff,
            explanation=f"Wrap lines {target_line}–{idx_end} in a try-except error handling block.",
            is_major=False
        )

    @classmethod
    def apply_proposal(cls, proposal: CodeEditProposal) -> bool:
        """
        Safely applies a proposal by creating a backup (.bak) first and writing updated code.
        """
        try:
            target = proposal.file_path
            bak_path = target.with_suffix(target.suffix + ".bak")
            shutil.copy2(target, bak_path)

            target.write_text(proposal.proposed_code, encoding="utf-8")
            logger.info(f"Successfully applied code edit to {target}. Backup at {bak_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to apply code proposal: {e}")
            return False
