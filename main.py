from lexer import lexer
from parser import parser
import pprint, os, sys, io
from symbol_table import build_symbol_table
from mixal_generator import MixalGenerator
from semantic_check import (
    check_undeclared_variables,
    check_main_exists,
    check_break_outside_while,
    check_duplicate_declarations,
    check_duplicate_functions,
    check_division_by_zero,
)


test_code = '''
int method1(int a)
{
 int b;
 b = a+10;
 return b;
}
int method2(int c, int d)
{
 int e;
 e = method1(c);
 e = e + d;
 return e;
}
int main()
{
 return method2(5,6);
}
'''

# 1)Δημιουργία φακέλου
os.makedirs("output", exist_ok=True)

# 2)Λεξική ανάλυση
lexer.input(test_code)
with open("output/lexical_analysis.txt", "w", encoding="utf-8") as f:
    f.write("--- Lexical Analysis (tokens) ---\n\n")
    while True:
        tok = lexer.token()
        if not tok:
            break
        f.write(f"{tok}\n")
print("✅ Lexical analysis generated at output/lexical_analysis")

lexer.lineno = 1           # reset line counter
lexer.input(test_code)     # ξαναφόρτωσε το ίδιο source

# 3) PARSE — αν αποτύχει, ΜΗΝ συνεχίσεις
try:
    result = parser.parse(test_code, lexer=lexer)
except SyntaxError:
    print("❌ Syntax errors — aborting.")
    sys.exit(1)

# 4) AST output
with open("output/ast_output.txt", "w", encoding="utf-8") as f:
    f.write("--- Abstract Syntax Tree ---\n\n")
    pprint.pprint(result, stream=f)
print("✅ Abstract Syntax Tree generated at output/ast_output")

# 5) Symbol table
symbol_table = build_symbol_table(result)
with open("output/symbol_table.txt", "w", encoding="utf-8") as f:
    f.write("--- Symbol Table ---\n\n")
    pprint.pprint(symbol_table, stream=f)


sem_buf = io.StringIO()
# τρέξε όλους τους ελέγχους γράφοντας ΚΑΙ στο buffer
check_undeclared_variables(result, symbol_table, stream=sem_buf)
check_main_exists(symbol_table, stream=sem_buf)
check_break_outside_while(result, symbol_table, stream=sem_buf)
check_duplicate_declarations(symbol_table, stream=sem_buf)
check_duplicate_functions(symbol_table, stream=sem_buf)
check_division_by_zero(result, stream=sem_buf)

# γράψε το περιεχόμενο του buffer στο αρχείο
os.makedirs("output", exist_ok=True)
with open("output/semantic_checks.txt", "w", encoding="utf-8") as f:
    f.write("--- Semantic Checks ---\n\n")
    f.write(sem_buf.getvalue())

# αν υπάρχουν μηνύματα, σταμάτα εδώ
if sem_buf.getvalue().strip():
    print("❌ Semantic errors — aborting codegen.")
    sys.exit(1)

# 6) Codegen μόνο αν όλα ΟΚ
gen = MixalGenerator(symbol_table=symbol_table, entry="main")
mixal_text = gen.gen_program(result)
with open("output/main.mixal", "w", encoding="utf-8") as f:
    f.write(mixal_text)
print("✅ MIXAL generated at output/main.mixal")
