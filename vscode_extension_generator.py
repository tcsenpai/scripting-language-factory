import json
import os
import shutil
import argparse
import sys
from pathlib import Path

def generate_vscode_extension(mapping_file, output_dir=None):
    """Generate a VS Code extension for syntax highlighting based on a mapping file."""
    # Load the mapping file
    with open(mapping_file, 'r') as f:
        mapping_data = json.load(f)
    
    # Extract language info
    if "language_info" in mapping_data:
        language_info = mapping_data["language_info"]
        language_name = language_info.get("name", "CustomLanguage")
        language_extension = language_info.get("file_extension", ".custom")
        language_description = language_info.get("description", "A custom programming language")
    else:
        language_name = "CustomLanguage"
        language_extension = ".custom"
        language_description = "A custom programming language"
    
    # Remove leading dot from extension if present
    if language_extension.startswith('.'):
        language_extension = language_extension[1:]
    
    # Create language ID (lowercase, no spaces)
    language_id = language_name.lower().replace(' ', '-')
    
    # Determine output directory
    if output_dir is None:
        output_dir = f"vscode-{language_id}"
    
    # Create extension directory structure
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "syntaxes"), exist_ok=True)
    
    # Generate package.json
    package_json = {
        "name": f"{language_id}",
        "displayName": language_name,
        "description": language_description,
        "version": "0.1.0",
        "engines": {
            "vscode": "^1.60.0"
        },
        "categories": [
            "Programming Languages"
        ],
        "contributes": {
            "languages": [
                {
                    "id": language_id,
                    "aliases": [language_name],
                    "extensions": [language_extension],
                    "configuration": f"./language-configuration.json"
                }
            ],
            "grammars": [
                {
                    "language": language_id,
                    "scopeName": f"source.{language_id}",
                    "path": f"./syntaxes/{language_id}.tmLanguage.json"
                }
            ]
        }
    }
    
    # Generate language-configuration.json
    language_config = {
        "comments": {
            "lineComment": "#",
        },
        "brackets": [
            ["{", "}"],
            ["[", "]"],
            ["(", ")"]
        ],
        "autoClosingPairs": [
            { "open": "{", "close": "}" },
            { "open": "[", "close": "]" },
            { "open": "(", "close": ")" },
            { "open": "\"", "close": "\"", "notIn": ["string"] },
            { "open": "'", "close": "'", "notIn": ["string", "comment"] }
        ],
        "surroundingPairs": [
            ["{", "}"],
            ["[", "]"],
            ["(", ")"],
            ["\"", "\""],
            ["'", "'"]
        ],
        "indentationRules": {
            "increaseIndentPattern": "^.*:\\s*$",
            "decreaseIndentPattern": "^\\s*$"
        }
    }
    
    # Extract keywords for syntax highlighting
    keywords = mapping_data.get("keywords", {})
    special_patterns = mapping_data.get("special_patterns", {})
    
    # Group keywords by their Python equivalents
    keyword_groups = {
        "control": [],      # if, else, for, while, etc.
        "declaration": [],  # def, class, import, etc.
        "operator": [],     # and, or, not, in, etc.
        "constant": [],     # True, False, None
        "builtin": [],      # print, len, etc.
        "storage": [],      # global, nonlocal
        "exception": []     # try, except, finally, raise
    }
    
    # Map Python keywords to their groups
    python_keyword_groups = {
        "if": "control", "else": "control", "elif": "control", 
        "for": "control", "while": "control", "break": "control", 
        "continue": "control", "return": "control", "in": "operator",
        "def": "declaration", "class": "declaration", "import": "declaration",
        "from": "declaration", "as": "declaration", "with": "declaration",
        "True": "constant", "False": "constant", "None": "constant",
        "print": "builtin", "len": "builtin", "range": "builtin",
        "global": "storage", "nonlocal": "storage",
        "try": "exception", "except": "exception", "finally": "exception",
        "raise": "exception", "assert": "exception", "Exception": "exception"
    }
    
    # Categorize custom keywords
    for custom_keyword, python_equiv in keywords.items():
        group = python_keyword_groups.get(python_equiv, "builtin")
        keyword_groups[group].append(custom_keyword)
    
    # Add special pattern keywords
    for pattern, python_equiv in special_patterns.items():
        # Extract the base keyword from the pattern (e.g., "no\\s+shot" -> "no shot")
        base_keyword = pattern.replace("\\s+", " ").replace("\\(\\w+\\)", "").strip()
        python_base = python_equiv.split()[0] if " " in python_equiv else python_equiv
        group = python_keyword_groups.get(python_base, "builtin")
        if base_keyword not in keyword_groups[group]:
            keyword_groups[group].append(base_keyword)
    
    # Generate TextMate grammar
    grammar = {
        "$schema": "https://raw.githubusercontent.com/martinring/tmlanguage/master/tmlanguage.json",
        "name": language_name,
        "patterns": [
            { "include": "#keywords" },
            { "include": "#strings" },
            { "include": "#comments" },
            { "include": "#numbers" },
            { "include": "#function-call" },
            { "include": "#decorator" }
        ],
        "repository": {
            "keywords": {
                "patterns": [
                    {
                        "name": "keyword.control." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["control"]) + ")\\b"
                    },
                    {
                        "name": "keyword.declaration." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["declaration"]) + ")\\b"
                    },
                    {
                        "name": "keyword.operator." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["operator"]) + ")\\b"
                    },
                    {
                        "name": "constant.language." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["constant"]) + ")\\b"
                    },
                    {
                        "name": "support.function." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["builtin"]) + ")\\b"
                    },
                    {
                        "name": "storage.modifier." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["storage"]) + ")\\b"
                    },
                    {
                        "name": "keyword.control.exception." + language_id,
                        "match": "\\b(" + "|".join(keyword_groups["exception"]) + ")\\b"
                    }
                ]
            },
            "strings": {
                "patterns": [
                    {
                        "name": "string.quoted.double." + language_id,
                        "begin": "\"",
                        "end": "\"",
                        "patterns": [
                            {
                                "name": "constant.character.escape." + language_id,
                                "match": "\\\\."
                            }
                        ]
                    },
                    {
                        "name": "string.quoted.single." + language_id,
                        "begin": "'",
                        "end": "'",
                        "patterns": [
                            {
                                "name": "constant.character.escape." + language_id,
                                "match": "\\\\."
                            }
                        ]
                    },
                    {
                        "name": "string.quoted.triple." + language_id,
                        "begin": "\"\"\"",
                        "end": "\"\"\"",
                        "patterns": [
                            {
                                "name": "constant.character.escape." + language_id,
                                "match": "\\\\."
                            }
                        ]
                    }
                ]
            },
            "comments": {
                "patterns": [
                    {
                        "name": "comment.line.number-sign." + language_id,
                        "match": "#.*$"
                    }
                ]
            },
            "numbers": {
                "patterns": [
                    {
                        "name": "constant.numeric." + language_id,
                        "match": "\\b[0-9]+(\\.[0-9]+)?\\b"
                    }
                ]
            },
            "function-call": {
                "patterns": [
                    {
                        "name": "entity.name.function." + language_id,
                        "match": "\\b([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\("
                    }
                ]
            },
            "decorator": {
                "patterns": [
                    {
                        "name": "entity.name.function.decorator." + language_id,
                        "match": "^\\s*(" + "|".join(keyword_groups["storage"]) + ")\\s*$"
                    }
                ]
            }
        },
        "scopeName": "source." + language_id
    }
    
    # Write files
    with open(os.path.join(output_dir, "package.json"), 'w') as f:
        json.dump(package_json, f, indent=4)
    
    with open(os.path.join(output_dir, "language-configuration.json"), 'w') as f:
        json.dump(language_config, f, indent=4)
    
    with open(os.path.join(output_dir, "syntaxes", f"{language_id}.tmLanguage.json"), 'w') as f:
        json.dump(grammar, f, indent=4)
    
    # Create README.md
    with open(os.path.join(output_dir, "README.md"), 'w') as f:
        f.write(f"# {language_name} VS Code Extension\n\n")
        f.write(f"This extension provides syntax highlighting for {language_name} files.\n") 