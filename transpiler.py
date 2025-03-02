import json
import re
import argparse
import os
import sys
import tempfile
import subprocess
import readline  # For better REPL experience
import py_compile
import shutil
from pathlib import Path
from vscode_extension_generator import generate_vscode_extension

class Transpiler:
    """
    Main transpiler class that handles conversion between custom language and Python.
    This class is responsible for loading language mappings, transpiling code,
    executing scripts, and providing a REPL environment.
    """
    def __init__(self, mapping_file):
        """
        Initialize the transpiler with a JSON mapping file.
        
        Args:
            mapping_file (str): Path to the JSON mapping file
        """
        # Load and parse the mapping file
        self.mapping_data = self._load_mapping_file(mapping_file)
        
        # Extract keyword mappings
        self.mapping = self._extract_keyword_mappings()
        
        # Extract and process special patterns
        self.special_patterns = self._extract_special_patterns()
        
        # Create reverse mapping for Python to custom language conversion
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # Prepare sorted keywords and patterns for efficient text processing
        self._prepare_patterns()
    
    def _load_mapping_file(self, mapping_file):
        """
        Load and parse the JSON mapping file.
        
        Args:
            mapping_file (str): Path to the JSON mapping file
            
        Returns:
            dict: The parsed mapping data
        """
        with open(mapping_file, 'r') as f:
            mapping_data = json.load(f)
        return mapping_data
    
    def _extract_keyword_mappings(self):
        """
        Extract keyword mappings from the loaded mapping data.
        
        Returns:
            dict: Dictionary of custom keywords to Python equivalents
        """
        # Handle structured mapping format
        if isinstance(self.mapping_data, dict) and "keywords" in self.mapping_data:
            return self.mapping_data.get("keywords", {})
        else:
            # Legacy format support with warning
            print("Warning: Using legacy mapping format. Consider updating to structured format.", file=sys.stderr)
            return self.mapping_data
    
    def _extract_special_patterns(self):
        """
        Extract special patterns from the loaded mapping data.
        
        Returns:
            dict: Dictionary of regex patterns to their Python equivalents
        """
        return self.mapping_data.get("special_patterns", {})
    
    def _prepare_patterns(self):
        """
        Prepare sorted keywords and compiled regex patterns for efficient text processing.
        """
        # Sort keywords by length (descending) to avoid partial replacements
        self.sorted_keywords = sorted(self.mapping.keys(), key=len, reverse=True)
        self.sorted_reverse_keywords = sorted(self.reverse_mapping.keys(), key=len, reverse=True)
        
        # Create regex patterns for word boundaries
        self.patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_keywords}
        self.reverse_patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_reverse_keywords}
        
        # Compile special patterns
        self.compiled_special_patterns = {re.compile(k): v for k, v in self.special_patterns.items()}

    def to_python(self, source_code):
        """
        Convert custom language code to Python.
        
        Args:
            source_code (str): Source code in custom language
            
        Returns:
            str: Equivalent Python code
        """
        result = source_code
        
        # Apply special patterns first (multi-word phrases, complex syntax)
        result = self._apply_special_patterns(result)
        
        # Then apply regular word replacements
        result = self._apply_keyword_replacements(result)
        
        # Fix common syntax issues
        result = self._fix_syntax_issues(result)
        
        # Fix indentation
        result = self._fix_indentation(result)
        
        return result
    
    def _apply_special_patterns(self, code):
        """
        Apply special regex patterns to the code.
        
        Args:
            code (str): Source code
            
        Returns:
            str: Code with special patterns replaced
        """
        for pattern, replacement in self.compiled_special_patterns.items():
            code = pattern.sub(replacement, code)
        return code
    
    def _apply_keyword_replacements(self, code):
        """
        Apply keyword replacements to the code.
        
        Args:
            code (str): Source code
            
        Returns:
            str: Code with keywords replaced
        """
        # Split the code into string literals and non-string parts
        parts = self._split_by_strings(code)
        
        # Only apply replacements to non-string parts
        for i in range(0, len(parts), 2):  # Even indices are non-string parts
            for keyword in self.sorted_keywords:
                parts[i] = self.patterns[keyword].sub(self.mapping[keyword], parts[i])
        
        # Rejoin the parts
        return ''.join(parts)
    
    def _split_by_strings(self, code):
        """
        Split code into string literals and non-string parts.
        
        Args:
            code (str): Source code
            
        Returns:
            list: Alternating non-string and string parts
        """
        # Regex to match string literals (handles both single and double quotes)
        # Accounts for escaped quotes within strings
        string_pattern = r'(\'(?:\\\'|[^\'])*\'|"(?:\\"|[^"])*")'
        
        # Split the code by string literals
        parts = re.split(string_pattern, code)
        
        # parts will have non-string parts at even indices and string literals at odd indices
        return parts
    
    def _fix_syntax_issues(self, code):
        """
        Fix common syntax issues in the transpiled code.
        
        Args:
            code (str): Transpiled code
            
        Returns:
            str: Code with syntax issues fixed
        """
        # Fix decorators - convert standalone decorators to proper Python syntax
        code = re.sub(r'@property\s*$', r'@property', code)
        code = re.sub(r'@staticmethod\s*$', r'@staticmethod', code)
        code = re.sub(r'@classmethod\s*$', r'@classmethod', code)
        
        # Fix main_character check
        code = code.replace('if __main__ ==', 'if __name__ ==')
        
        # Fix list and dict literals
        code = code.replace('list ', '')
        code = code.replace('dict ', '')
        
        # Fix L_plus_ratio exception
        code = code.replace('L_plus_del', 'Exception')
        
        return code
    
    def _fix_indentation(self, code):
        """
        Fix indentation in the transpiled code.
        
        Args:
            code (str): Code with potentially incorrect indentation
            
        Returns:
            str: Code with proper Python indentation
        """
        lines = code.split('\n')
        properly_indented_lines = []
        for line in lines:
            # Count leading spaces
            leading_spaces = len(line) - len(line.lstrip())
            # Calculate proper indentation level (4 spaces per level)
            indent_level = leading_spaces // 4
            # Create properly indented line
            properly_indented_lines.append('    ' * indent_level + line.lstrip())
        
        return '\n'.join(properly_indented_lines)
    
    def from_python(self, python_code):
        """
        Convert Python code back to custom language.
        
        Args:
            python_code (str): Python source code
            
        Returns:
            str: Equivalent custom language code
        """
        result = python_code
        
        # Split the code into string literals and non-string parts
        parts = self._split_by_strings(result)
        
        # Only apply replacements to non-string parts
        for i in range(0, len(parts), 2):  # Even indices are non-string parts
            # Apply regular word replacements
            for keyword in self.sorted_reverse_keywords:
                parts[i] = self.reverse_patterns[keyword].sub(self.reverse_mapping[keyword], parts[i])
        
        # Rejoin the parts
        result = ''.join(parts)
        
        # Then apply special patterns in reverse
        result = self._apply_reverse_special_patterns(result)
                
        return result
    
    def _apply_reverse_special_patterns(self, code):
        """
        Apply special patterns in reverse (Python to custom language).
        
        Args:
            code (str): Python code
            
        Returns:
            str: Code with special patterns reversed
        """
        # Split the code into string literals and non-string parts
        parts = self._split_by_strings(code)
        
        # Only apply replacements to non-string parts
        for i in range(0, len(parts), 2):  # Even indices are non-string parts
            for pattern, replacement in self.compiled_special_patterns.items():
                # Create reverse pattern
                reverse_pattern = re.compile(r'\b' + re.escape(replacement) + r'\b')
                # Extract capture groups if any
                match = re.search(r'\\(\d+)', pattern.pattern)
                if match:
                    # If there are capture groups, we need to handle them specially
                    capture_group = int(match.group(1))
                    # Find all matches of the reverse pattern
                    matches = reverse_pattern.finditer(parts[i])
                    for m in matches:
                        # Extract the captured value
                        captured = m.group(capture_group) if capture_group <= len(m.groups()) else ""
                        # Replace with the original pattern format
                        original_format = pattern.pattern.replace(f'\\{capture_group}', captured)
                        parts[i] = parts[i].replace(m.group(0), original_format)
                else:
                    # Simple replacement
                    parts[i] = reverse_pattern.sub(pattern.pattern, parts[i])
        
        # Rejoin the parts
        return ''.join(parts)
    
    def transpile_file(self, input_file, output_file=None, reverse=False):
        """
        Transpile a file from custom language to Python or vice versa.
        
        Args:
            input_file (str): Path to input file
            output_file (str, optional): Path to output file. If None, returns the transpiled code.
            reverse (bool): If True, transpiles from Python to custom language
            
        Returns:
            str: Result message or transpiled code
        """
        with open(input_file, 'r') as f:
            source = f.read()
        
        if reverse:
            result = self.from_python(source)
        else:
            result = self.to_python(source)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(result)
            return f"Transpiled to {output_file}"
        else:
            return result
    
    def execute_code(self, input_file, args=None, debug=False):
        """
        Execute a custom language file by transpiling to Python and running it.
        
        Args:
            input_file (str): Path to custom language file
            args (list, optional): Command-line arguments to pass to the script
            debug (bool): If True, shows the transpiled Python code
            
        Returns:
            int: Return code from the executed script
        """
        # Create a temporary file for the transpiled Python code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Transpile the input file to the temporary Python file
            self.transpile_file(input_file, temp_filename)
            
            # If debug mode is enabled, print the transpiled Python code
            if debug:
                self._print_debug_info(temp_filename)
            
            # Execute the Python file
            return_code = self._run_python_file(temp_filename, args)
            
            return return_code
        finally:
            # Clean up the temporary file unless in debug mode
            if os.path.exists(temp_filename) and not debug:
                os.remove(temp_filename)
    
    def _print_debug_info(self, python_file):
        """
        Print debug information for a transpiled Python file.
        
        Args:
            python_file (str): Path to the Python file
        """
        with open(python_file, 'r') as f:
            print("=== Transpiled Python Code ===")
            print(f.read())
            print("=============================")
    
    def _run_python_file(self, python_file, args=None):
        """
        Run a Python file with optional arguments.
        
        Args:
            python_file (str): Path to the Python file
            args (list, optional): Command-line arguments to pass to the script
            
        Returns:
            int: Return code from the executed script
        """
        # Prepare command to run the Python file
        cmd = [sys.executable, python_file]
        if args:
            cmd.extend(args)
        
        # Execute the Python file
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output and errors
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr)
        
        # If there's a syntax error, provide debugging information
        if "SyntaxError" in result.stderr:
            self._print_syntax_error_help(python_file)
        
        return result.returncode
    
    def _print_syntax_error_help(self, python_file):
        """
        Print helpful information for syntax errors.
        
        Args:
            python_file (str): Path to the Python file with the error
        """
        print("\n=== Debugging Information ===")
        print(f"The error occurred in the transpiled Python code. To debug:")
        print(f"1. Run with debug flag: python transpiler.py run {python_file} --debug")
        print(f"2. Or transpile to inspect: python transpiler.py transpile {python_file} -o debug.py")
        print("==============================")
    
    def compile_code(self, input_file, output_dir=None, keep_py=False):
        """
        Compile a custom language file to Python bytecode.
        
        Args:
            input_file (str): Path to custom language file
            output_dir (str, optional): Directory for output files
            keep_py (bool): If True, keeps the intermediate Python file
            
        Returns:
            bool: True if compilation succeeded, False otherwise
        """
        # Get the base name of the input file
        base_name = os.path.basename(input_file)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(input_file) or '.'
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a temporary Python file
        py_file = os.path.join(output_dir, f"{name_without_ext}.py")
        
        try:
            # Transpile the input file to Python
            self.transpile_file(input_file, py_file)
            
            # Compile the Python file to bytecode
            py_compile.compile(py_file, cfile=os.path.join(output_dir, f"{name_without_ext}.pyc"))
            
            print(f"Compiled to {os.path.join(output_dir, name_without_ext + '.pyc')}")
            
            # Optionally remove the intermediate Python file
            if not keep_py and os.path.exists(py_file):
                os.remove(py_file)
                
            return True
        except Exception as e:
            print(f"Compilation error: {e}", file=sys.stderr)
            # Clean up in case of error
            if os.path.exists(py_file) and not keep_py:
                os.remove(py_file)
            return False
    
    def start_repl(self):
        """
        Start a REPL (Read-Eval-Print Loop) for the custom language.
        """
        print(f"Custom Language REPL (Python {sys.version.split()[0]})")
        print("Type 'exit()' or 'quit()' to exit")
        
        # Set up readline history
        self._setup_repl_history()
        
        # Create a temporary module for the REPL
        temp_module = {}
        
        # Keep track of indentation level
        indent_level = 0
        buffer = []
        
        # Main REPL loop
        while True:
            try:
                # Get input from user
                line = self._get_repl_input(indent_level)
                
                # Check for exit commands
                if line.strip() in ('exit()', 'quit()') and indent_level == 0:
                    break
                
                # Process the input line
                indent_level = self._process_repl_line(line, buffer, indent_level, temp_module)
            
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
                buffer = []
                indent_level = 0
            except EOFError:
                print("\nExiting...")
                break
        
        # Save readline history
        self._save_repl_history()
    
    def _setup_repl_history(self):
        """
        Set up readline history for the REPL.
        """
        histfile = os.path.join(os.path.expanduser("~"), ".custom_lang_history")
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        return histfile
    
    def _get_repl_input(self, indent_level):
        """
        Get input from the user with appropriate prompt.
        
        Args:
            indent_level (int): Current indentation level
            
        Returns:
            str: User input
        """
        # Determine prompt based on indentation
        if indent_level > 0:
            prompt = "... " + "    " * indent_level
        else:
            prompt = ">>> "
        
        # Get input from user
        return input(prompt)
    
    def _process_repl_line(self, line, buffer, indent_level, temp_module):
        """
        Process a line of input in the REPL.
        
        Args:
            line (str): Input line
            buffer (list): Current code buffer
            indent_level (int): Current indentation level
            temp_module (dict): Temporary module for execution
            
        Returns:
            int: New indentation level
        """
        # Add line to buffer
        buffer.append(line)
        
        # Update indentation level
        if line.endswith(':'):
            indent_level += 1
        elif line.strip() == '' and indent_level > 0:
            indent_level -= 1
        
        # If we're back to zero indentation, execute the buffer
        if indent_level == 0 and buffer:
            self._execute_repl_buffer(buffer, temp_module)
            buffer.clear()
        
        return indent_level
    
    def _execute_repl_buffer(self, buffer, temp_module):
        """
        Execute the code in the REPL buffer.
        
        Args:
            buffer (list): Code buffer to execute
            temp_module (dict): Temporary module for execution
        """
        # Join the buffer into a single string
        code_to_execute = '\n'.join(buffer)
        
        # Transpile the custom code to Python
        python_code = self.to_python(code_to_execute)
        
        try:
            # Try to execute as an expression
            result = eval(python_code, temp_module)
            if result is not None:
                print(repr(result))
        except SyntaxError:
            try:
                # If it's not an expression, execute it as a statement
                exec(python_code, temp_module)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
    
    def _save_repl_history(self):
        """
        Save the REPL command history.
        """
        histfile = os.path.join(os.path.expanduser("~"), ".custom_lang_history")
        try:
            readline.write_history_file(histfile)
        except:
            pass


