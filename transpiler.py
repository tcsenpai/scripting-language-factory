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
    def __init__(self, mapping_file):
        """Initialize the transpiler with a JSON mapping file."""
        with open(mapping_file, 'r') as f:
            mapping_data = json.load(f)
        
        # Handle structured mapping format
        if isinstance(mapping_data, dict) and "keywords" in mapping_data:
            self.mapping = mapping_data.get("keywords", {})
        else:
            # Convert legacy format to structured format
            self.mapping = mapping_data
            print("Warning: Using legacy mapping format. Consider updating to structured format.", file=sys.stderr)
        
        special_patterns_raw = mapping_data.get("special_patterns", {})
        
        # Convert string patterns to actual regex patterns
        self.special_patterns = {}
        for pattern_str, replacement in special_patterns_raw.items():
            self.special_patterns[pattern_str] = replacement
        
        # Create reverse mapping for Python to custom language
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # Sort keywords by length (descending) to avoid partial replacements
        self.sorted_keywords = sorted(self.mapping.keys(), key=len, reverse=True)
        self.sorted_reverse_keywords = sorted(self.reverse_mapping.keys(), key=len, reverse=True)
        
        # Create regex patterns for word boundaries
        self.patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_keywords}
        self.reverse_patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_reverse_keywords}
        
        # Compile special patterns
        self.compiled_special_patterns = {re.compile(k): v for k, v in self.special_patterns.items()}

    def to_python(self, source_code):
        """Convert custom language to Python."""
        result = source_code
        
        # Apply special patterns first
        for pattern, replacement in self.compiled_special_patterns.items():
            result = pattern.sub(replacement, result)
        
        # Then apply regular word replacements
        for keyword in self.sorted_keywords:
            result = self.patterns[keyword].sub(self.mapping[keyword], result)
            
        # Fix common syntax issues
        
        # Fix decorators - first convert standalone decorators to proper Python syntax
        result = re.sub(r'@property\s*$', r'@property', result)
        result = re.sub(r'@staticmethod\s*$', r'@staticmethod', result)
        result = re.sub(r'@classmethod\s*$', r'@classmethod', result)
        
        # Fix main_character check
        result = result.replace('if __main__ ==', 'if __name__ ==')
        
        # Fix list and dict literals
        result = result.replace('list ', '')
        result = result.replace('dict ', '')
        
        # Fix L_plus_ratio exception
        result = result.replace('L_plus_del', 'Exception')
        
        # Fix indentation
        lines = result.split('\n')
        properly_indented_lines = []
        for line in lines:
            # Count leading spaces
            leading_spaces = len(line) - len(line.lstrip())
            # Calculate proper indentation level (4 spaces per level)
            indent_level = leading_spaces // 4
            # Create properly indented line
            properly_indented_lines.append('    ' * indent_level + line.lstrip())
        
        result = '\n'.join(properly_indented_lines)
        
        return result
    
    def from_python(self, python_code):
        """Convert Python to custom language."""
        result = python_code
        
        # Apply regular word replacements first
        for keyword in self.sorted_reverse_keywords:
            result = self.reverse_patterns[keyword].sub(self.reverse_mapping[keyword], result)
        
        # Then apply special patterns in reverse
        for pattern, replacement in self.compiled_special_patterns.items():
            # Create reverse pattern
            reverse_pattern = re.compile(r'\b' + re.escape(replacement) + r'\b')
            # Extract capture groups if any
            match = re.search(r'\\(\d+)', pattern.pattern)
            if match:
                # If there are capture groups, we need to handle them specially
                capture_group = int(match.group(1))
                # Find all matches of the reverse pattern
                matches = reverse_pattern.finditer(result)
                for m in matches:
                    # Extract the captured value
                    captured = m.group(capture_group) if capture_group <= len(m.groups()) else ""
                    # Replace with the original pattern format
                    original_format = pattern.pattern.replace(f'\\{capture_group}', captured)
                    result = result.replace(m.group(0), original_format)
            else:
                # Simple replacement
                result = reverse_pattern.sub(pattern.pattern, result)
                
        return result
    
    def transpile_file(self, input_file, output_file=None, reverse=False):
        """Transpile a file from custom language to Python or vice versa."""
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
        """Execute a custom language file by transpiling to Python and running it."""
        # Create a temporary file for the transpiled Python code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        try:
            # Transpile the input file to the temporary Python file
            self.transpile_file(input_file, temp_filename)
            
            # If debug mode is enabled, print the transpiled Python code
            if debug:
                with open(temp_filename, 'r') as f:
                    print("=== Transpiled Python Code ===")
                    print(f.read())
                    print("=============================")
            
            # Prepare command to run the Python file
            cmd = [sys.executable, temp_filename]
            if args:
                cmd.extend(args)
            
            # Execute the Python file
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print output and errors
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(result.stderr, end='', file=sys.stderr)
            
            # If there's a syntax error, try to map it back to the original file
            if "SyntaxError" in result.stderr:
                print("\n=== Debugging Information ===")
                print(f"The error occurred in the transpiled Python code. To debug:")
                print(f"1. Run with debug flag: python transpiler.py run {input_file} --debug")
                print(f"2. Or transpile to inspect: python transpiler.py transpile {input_file} -o debug.py")
                print("==============================")
            
            return result.returncode
        finally:
            # Clean up the temporary file unless in debug mode
            if os.path.exists(temp_filename) and not debug:
                os.remove(temp_filename)
    
    def compile_code(self, input_file, output_dir=None, keep_py=False):
        """Compile a custom language file to Python bytecode."""
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
        """Start a REPL (Read-Eval-Print Loop) for the custom language."""
        print(f"Custom Language REPL (Python {sys.version.split()[0]})")
        print("Type 'exit()' or 'quit()' to exit")
        
        # Set up readline history
        histfile = os.path.join(os.path.expanduser("~"), ".custom_lang_history")
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        
        # Create a temporary module for the REPL
        temp_module = {}
        
        # Keep track of indentation level
        indent_level = 0
        buffer = []
        
        while True:
            try:
                # Determine prompt based on indentation
                if indent_level > 0:
                    prompt = "... " + "    " * indent_level
                else:
                    prompt = ">>> "
                
                # Get input from user
                line = input(prompt)
                
                # Check for exit commands
                if line.strip() in ('exit()', 'quit()') and indent_level == 0:
                    break
                
                # Add line to buffer
                buffer.append(line)
                
                # Update indentation level
                if line.endswith(':'):
                    indent_level += 1
                elif line.strip() == '' and indent_level > 0:
                    indent_level -= 1
                
                # If we're back to zero indentation, execute the buffer
                if indent_level == 0 and buffer:
                    # Join the buffer into a single string
                    code_to_execute = '\n'.join(buffer)
                    buffer = []
                    
                    # Transpile the custom code to Python
                    python_code = self.to_python(code_to_execute)
                    
                    try:
                        # Execute the Python code
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
            
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt")
                buffer = []
                indent_level = 0
            except EOFError:
                print("\nExiting...")
                break
        
        # Save readline history
        try:
            readline.write_history_file(histfile)
        except:
            pass

def main():
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
        return
    
    # Handle create-mapping command
    if args.command == 'create-mapping':
        create_default_mapping(args.output_file)
        print(f"Created default mapping file at {args.output_file}")
        return
    
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

def create_default_mapping(filename):
    """Create a default mapping file with meme/slang terms."""
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

if __name__ == "__main__":
    sys.exit(main() or 0) 