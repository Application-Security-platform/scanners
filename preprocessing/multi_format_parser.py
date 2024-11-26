import hashlib
import os
import tree_sitter_python as tspython
import tree_sitter_java as tsjava
import tree_sitter_cpp as tscpp
import tree_sitter_yaml as tsyaml
import tree_sitter_go as tsgo
import tree_sitter_bash as tsbash 
import tree_sitter_json as tsjson

import tree_sitter_fortran as tsfortran

import tree_sitter_glsl as tsglsl
import tree_sitter_gstlaunch as tsgstlaunch 
import tree_sitter_haskell as tshaskell
import tree_sitter_hlsl as tshlsl

import tree_sitter_hlsplaylist as tshlsplaylist
import tree_sitter_fluentbit as tsfluentbit
import tree_sitter_ruby as tsruby
import tree_sitter_php as tsphp
import tree_sitter_c as tsc
import tree_sitter_rust as tsrust
import tree_sitter_html as tshtml
import tree_sitter_css as tscss
import tree_sitter_toml as tstmol
import tree_sitter_typescript as tsts

import tree_sitter_idl as tsidl
import tree_sitter_jsdoc as tsjsdoc
import tree_sitter_julia as tsjulia
import tree_sitter_kotlin as tskotlin
import tree_sitter_rust as tsrust
import tree_sitter_html as tshtml
import tree_sitter_css as tscss
import tree_sitter_toml as tstmol
import tree_sitter_typescript as tsts


from tree_sitter import Language, Parser

class ASTFingerprintParser:
    # Language mapping
    LANGUAGE_PARSERS = {
        '.py': (tspython.language(), 'python'),
        '.java': (tsjava.language(), 'java'),
        '.cpp': (tscpp.language(), 'cpp'),
        '.hpp': (tscpp.language(), 'cpp'),
        '.cc': (tscpp.language(), 'cpp'),
        '.yaml': (tsyaml.language(), 'yaml'),
        '.yml': (tsyaml.language(), 'yaml'),
        '.go': (tsgo.language(), 'go'),
        '.json': (tsjson.language(), 'json'),
        'Dockerfile': (tsbash.language(), 'dockerfile'),
        '.sh': (tsbash.language(), 'bash')
    }

    SPECIAL_LANGUAGE_PARSERS = {
        'Dockerfile': (tsbash.language(), 'dockerfile')
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.language, self.lang_name = self.get_language_parser()
        self.tree = None

    def get_language_parser(self):
        """
        Dynamically select the appropriate tree-sitter language parser based on file extension
        """
        try:
            file_extension = os.path.splitext(self.file_path)[1].lower()
            file_name = os.path.basename(self.file_path)
            print(f'{file_extension=}')
            if file_extension in ASTFingerprintParser.LANGUAGE_PARSERS:
                language_func, language_name = ASTFingerprintParser.LANGUAGE_PARSERS[file_extension]
                language = Language(language_func)
                return language, language_name
            elif file_name in ASTFingerprintParser.SPECIAL_LANGUAGE_PARSERS:
                language_func, language_name = ASTFingerprintParser.SPECIAL_LANGUAGE_PARSERS[file_name]
                language = Language(language_func)
                return language, language_name
            elif file_extension in ['.txt', '.csv', '']:  # Handle non-code files
                return None, 'text'
            else:
                raise ValueError(f"Unsupported file type or name: {file_extension or file_name}")
        except TypeError:
            raise TypeError("expected filepath, not NoneType")
        

    # @memory.cache
    def parse_entire_file(self):
        """
        Parse the file into tree-sitter AST with dynamic language support
        """
        try:
            # Create parser with the specific language
            parser = Parser()
            parser.language = self.language

            # Read and parse file
            with open(self.file_path, 'r', encoding='utf-8') as file:
                code = file.read()
            
            # Parse entire file into AST
            self.tree = parser.parse(bytes(code, 'utf8'))
            return self.tree
        except Exception as e:
            print(f"Error parsing file {self.file_path}: {e}")
            return None

    def find_secret_nodes(self, start_line, end_line, start_column=None, end_column=None):
        """
        Find nodes within specified line and optional column range
        """
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
        # Parse the entire file only once

        if self.lang_name == 'text':
            # Handle text-based files (e.g., .txt, .csv)
            fingerprint = self.generate_fingerprint_for_text(start_line, end_line)
            if fingerprint:
                print(f"Generated Fingerprint for lines {start_line}-{end_line}: {fingerprint}")
                return fingerprint
            else:
                print(f"Failed to generate fingerprint for lines {start_line}-{end_line}")

        else:
            tree = self.parse_entire_file()

            if tree:
                print(f"Parsing file with {self.lang_name} language parser")
                
                # Locate the secret nodes
                secret_nodes = self.find_secret_nodes(start_line, end_line, start_column, end_column)

                if secret_nodes:
                    # Generate the fingerprint
                    fingerprint = self.generate_fingerprint_with_secret(secret_nodes)
                    print(f"Generated Fingerprint for lines {start_line}-{end_line}: {fingerprint}")
                    return fingerprint
                else:
                    print(f"No nodes found for lines {start_line}-{end_line}")
            else:
                print("Failed to parse the file.")

# Making the script into a module
if __name__ == "__main__":
    # Example usage of the module
    # file_path = "/home/pk/Documents/projects/Application-Security-platform/scan-workers/common/preprocess_data.py"
    FILE_PATH = "/home/pk/Documents/projects/Application-Security-platform/scan-workers/ast_fingerprint/test.go"
    findings = [
        {'start_line': 1, 'end_line': 3},
        {'start_line': 5, 'end_line': 6},
        {'start_line': 8, 'end_line': 10}
    ]

    # Create an instance of MultiFormatParser
    parser = ASTFingerprintParser(FILE_PATH)

    # Process each finding
    for finding in findings:
        parser.process_file_findings(
            finding['start_line'],
            finding['end_line'],
            finding.get('start_column'),
            finding.get('end_column')
        )
