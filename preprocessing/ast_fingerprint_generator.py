# pip install tree-sitter==0.21.3
import os
from tree_sitter import Parser
from tree_sitter_languages import get_language
import hashlib

class MultiFormatParser:
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.java': 'java',
        '.cpp': 'cpp',
        '.hpp': 'cpp',
        '.cc': 'cpp',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.go': 'go',
        '.sh': 'bash',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.rb': 'ruby',
        '.php': 'php',
        '.c': 'c',
        '.h': 'c',
        '.rs': 'rust',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.toml': 'toml'
    }

    SPECIAL_FILES = {
        'Dockerfile': 'dockerfile'
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.language, self.lang_name, self.parser = self.get_language_parser()
        self.tree = None

    def get_language_parser(self):
        """
        Dynamically select the appropriate tree-sitter language parser based on file extension or filename
        """
        file_extension = os.path.splitext(self.file_path)[1].lower()
        file_name = os.path.basename(self.file_path)

        # Check for special files first (like Dockerfile)
        if file_name in self.SPECIAL_FILES:
            language_name = self.SPECIAL_FILES[file_name]
        # Then check for supported extensions
        elif file_extension in self.SUPPORTED_EXTENSIONS:
            language_name = self.SUPPORTED_EXTENSIONS[file_extension]
        # Handle non-code files
        elif file_extension in ['.txt', '.csv', '']:
            return None, 'text', None
        else:
            raise ValueError(f"Unsupported file type or name: {file_extension or file_name}")

        try:
            # Create parser and get language
            parser = Parser()
            language = get_language(language_name)
            parser.set_language(language)
            return language, language_name, parser
        except Exception as e:
            print(f"Error initializing parser for {language_name}: {e}")
            raise

    def parse_entire_file(self):
        """
        Parse the file into tree-sitter AST with dynamic language support
        """
        if self.parser is None:
            return None  # Non-code files don't need parsing
        
        try:
            # Read and parse file
            with open(self.file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            
            # Parse entire file into AST
            self.tree = self.parser.parse(code.encode())
            return self.tree
        except Exception as e:
            print(f"Error parsing file {self.file_path}: {e}")
            return None

    def find_secret_nodes(self, start_line, end_line, start_column=None, end_column=None):
        """
        Find nodes within specified line and optional column range
        """
        if self.lang_name == 'text':
            return None  # Text files are handled differently

        if self.tree is None:
            raise ValueError("AST tree is not parsed. Please parse the file first.")

        root_node = self.tree.root_node
        target_nodes = []

        def traverse(node):
            # Check if node is within the specified line range
            if start_line <= node.start_point[0] + 1 <= end_line:
                # If column specifics are provided, do additional filtering
                if start_column is not None and end_column is not None:
                    if (start_column <= node.start_point[1] and 
                        node.end_point[1] <= end_column):
                        target_nodes.append(node)
                else:
                    target_nodes.append(node)
            
            # Recursively traverse child nodes
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return target_nodes

    def generate_fingerprint_with_secret(self, nodes):
        """
        Generate a SHA-256 fingerprint from the combined text of nodes
        """
        combined_string = ""
        for node in nodes:
            combined_string += node.text.decode('utf-8')

        # Generate fingerprint using SHA-256
        fingerprint = hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
        return fingerprint

    def generate_fingerprint_for_text(self, start_line, end_line):
        """
        Generate a SHA-256 fingerprint for text-based files (e.g., txt, csv)
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                relevant_lines = lines[start_line - 1:end_line]
                combined_string = "".join(relevant_lines)
                fingerprint = hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
                return fingerprint
        except Exception as e:
            print(f"Error reading text file {self.file_path}: {e}")
            return None

    def process_file_findings(self, start_line, end_line, start_column=None, end_column=None):
        """
        Process file with multiple findings and generate fingerprints
        """
        try:
            if self.lang_name == 'text':
                # Handle text-based files
                fingerprint = self.generate_fingerprint_for_text(start_line, end_line)
                if fingerprint:
                    print(f"Generated Fingerprint for lines {start_line}-{end_line}: {fingerprint}")
                else:
                    print(f"Failed to generate fingerprint for lines {start_line}-{end_line}")
            else:
                # Parse the entire file only once
                tree = self.parse_entire_file()

                if tree:
                    print(f"Parsing file with {self.lang_name} language parser")
                    
                    # Locate the secret nodes
                    secret_nodes = self.find_secret_nodes(start_line, end_line, start_column, end_column)

                    if secret_nodes:
                        # Generate the fingerprint
                        fingerprint = self.generate_fingerprint_with_secret(secret_nodes)
                        print(f"Generated Fingerprint for lines {start_line}-{end_line}: {fingerprint}")
                        
                        # Optional: Print node texts for debugging
                        # for node in secret_nodes:
                        #     print(f"Node text: {node.text.decode('utf-8')}")
                    else:
                        print(f"No nodes found for lines {start_line}-{end_line}")
                else:
                    print("Failed to parse the file.")
        except Exception as e:
            print(f"Error processing file {self.file_path}: {e}")

# Example usage
if __name__ == "__main__":
    FILE_PATH = "/home/pk/Documents/projects/Application-Security-platform/scan-workers/ast_fingerprint/test.go"
    findings = [
        {'start_line': 1, 'end_line': 3},
        {'start_line': 5, 'end_line': 6},
        {'start_line': 8, 'end_line': 10}
    ]

    try:
        # Create an instance of MultiFormatParser
        parser = MultiFormatParser(FILE_PATH)

        # Process each finding
        for finding in findings:
            parser.process_file_findings(
                finding['start_line'],
                finding['end_line'],
                finding.get('start_column'),
                finding.get('end_column')
            )
    except Exception as e:
        print(f"Error: {e}")