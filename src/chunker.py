"""
Smart code chunking with AST-aware splitting.
Falls back to regex-based chunking for unsupported languages.
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from src.config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'method', 'block', 'raw'
    context: Optional[str] = None  # e.g., class name for methods, imports


class Chunker:
    """Smart code chunker with language-specific support."""

    def __init__(self):
        self.tree_sitter_available = False
        try:
            import tree_sitter
            import tree_sitter_python
            import tree_sitter_javascript

            self.tree_sitter_available = True
        except ImportError:
            pass

    def chunk_file(self, file_path: Path) -> List[CodeChunk]:
        """
        Chunk a file into semantically meaningful pieces.

        Args:
            file_path: Path to the file to chunk

        Returns:
            List of code chunks
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return []

        if not content.strip():
            return []

        # Get file extension
        ext = file_path.suffix.lower()

        # Try language-specific chunking first
        if ext == ".py":
            chunks = self._chunk_python(content, str(file_path))
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
            chunks = self._chunk_javascript(content, str(file_path))
        elif ext == ".rb":
            chunks = self._chunk_ruby(content, str(file_path))
        elif ext in (".go", ".rs", ".java", ".kt"):
            chunks = self._chunk_c_style(content, str(file_path))
        else:
            # Fallback to simple chunking
            chunks = self._chunk_simple(content, str(file_path))

        # Filter out chunks that are too small
        chunks = [c for c in chunks if len(c.content.strip()) >= MIN_CHUNK_SIZE]

        return chunks

    def _chunk_python(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Python code by functions, classes, and methods."""
        chunks = []
        lines = content.split("\n")

        # Extract imports for context
        imports = []
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                imports.append(line.strip())
            elif line.strip() and not line.strip().startswith("#"):
                break  # Stop at first non-import, non-comment line

        import_context = "\n".join(imports) if imports else None

        # Regex patterns for Python constructs
        class_pattern = re.compile(r"^class\s+(\w+)", re.MULTILINE)
        function_pattern = re.compile(r"^def\s+(\w+)", re.MULTILINE)
        method_pattern = re.compile(r"^\s+def\s+(\w+)", re.MULTILINE)

        # Find all class definitions
        for match in class_pattern.finditer(content):
            start_pos = match.start()
            start_line = content[:start_pos].count("\n") + 1
            class_name = match.group(1)

            # Find the end of the class (next class or end of file)
            next_class = class_pattern.search(content, match.end())
            end_pos = next_class.start() if next_class else len(content)
            end_line = content[:end_pos].count("\n") + 1

            class_content = content[start_pos:end_pos].rstrip()

            # If class is too large, chunk its methods separately
            if len(class_content) > CHUNK_SIZE * 2:
                # Extract methods from the class
                method_chunks = self._extract_python_methods(
                    class_content, file_path, start_line, class_name, import_context
                )
                chunks.extend(method_chunks)
            else:
                chunks.append(
                    CodeChunk(
                        content=class_content,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        chunk_type="class",
                        context=import_context,
                    )
                )

        # Find standalone functions (not methods)
        for match in function_pattern.finditer(content):
            # Skip if it's a method (indented)
            line_start = content.rfind("\n", 0, match.start()) + 1
            if content[line_start : match.start()].strip():
                continue

            start_pos = match.start()
            start_line = content[:start_pos].count("\n") + 1
            func_name = match.group(1)

            # Find the end of the function
            end_pos = self._find_python_function_end(content, start_pos)
            end_line = content[:end_pos].count("\n") + 1

            func_content = content[start_pos:end_pos].rstrip()

            if len(func_content) <= CHUNK_SIZE * 2:
                chunks.append(
                    CodeChunk(
                        content=func_content,
                        file_path=file_path,
                        start_line=start_line,
                        end_line=end_line,
                        chunk_type="function",
                        context=import_context,
                    )
                )

        # If no chunks were created, fall back to simple chunking
        if not chunks:
            return self._chunk_simple(content, file_path)

        return chunks

    def _extract_python_methods(
        self,
        class_content: str,
        file_path: str,
        class_start_line: int,
        class_name: str,
        import_context: Optional[str],
    ) -> List[CodeChunk]:
        """Extract methods from a Python class."""
        chunks = []
        method_pattern = re.compile(r"^\s+def\s+(\w+)", re.MULTILINE)

        for match in method_pattern.finditer(class_content):
            start_pos = match.start()
            start_line = class_start_line + class_content[:start_pos].count("\n")
            method_name = match.group(1)

            # Find the end of the method
            end_pos = self._find_python_function_end(class_content, start_pos)
            end_line = class_start_line + class_content[:end_pos].count("\n")

            method_content = class_content[start_pos:end_pos].rstrip()

            # Add class context
            context_lines = [f"# Class: {class_name}"]
            if import_context:
                context_lines.append(import_context)

            full_context = "\n".join(context_lines)

            chunks.append(
                CodeChunk(
                    content=method_content,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type="method",
                    context=full_context,
                )
            )

        return chunks

    def _find_python_function_end(self, content: str, start_pos: int) -> int:
        """Find the end position of a Python function/method."""
        lines = content[start_pos:].split("\n")
        if not lines:
            return start_pos

        # Get the indentation of the def line
        def_line = lines[0]
        def_indent = len(def_line) - len(def_line.lstrip())

        # Find where indentation returns to def level or less
        pos = start_pos + len(lines[0]) + 1  # Skip first line

        for i, line in enumerate(lines[1:], 1):
            if line.strip():  # Non-empty line
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= def_indent:
                    # Found the end
                    return start_pos + sum(len(l) + 1 for l in lines[:i])

            pos += len(line) + 1

        return len(content)  # End of content

    def _chunk_javascript(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code."""
        chunks = []
        lines = content.split("\n")

        # Extract imports
        imports = []
        for line in lines:
            if line.strip().startswith(("import ", "export ")):
                imports.append(line.strip())

        import_context = "\n".join(imports[:10]) if imports else None

        # Patterns for JS/TS constructs
        function_patterns = [
            re.compile(r"^(export\s+)?(async\s+)?function\s+(\w+)", re.MULTILINE),
            re.compile(r"^(export\s+)?const\s+(\w+)\s*=\s*(async\s*)?\(", re.MULTILINE),
            re.compile(r"^(export\s+)?const\s+(\w+)\s*=\s*(async\s+)?function", re.MULTILINE),
        ]

        class_pattern = re.compile(r"^(export\s+)?class\s+(\w+)", re.MULTILINE)

        # Find classes
        for match in class_pattern.finditer(content):
            start_pos = match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Find matching closing brace
            end_pos = self._find_matching_brace(content, start_pos)
            end_line = content[:end_pos].count("\n") + 1

            class_content = content[start_pos:end_pos]

            chunks.append(
                CodeChunk(
                    content=class_content,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type="class",
                    context=import_context,
                )
            )

        # Find functions
        for pattern in function_patterns:
            for match in pattern.finditer(content):
                start_pos = match.start()
                start_line = content[:start_pos].count("\n") + 1

                # Find matching closing brace or arrow function end
                end_pos = self._find_matching_brace(content, start_pos)
                end_line = content[:end_pos].count("\n") + 1

                func_content = content[start_pos:end_pos]

                if len(func_content) <= CHUNK_SIZE * 2:
                    chunks.append(
                        CodeChunk(
                            content=func_content,
                            file_path=file_path,
                            start_line=start_line,
                            end_line=end_line,
                            chunk_type="function",
                            context=import_context,
                        )
                    )

        if not chunks:
            return self._chunk_simple(content, file_path)

        return chunks

    def _chunk_ruby(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk Ruby code."""
        # Similar to Python but with different keywords
        chunks = []

        class_pattern = re.compile(r"^class\s+(\w+)", re.MULTILINE)
        method_pattern = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)

        # Find classes
        for match in class_pattern.finditer(content):
            start_pos = match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Find matching 'end'
            end_pos = self._find_ruby_block_end(content, start_pos)
            end_line = content[:end_pos].count("\n") + 1

            class_content = content[start_pos:end_pos]

            chunks.append(
                CodeChunk(
                    content=class_content,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type="class",
                    context=None,
                )
            )

        if not chunks:
            return self._chunk_simple(content, file_path)

        return chunks

    def _chunk_c_style(self, content: str, file_path: str) -> List[CodeChunk]:
        """Chunk C-style languages (Go, Rust, Java, Kotlin)."""
        return self._chunk_simple(content, file_path)

    def _chunk_simple(self, content: str, file_path: str) -> List[CodeChunk]:
        """Simple line-based chunking with overlap."""
        chunks = []
        lines = content.split("\n")

        # Calculate lines per chunk
        avg_line_length = len(content) / max(len(lines), 1)
        lines_per_chunk = max(int(CHUNK_SIZE / avg_line_length), 10)
        overlap_lines = max(int(CHUNK_OVERLAP / avg_line_length), 2)

        i = 0
        while i < len(lines):
            end = min(i + lines_per_chunk, len(lines))
            chunk_lines = lines[i:end]
            chunk_content = "\n".join(chunk_lines)

            if chunk_content.strip():
                chunks.append(
                    CodeChunk(
                        content=chunk_content,
                        file_path=file_path,
                        start_line=i + 1,
                        end_line=end,
                        chunk_type="block",
                        context=None,
                    )
                )

            i += lines_per_chunk - overlap_lines

        return chunks

    def _find_matching_brace(self, content: str, start_pos: int) -> int:
        """Find the position of the matching closing brace."""
        # Find the opening brace
        open_pos = content.find("{", start_pos)
        if open_pos == -1:
            # No brace found, return a reasonable end
            return min(start_pos + CHUNK_SIZE, len(content))

        count = 1
        pos = open_pos + 1

        while pos < len(content) and count > 0:
            if content[pos] == "{":
                count += 1
            elif content[pos] == "}":
                count -= 1
            pos += 1

        return pos if count == 0 else len(content)

    def _find_ruby_block_end(self, content: str, start_pos: int) -> int:
        """Find the end of a Ruby block (matching 'end')."""
        lines = content[start_pos:].split("\n")
        depth = 1
        pos = start_pos + len(lines[0]) + 1

        for line in lines[1:]:
            stripped = line.strip()

            # Count block starts
            if re.match(r"^(class|module|def|if|unless|case|while|until|for|begin)\b", stripped):
                depth += 1

            # Count block ends
            if stripped == "end" or stripped.startswith("end "):
                depth -= 1
                if depth == 0:
                    return pos + len(line)

            pos += len(line) + 1

        return len(content)


# Module-level convenience function
def chunk_file(file_path: Path) -> List[CodeChunk]:
    """
    Convenience function to chunk a file.

    Args:
        file_path: Path to the file to chunk

    Returns:
        List of code chunks
    """
    chunker = Chunker()
    return chunker.chunk_file(file_path)
