"""
Tree-sitter based AST-aware code chunking.
Provides precise code understanding using language parsers.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.chunker import CodeChunk
from src.config import CHUNK_SIZE, MIN_CHUNK_SIZE


@dataclass
class TreeSitterLanguage:
    """Wrapper for tree-sitter language configuration."""

    name: str
    parser: any
    function_query: str
    class_query: str
    method_query: str
    import_query: Optional[str] = None


class TreeSitterChunker:
    """AST-based code chunker using tree-sitter."""

    def __init__(self):
        """Initialize tree-sitter parsers for supported languages."""
        self.languages = {}
        self._init_languages()

    def _init_languages(self):
        """Initialize tree-sitter language parsers."""
        try:
            import tree_sitter_python as tspython
            from tree_sitter import Language, Parser

            # Python
            PY_LANGUAGE = Language(tspython.language())
            py_parser = Parser(PY_LANGUAGE)

            self.languages["python"] = TreeSitterLanguage(
                name="python",
                parser=py_parser,
                function_query="""
                    (function_definition
                        name: (identifier) @function.name
                    ) @function.def
                """,
                class_query="""
                    (class_definition
                        name: (identifier) @class.name
                    ) @class.def
                """,
                method_query="""
                    (class_definition
                        body: (block
                            (function_definition
                                name: (identifier) @method.name
                            ) @method.def
                        )
                    )
                """,
                import_query="""
                    [
                        (import_statement) @import
                        (import_from_statement) @import
                    ]
                """,
            )

        except ImportError:
            pass

        try:
            import tree_sitter_javascript as tsjavascript
            from tree_sitter import Language, Parser

            # JavaScript/TypeScript
            JS_LANGUAGE = Language(tsjavascript.language())
            js_parser = Parser(JS_LANGUAGE)

            self.languages["javascript"] = TreeSitterLanguage(
                name="javascript",
                parser=js_parser,
                function_query="""
                    [
                        (function_declaration
                            name: (identifier) @function.name
                        ) @function.def
                        (arrow_function) @function.def
                        (function_expression) @function.def
                    ]
                """,
                class_query="""
                    (class_declaration
                        name: (identifier) @class.name
                    ) @class.def
                """,
                method_query="""
                    (class_declaration
                        body: (class_body
                            (method_definition
                                name: (property_identifier) @method.name
                            ) @method.def
                        )
                    )
                """,
                import_query="""
                    [
                        (import_statement) @import
                        (export_statement) @import
                    ]
                """,
            )

            # TypeScript uses same parser
            self.languages["typescript"] = self.languages["javascript"]

        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if tree-sitter is available."""
        return len(self.languages) > 0

    def can_chunk_file(self, file_path: Path) -> bool:
        """Check if we can use tree-sitter for this file."""
        ext = file_path.suffix.lower()
        language = self._get_language_for_extension(ext)
        return language is not None

    def chunk_file(self, file_path: Path) -> List[CodeChunk]:
        """
        Chunk a file using tree-sitter AST parsing.

        Args:
            file_path: Path to the file to chunk

        Returns:
            List of code chunks
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        if not content.strip():
            return []

        ext = file_path.suffix.lower()
        language = self._get_language_for_extension(ext)

        if not language:
            return []

        # Parse the file
        tree = language.parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node

        chunks = []
        lines = content.split("\n")

        # Extract imports for context
        import_context = self._extract_imports(root_node, content, language)

        # Extract classes
        classes = self._extract_nodes_by_type(root_node, ["class_definition", "class_declaration"])

        for class_node in classes:
            class_chunks = self._chunk_class(
                class_node, content, lines, str(file_path), import_context
            )
            chunks.extend(class_chunks)

        # Extract top-level functions (not methods)
        functions = self._extract_top_level_functions(root_node)

        for func_node in functions:
            func_chunk = self._chunk_function(
                func_node, content, lines, str(file_path), import_context, None
            )
            if func_chunk:
                chunks.append(func_chunk)

        # Filter small chunks
        chunks = [c for c in chunks if len(c.content.strip()) >= MIN_CHUNK_SIZE]

        return chunks

    def _get_language_for_extension(self, ext: str) -> Optional[TreeSitterLanguage]:
        """Get tree-sitter language for file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mjs": "javascript",
            ".cjs": "javascript",
        }
        lang_name = ext_map.get(ext)
        return self.languages.get(lang_name) if lang_name else None

    def _extract_imports(
        self, root_node, content: str, language: TreeSitterLanguage
    ) -> Optional[str]:
        """Extract import statements for context."""
        imports = []

        # Get import nodes based on language
        if language.name == "python":
            import_types = ["import_statement", "import_from_statement"]
        else:  # JavaScript/TypeScript
            import_types = ["import_statement"]

        for node in self._extract_nodes_by_type(root_node, import_types):
            import_text = content[node.start_byte : node.end_byte]
            imports.append(import_text)

            # Limit to first 10 imports to keep context manageable
            if len(imports) >= 10:
                break

        return "\n".join(imports) if imports else None

    def _extract_nodes_by_type(self, root_node, type_names: List[str]):
        """Extract all nodes of specific types from the tree."""
        nodes = []

        def traverse(node):
            if node.type in type_names:
                nodes.append(node)
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return nodes

    def _extract_top_level_functions(self, root_node):
        """Extract only top-level functions (not methods inside classes)."""
        functions = []

        function_types = ["function_definition", "function_declaration"]

        for child in root_node.children:
            if child.type in function_types:
                functions.append(child)
            # For module-level, check one level deep for exports
            elif child.type in ["export_statement", "decorated_definition"]:
                for subchild in child.children:
                    if subchild.type in function_types:
                        functions.append(subchild)

        return functions

    def _chunk_class(
        self,
        class_node,
        content: str,
        lines: List[str],
        file_path: str,
        import_context: Optional[str],
    ) -> List[CodeChunk]:
        """Chunk a class - either whole or by methods."""
        chunks = []

        start_line = class_node.start_point[0] + 1
        end_line = class_node.end_point[0] + 1
        class_content = content[class_node.start_byte : class_node.end_byte]

        # Get class name
        class_name = self._get_node_name(class_node, content)

        # If class is small enough, return as single chunk
        if len(class_content) <= CHUNK_SIZE * 2:
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
        else:
            # Class is large, chunk by methods
            methods = self._extract_methods(class_node)

            for method_node in methods:
                context_parts = [f"# Class: {class_name}"]
                if import_context:
                    context_parts.append(import_context)
                method_context = "\n".join(context_parts)

                method_chunk = self._chunk_function(
                    method_node, content, lines, file_path, method_context, class_name
                )
                if method_chunk:
                    chunks.append(method_chunk)

        return chunks

    def _extract_methods(self, class_node):
        """Extract method nodes from a class."""
        methods = []

        method_types = ["function_definition", "method_definition"]

        # Find the class body
        for child in class_node.children:
            if child.type in ["block", "class_body"]:
                for method_child in child.children:
                    if method_child.type in method_types:
                        methods.append(method_child)
                break

        return methods

    def _chunk_function(
        self,
        func_node,
        content: str,
        lines: List[str],
        file_path: str,
        import_context: Optional[str],
        class_name: Optional[str],
    ) -> Optional[CodeChunk]:
        """Create a chunk from a function/method node."""
        start_line = func_node.start_point[0] + 1
        end_line = func_node.end_point[0] + 1
        func_content = content[func_node.start_byte : func_node.end_byte]

        # Skip if too large
        if len(func_content) > CHUNK_SIZE * 2:
            return None

        chunk_type = "method" if class_name else "function"

        return CodeChunk(
            content=func_content,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            chunk_type=chunk_type,
            context=import_context,
        )

    def _get_node_name(self, node, content: str) -> str:
        """Extract the name from a node (class or function)."""
        # Look for name child node
        for child in node.children:
            if child.type in ["identifier", "property_identifier"]:
                return content[child.start_byte : child.end_byte]

        return "unknown"
