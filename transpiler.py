import json
import re
import argparse
import os

class Transpiler:
    def __init__(self, mapping_file):
        """Initialize the transpiler with a JSON mapping file."""
        with open(mapping_file, 'r') as f:
            self.mapping = json.load(f)
        
        # Create reverse mapping for Python to custom language
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # Sort keywords by length (descending) to avoid partial replacements
        self.sorted_keywords = sorted(self.mapping.keys(), key=len, reverse=True)
        self.sorted_reverse_keywords = sorted(self.reverse_mapping.keys(), key=len, reverse=True)
        
        # Create regex patterns for word boundaries
        self.patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_keywords}
        self.reverse_patterns = {k: re.compile(r'\b' + re.escape(k) + r'\b') for k in self.sorted_reverse_keywords}

    def to_python(self, source_code):
        """Convert custom language to Python."""
        result = source_code
        for keyword in self.sorted_keywords:
            result = self.patterns[keyword].sub(self.mapping[keyword], result)
        return result
    
    def from_python(self, python_code):
        """Convert Python to custom language."""
        result = python_code
        for keyword in self.sorted_reverse_keywords:
            result = self.reverse_patterns[keyword].sub(self.reverse_mapping[keyword], result)
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

def main():
    parser = argparse.ArgumentParser(description='Transpile between custom language and Python')
    parser.add_argument('input_file', help='Input file to transpile')
    parser.add_argument('-o', '--output', help='Output file (if not specified, prints to stdout)')
    parser.add_argument('-m', '--mapping', required=True, help='JSON mapping file')
    parser.add_argument('-r', '--reverse', action='store_true', help='Transpile from Python to custom language')
    
    args = parser.parse_args()
    
    transpiler = Transpiler(args.mapping)
    
    if args.output:
        result = transpiler.transpile_file(args.input_file, args.output, args.reverse)
        print(result)
    else:
        result = transpiler.transpile_file(args.input_file, reverse=args.reverse)
        print(result)

if __name__ == "__main__":
    main() 