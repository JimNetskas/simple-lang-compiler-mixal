# Mini Compiler (PLY → MIXAL)

Compiler για απλή γλώσσα τύπου C, υλοποιημένος σε Python με PLY (lex/yacc).
Παράγει MIXAL κώδικα εκτελέσιμο σε MIX VM (GNU MDK).

## Περιεχόμενα
- lexer.py: Λεξική ανάλυση (tokens, σχόλια //, έλεγχος leading zeros)
- parser.py: Συντακτική ανάλυση βάσει γραμματικής, παραγωγή AST (tuples)
- symbol_table.py: Πίνακας συμβόλων (global + ανά μέθοδο)
- semantic_check.py: Σημασιολογικοί έλεγχοι (main, break, duplicates, undeclared, calls, /0)
- mixal_generator.py: Παραγωγή κώδικα MIXAL (labels, const pool, control flow, calls)
- main.py: Τρέχει όλη τη ροή και γράφει output/* (tokens, AST, symtable, semantic checks, main.mixal)

## Εγκατάσταση
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