def create_default_mapping(filename):
    """
    Create a default mapping file with meme/slang terms.
    
    Args:
        filename (str): Path to the output mapping file
    """
    default_mapping = {
        "keywords": {
            "skibidi": "def",
            "toilet": "class",
            "ohio": "import",
            "rizz": "return",
            "bussin": "print",
            "fr": "for",
            "no_cap": "True",
            "cap": "False",
            "yeet": "if",
            "sus": "else",
            "vibe_check": "while",
            "finna": "try",
            "bruh": "except",
            "slay": "lambda",
            "based": "with",
            "sheesh": "pass",
            "mid": "None",
            "goated": "self",
            "npc": "object",
            "glizzy": "list",
            "drip": "dict",
            "bet": "in",
            "rent_free": "yield",
            "chad": "super",
            "karen": "raise",
            "boomer": "break",
            "zoomer": "continue",
            "stan": "from",
            "simp": "as",
            "cringe": "assert",
            "touch_grass": "exit",
            "down_bad": "False",
            "up_good": "True",
            "ong": "not",
            "lowkey": "nonlocal",
            "highkey": "global",
            "main_character": "__main__",
            "villain_arc": "__init__",
            "plot_twist": "finally",
            "gaslighting": "isinstance",
            "gatekeeping": "issubclass",
            "girlboss": "property",
            "sigma": "staticmethod",
            "alpha": "classmethod",
            "beta": "abstractmethod",
            "L_plus_ratio": "Exception",
            "skill_issue": "ValueError",
            "cope": "TypeError",
            "seethe": "KeyError",
            "mald": "IndexError"
        },
        "special_patterns": {
            "no\\s+shot": "assert",
            "on\\s+god": "global",
            "slide\\s+into\\s+(\\w+)": "import \\1",
            "spill\\s+the\\s+tea": "raise Exception",
            "ratio\\s+(\\w+)": "del \\1"
        },
        "language_info": {
            "name": "RizzLang",
            "version": "1.0.0",
            "description": "A meme-based programming language",
            "file_extension": ".ski",
            "author": "Scripting Language Factory"
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(default_mapping, f, indent=4)


def main():
    """
    Main entry point for the transpiler command-line interface.
    
    Returns:
        int: Exit code
    """
    # Create argument parser
    parser = argparse.ArgumentParser(description='Transpile, execute, or compile custom language files')
    
    # Common arguments that apply to all commands
    parser.add_argument('-c', '--config', help='JSON mapping file (defaults to mapping.json in current directory)')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Transpile command
    transpile_parser = subparsers.add_parser('transpile', help='Transpile between custom language and Python')
    transpile_parser.add_argument('input_file', help='Input file to transpile')
    transpile_parser.add_argument('-o', '--output', help='Output file (if not specified, prints to stdout)')
    transpile_parser.add_argument('-r', '--reverse', action='store_true', help='Transpile from Python to custom language')
    
    # Execute command
    execute_parser = subparsers.add_parser('run', help='Execute a custom language file')
    execute_parser.add_argument('input_file', help='Input file to execute')
    execute_parser.add_argument('args', nargs='*', help='Arguments to pass to the program')
    execute_parser.add_argument('--debug', action='store_true', help='Show transpiled Python code for debugging')
    
    # Compile command
    compile_parser = subparsers.add_parser('compile', help='Compile a custom language file to Python bytecode')
    compile_parser.add_argument('input_file', help='Input file to compile')
    compile_parser.add_argument('-o', '--output-dir', help='Output directory for compiled files')
    compile_parser.add_argument('-k', '--keep-py', action='store_true', help='Keep intermediate Python file')
    
    # REPL command
    repl_parser = subparsers.add_parser('repl', help='Start a REPL for the custom language')
    
    # Create mapping command
    create_parser = subparsers.add_parser('create-mapping', help='Create a new mapping file with default values')
    create_parser.add_argument('output_file', help='Output file for the mapping')
    
    # VS Code extension command
    vscode_parser = subparsers.add_parser('vscode', help='Generate VS Code extension for syntax highlighting')
    vscode_parser.add_argument('-o', '--output-dir', help='Output directory for the extension')
    
    args = parser.parse_args()
    
    # If no command is specified, show help
    if not args.command:
        parser.print_help()
        return 0
    
    # Handle create-mapping command
    if args.command == 'create-mapping':
        create_default_mapping(args.output_file)
        print(f"Created default mapping file at {args.output_file}")
        return 0
    
    # Ensure mapping file is provided for other commands
    if not args.config:
        # Try to find a mapping.json file in the current directory
        if os.path.exists('mapping.json'):
            args.config = 'mapping.json'
        else:
            print("Error: Mapping file is required. Use -c/--config option or create a mapping.json file in the current directory.", file=sys.stderr)
            return 1
    
    # Create transpiler
    transpiler = Transpiler(args.config)
    
    # Handle commands
    if args.command == 'transpile':
        if args.output:
            result = transpiler.transpile_file(args.input_file, args.output, args.reverse)
            print(result)
        else:
            result = transpiler.transpile_file(args.input_file, reverse=args.reverse)
            print(result)
    
    elif args.command == 'run':
        return transpiler.execute_code(args.input_file, args.args, args.debug)
    
    elif args.command == 'compile':
        transpiler.compile_code(args.input_file, args.output_dir, args.keep_py)
    
    elif args.command == 'repl':
        transpiler.start_repl()
    
    elif args.command == 'vscode':
        generate_vscode_extension(args.config, args.output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0) 