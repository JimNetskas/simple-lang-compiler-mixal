# Mini C-like Compiler to MIXAL

A compiler implementation for a simple C-like language, written in **Python** using **PLY** (Python Lex-Yacc). It performs lexical, syntax, and semantic analysis before generating **MIXAL assembly code**, executable on the **MIX** architecture (e.g., via GNU MDK).

**University:** Aristotle University of Thessaloniki
**Course:** Programming Languages & Compilers
**Author:** Dimitrios Netskas (AEM: 4341)

---

## 🚀 Features

### 1. Language Support
* **Data Types:** `int` and boolean logic (0/1).
* **Control Flow:** `if`, `if/else`, `while`, `break`, `return`.
* **Functions:** Support for function definitions, calls, and recursion.
* **Comments:** C-style line comments (`//`).

### 2. Compiler Pipeline
* **Lexical Analysis:** Handles tokens, ignores whitespace, and detects illegal number formats (e.g., leading zeros like `05`).
* **Syntax Analysis:** Generates an Abstract Syntax Tree (AST) using tuples.
* **Semantic Analysis:** Performs robust checks before code generation:
    * Existence of `main` function.
    * Detection of `break` statements outside loops.
    * Undeclared variables and functions.
    * Duplicate declarations (variables and functions).
    * Function call validation (argument count matching).
    * **Division by zero** detection.
* **Code Generation:** Produces valid `.mixal` code, managing registers (`rA`, `rX`) and memory storage.

---

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `main.py` | **Entry point**. Orchestrates the pipeline and generates the `output/` folder. |
| `lexer.py` | Token definitions, regex rules, and error handling. |
| `parser.py` | Grammar rules and AST construction. |
| `symbol_table.py` | Builds scope-based symbol tables (global vs method). |
| `semantic_check.py` | Validates logic (undeclared vars, types, div-by-zero, etc.). |
| `mixal_generator.py` | Generates the final assembly code (`.mixal`). |

---

## 🛠️ Installation

### Prerequisites
* Python 3.10+
* PLY (Python Lex-Yacc)

### Setup
1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Create a virtual environment (Optional but recommended):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If `requirements.txt` is missing, simply run `pip install ply`)*.

---

## ▶️ Usage

### 1. Edit Source Code
The source code to be compiled is currently located inside `main.py`.
1.  Open `main.py`.
2.  Locate the `test_code` variable.
3.  Replace the content with your own C-like code.

**Example Input:**
```c
int main() {
    int a;
    a = 10 + 5;
    return a;
}
2. Run the Compiler
Execute the main script via your terminal:

Bash
python main.py
3. Check Outputs
The compiler creates an output/ directory containing the following files:

lexical_analysis.txt: Stream of tokens found.

ast_output.txt: The Abstract Syntax Tree structure.

symbol_table.txt: Variables and functions per scope.

semantic_checks.txt: Results of semantic validation. If errors exist, compilation stops here.

main.mixal: The final executable assembly code (generated only if no errors occur).

💻 Running the MIXAL Code
To execute the generated assembly, use a MIX emulator like GNU MDK (mixvm).
+1

Load the output file: output/main.mixal.

Run it in your emulator:

Bash
mixvm -r output/main.mixal
(Alternatively, load it into the MDK GUI debugger).

⚠️ Error Handling Examples
The compiler will abort generation and report errors in the console and output/semantic_checks.txt for cases such as:

Syntax Errors: e.g., int a = ;.

Semantic Errors:


break; used outside a while loop.


b = a + 1; where a is not declared.


method(1, 2) calling a function that expects 3 arguments.


Division by zero (e.g., a = 10 / 0;).


Project created for the course "Programming Languages and Compilers", September 2025.