

# Scripting Language Factory

A powerful tool for creating, running, and managing custom programming languages based on any slang, meme terminology, or domain-specific vocabulary you prefer.

## Overview

This project allows you to define your own programming language syntax by mapping custom keywords to Python equivalents. It provides a complete environment for working with your custom language, including:

- Transpilation between your language and Python
- Direct execution of your language scripts
- Interactive REPL for development
- Compilation to Python bytecode
- Extensive customization options

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/scripting-language-factory.git
   cd scripting-language-factory
   ```

2. No additional dependencies required beyond Python 3.6+

## Quick Start

1. Create a default mapping file:
   ```
   python transpiler.py create-mapping my_mapping.json
   ```

2. Write a script in your custom language (e.g., `hello.ski`):
   ```
   ohio math
   
   skibidi say_hello(name):
       bussin(f"What's good, {name}!")
       rizz f"Hello function executed for {name}"
   
   yeet main_character == "__main__":
       say_hello("fam")
   ```

3. Run your script:
   ```
   python transpiler.py run hello.ski -c my_mapping.json
   ```

## Command Reference

### Create a Mapping File

```
python transpiler.py create-mapping filename.json
```

This creates a JSON file with default keyword mappings that you can customize.

### Transpile a File

```
python transpiler.py transpile input.ski -o output.py -c my_mapping.json
```

Convert your custom language to Python. Use the `-r` flag to convert from Python back to your custom language.

### Run a Script

```
python transpiler.py run script.ski -c my_mapping.json [args...]
```

Execute a script written in your custom language. Add `--debug` to see the transpiled Python code.

### Start the REPL

```
python transpiler.py repl -c my_mapping.json
```

Launch an interactive Read-Eval-Print Loop for your custom language.

### Compile to Bytecode

```
python transpiler.py compile script.ski -o output_dir -k -c my_mapping.json
```

Compile your custom language to Python bytecode (.pyc files). The `-k` flag keeps the intermediate Python file.

## Customizing Your Language

Edit the mapping file to define your own language syntax. The file has a structured format:

```json
{
    "keywords": {
        "skibidi": "def",
        "toilet": "class",
        "bussin": "print",
        "rizz": "return",
        ...
    },
    "special_patterns": {
        "no\\s+shot": "assert",
        "on\\s+god": "global",
        "spill\\s+the\\s+tea": "raise Exception",
        "ratio\\s+(\\w+)": "del \\1"
    },
    "language_info": {
        "name": "YourLanguage",
        "version": "1.0.0",
        "description": "Your custom language description",
        "file_extension": ".yourlang"
    }
}
```

- **keywords**: Simple word-to-word mappings
- **special_patterns**: Regular expressions for more complex syntax patterns
- **language_info**: Metadata about your language

You can add as many mappings as you want, including slang, meme terms, or domain-specific vocabulary.

## Special Syntax Features

The transpiler supports special multi-word phrases and patterns:

- `no shot <condition>` → `assert <condition>`
- `on god <variable>` → `global <variable>`
- `spill the tea` → `raise Exception`
- `ratio <variable>` → `del <variable>`

## Example

Here's a sample program in our default "meme language":

```
ohio math
ohio random simp rng

on god counter
counter = 0

toilet RizzCalculator(npc):
    skibidi villain_arc(goated, name="Rizz Master"):
        goated.name = name
        goated.rizz_level = 0
    
    girlboss
    skibidi rizz_level(goated):
        rizz goated.rizz_level
    
    sigma
    skibidi get_random_rizz():
        rizz rng.randint(1, 100)
    
    skibidi add_rizz(goated, amount):
        finna:
            goated.rizz_level += amount
            rizz goated.rizz_level
        bruh L_plus_ratio simp e:
            bussin(f"L + ratio: {e}")
            rizz mid

yeet main_character == "__main__":
    calculator = RizzCalculator("Rizzy McRizzface")
    
    fr i bet range(5):
        random_rizz = RizzCalculator.get_random_rizz()
        calculator.add_rizz(random_rizz)
        counter += 1
    
    bussin(f"Final rizz level: {calculator.rizz_level}")
```

## Advanced Features

- **Indentation Handling**: The transpiler automatically fixes indentation in the generated Python code.
- **Decorator Support**: Properly handles Python decorators like `@property` and `@staticmethod`.
- **Error Reporting**: Provides helpful debugging information when errors occur.
- **Command History**: The REPL maintains command history between sessions.

## Creating Your Own Language

1. Start with the default mapping file
2. Replace keywords with your preferred terms
3. Add new mappings for additional Python features
4. Create special syntax patterns for complex transformations
5. Write scripts in your new language
6. Share your language with others by distributing your mapping file

## Troubleshooting

If you encounter errors:

1. Use the `--debug` flag to see the transpiled Python code:
   ```
   python transpiler.py run script.ski --debug -c my_mapping.json
   ```

2. Transpile to Python and inspect the code:
   ```
   python transpiler.py transpile script.ski -o debug.py -c my_mapping.json
   ```

3. Check for syntax errors in your custom language script

## Contributing

Contributions are welcome! Feel free to:
- Add support for more Python features
- Improve error handling and debugging
- Create pre-defined language mappings
- Enhance the REPL experience

## License

[LICENSE.md](LICENSE.md)

## Acknowledgments

This project was inspired by the creativity of internet slang and meme culture, and the flexibility of the Python programming language.
