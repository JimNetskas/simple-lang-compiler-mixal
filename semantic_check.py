def check_undeclared_variables(ast, symbol_table, stream=None):
    # Εντοπίζει αναφορές σε αδήλωτες μεταβλητές και σφάλματα κλήσης συναρτήσεων (undefined/λάθος πλήθος ορισμάτων).
    
    # Αν δεν έχουμε σωστή ρίζα προγράμματος, δεν υπάρχει κάτι να ελέγξουμε.
    if not ast or ast[0] != 'program':  # αν δεν βρει τον κόμβο 'program', τερματίζει
        return

    # Παίρνουμε τη λίστα με όλες τις μεθόδους του προγράμματος.
    methods = ast[1]

    # Φτιάχνουμε λεξικό με ΟΛΕΣ τις δηλωμένες συναρτήσεις στο global scope:
    #  όνομα_συνάρτησης -> entry (περιέχει params, τύπο κ.λπ.)
    declared_funcs = {entry['name']: entry for entry in symbol_table.get("global", [])}

    # Σαρώνονται όλες οι μέθοδοι του AST
    for method in methods:
        if method[0] != 'method':
            continue  #αγνοώ ό,τι δεν είναι μέθοδος

        # method = ('method', return_type, method_name, params, body)
        _, _, method_name, _, body = method

        # body = ('body', decls, stmts) -> κρατάμε μόνο τα statements
        _, _, stmts = body

        # declared_names: όλα τα ΟΝΟΜΑΤΑ που είναι ορατά μέσα στη μέθοδο (params + locals)
        declared_names = {entry['name'] for entry in symbol_table.get(method_name, [])}

        # Ελέγχουμε κάθε statement της μεθόδου για αδήλωτες μεταβλητές/κλήσεις.
        for stmt in stmts:
            check_stmt(stmt, declared_names, method_name, declared_funcs, stream)


def check_stmt(stmt, declared_names, method_name, declared_funcs, stream=None):
    """
    Ελέγχει ένα μονο statement:
    - αδήλωτες μεταβλητές που χρησιμοποιούνται
    - αδήλωτη αριστερή πλευρά ανάθεσης
    - εκφράσεις/κλήσεις μέσα στο statement
    """
    if not stmt:
        return  # Αν είναι κενό, δεν έχει κάτι να ελέγξει

    tag = stmt[0]

    # --- Ανάθεση τιμής σε μεταβλητή: ('assign_stmt', ('assign', var_name, expr))
    if tag == 'assign_stmt':
        assign = stmt[1]            # ('assign', 'x', expr)
        var_name = assign[1]        # όνομα μεταβλητής αριστερά
        expr = assign[2]            # έκφραση δεξιά

        # Έλεγχος δεξιάς πλευράς (μπορεί να περιέχει identifiers / κλήσεις συναρτήσεων)
        check_expr(expr, declared_names, method_name, declared_funcs, stream)

        # Έλεγχος ότι η αριστερή μεταβλητή έχει δηλωθεί (params/locals της μεθόδου)
        if var_name not in declared_names and stream:
            print(f"Semantic Error: Undeclared variable '{var_name}' in method '{method_name}'", file=stream)

    # --- Επιστροφή τιμής: ('return_stmt', expr)
    elif tag == 'return_stmt':
        expr = stmt[1]
        # Ελέγχουμε την έκφραση επιστροφής για αδήλωτες αναφορές
        check_expr(expr, declared_names, method_name, declared_funcs, stream)

    # --- If/While: έλεγχος συνθήκης και (μόνο) block-σωμάτων για undeclared 
    elif tag in ['if_stmt', 'while_stmt']:
        cond = stmt[1]  # η boolean συνθήκη
        # Ελέγχουμε τη συνθήκη (μπορεί να έχει identifiers/κλήσεις)
        check_expr(cond, declared_names, method_name, declared_funcs, stream)

        # Σημείωση: Εδώ κατεβαίνουμε στα σώματα ΜΟΝΟ αν είναι block ('block', stmts_list).
        for part in stmt[2:]:
            if isinstance(part, tuple) and part[0] == 'block':
                # part = ('block', [stmts...]) -> ελέγχουμε αναδρομικά τα stmts του block
                traverse_statements(part[1], method_name, inside_while=1, stream=stream)


def check_expr(expr, declared_names, method_name, declared_funcs=None, stream=None):
    """
    Ελέγχει αναδρομικά μια ΕΚΦΡΑΣΗ:
    - αναφορές σε αδήλωτες μεταβλητές (σκέτα identifiers)
    - κλήσεις συναρτήσεων: undefined function ή λάθος πλήθος ορισμάτων
    - υποεκφράσεις (add/mulop/relop/call args)
    """
    # Καμία έκφραση -> κανένας έλεγχος
    if expr is None:
        return

    # Περίπτωση: σκέτο string (π.χ. 'x') -> πιθανό identifier
    if isinstance(expr, str):
        # Αν ΔΕΝ είναι αριθμητικό string και ΔΕΝ ανήκει στα δηλωμένα ονόματα, τότε είναι αδήλωτο
        if not expr.isdigit() and expr not in declared_names and stream:
            # Αν η έκφραση είναι ένα απλό όνομα (string) — και δεν είναι αριθμός ή δηλωμένη μεταβλητή — είναι λάθος.
            print(f"Semantic Error: Undeclared variable '{expr}' in method '{method_name}'", file=stream)

    # Περίπτωση: tuple -> σύνθετος κόμβος AST (π.χ. call, add, mulop, relop, bool...)
    elif isinstance(expr, tuple):
        tag = expr[0]

        # Κλήση συνάρτησης: ('call', fname, args_list)
        if tag == 'call':
            fname = expr[1]
            args = expr[2]

            # Προστασία: αν δεν δόθηκε λεξικό δηλωμένων συναρτήσεων
            if declared_funcs is None:
                declared_funcs = {}

            # Σφάλμα: κλήση σε αδήλωτη συνάρτηση (δεν υπάρχει στο global)
            if fname not in declared_funcs:
                if stream:
                    print(f"Semantic Error: Call to undefined function '{fname}' in method '{method_name}'", file=stream)
            else:
                # Έλεγχος arity: πλήθος actual args vs πλήθος δηλωμένων params
                expected_params = declared_funcs[fname]['params']
                if len(args) != len(expected_params) and stream:
                    print(
                        f"Semantic Error: Function '{fname}' called with {len(args)} arguments, "
                        f"expected {len(expected_params)}",
                        file=stream
                    )

            # Ελέγχουμε ΚΑΘΕ όρισμα αναδρομικά (μπορεί να έχει identifiers/κλήσεις)
            for arg in args:
                check_expr(arg, declared_names, method_name, declared_funcs, stream)

        else:
            # Άλλοι κόμβοι εκφράσεων (π.χ. ('add','+', L, R), ('mulop','*', L, R), ('relop','==', L, R), ('bool', 0/1))
            # Γενικός κανόνας: αγνοούμε τα πρώτα 1-2 slots (tag, πιθανός operator) και ελέγχουμε τις υποεκφράσεις.
            for subexpr in expr[2:]:
                check_expr(subexpr, declared_names, method_name, declared_funcs, stream)


def check_main_exists(symbol_table, stream=None):
    """
    Ελέγχει ότι υπάρχει main() δηλωμένη ως function στο global scope.
    Αν λείπει, εκτυπώνει semantic error.
    """
    # Σαρώνουμε το global scope και ψάχνουμε entry με name='main' και kind='function'
    found_main = any(
        entry['name'] == 'main' and entry['kind'] == 'function'
        for entry in symbol_table.get('global', [])
    )
    if not found_main and stream:
        print("Semantic Error: No 'main' function defined", file=stream)


def check_break_outside_while(ast, symbol_table, stream=None):
    """
    Ελέγχει ότι κάθε 'break;' βρίσκεται μέσα σε while.
    - Διασχίζει τα statements κάθε μεθόδου και κρατά μετρητή 'inside_while'.
    - Αν βρεθεί break με inside_while == 0 -> σφάλμα.
    """
    # Αν δεν υπάρχει έγκυρο AST ή δεν ξεκινά από 'program', δεν κάνουμε έλεγχο.
    if not ast or ast[0] != 'program':  # ελέγχει αν υπάρχει break εκτός while
        return

    methods = ast[1]

    for method in methods:
        if method[0] != 'method':
            continue

        # Πάρε όνομα μεθόδου και statements
        _, _, method_name, _, body = method
        _, _, stmts = body

        # Ξεκίνα traversal με inside_while=0 (δηλ. εκτός while)
        traverse_statements(stmts, method_name, inside_while=0, stream=stream)


def traverse_statements(stmts, method_name, inside_while, stream=None):
    """
    Διασχίζει λίστα statements για:
    - nested while (αυξομείωση inside_while)
    - εύρεση break εκτός while
    - κατέβασμα μέσα σε blocks
    Σημ.: Δεν κάνει έλεγχο undeclared μόνο του· απλώς εντοπίζει 'break' σε λάθος θέση.
    """
    for stmt in stmts:
        if not stmt:
            continue

        tag = stmt[0]

        # while_stmt: αυξάνουμε το επίπεδο nesting κατά 1 και κατεβαίνουμε στο σώμα
        if tag == 'while_stmt':
            # ('while_stmt', cond, body_stmt_or_block)
            _, _, inner_stmt = stmt
            # Κατεβαίνουμε με inside_while + 1 ώστε τα break μέσα να θεωρούνται έγκυρα
            traverse_statements([inner_stmt], method_name, inside_while + 1, stream)

        # block: κατεβαίνουμε στα περιεχόμενα χωρίς να αλλάξουμε inside_while
        elif tag == 'block':
            # ('block', [stmts...])
            block_stmts = stmt[1]
            traverse_statements(block_stmts, method_name, inside_while, stream)

        # break_stmt: αν ΔΕΝ είμαστε μέσα σε while (inside_while == 0), είναι σφάλμα
        elif tag == 'break_stmt':
            if inside_while == 0 and stream:
                print(f"Semantic Error: 'break' outside of while in method '{method_name}'", file=stream)

        # Άλλα είδη statements: αν περιέχουν block-παιδιά, κατεβαίνουμε σε αυτά
        elif tag in ['assign_stmt', 'return_stmt', 'if_stmt']:
            # Προσοχή: εδώ κατεβαίνουμε μόνο αν βρούμε block-παιδί. Αν το then/else
            # είναι single-statement (μη-block), δεν κατεβαίνουμε σήμερα.
            for part in stmt[1:]:
                if isinstance(part, tuple) and part[0] == 'block':
                    # Εδώ part είναι ('block', [...])
                    traverse_statements([part], method_name, inside_while, stream)


def check_duplicate_declarations(symbol_table, stream=None):
    """
    Ελέγχει διπλές δηλώσεις ΟΝΟΜΑΤΩΝ μέσα στην ΙΔΙΑ μέθοδο (locals/params).
    Αν βρεθεί το ίδιο όνομα δύο φορές στο ίδιο method scope -> σφάλμα.
    """
    # Σαρώνουμε όλα τα scopes εκτός από το global (εκεί κρατάμε μόνο συναρτήσεις)
    for method_name, entries in symbol_table.items():
        if method_name == "global":
            continue

        seen = set()  # αποθήκευση των ονομάτων που έχουμε ήδη δει στη μέθοδο
        for entry in entries:
            var_name = entry['name']
            if var_name in seen:
                print(
                    f"Semantic Error: Duplicate declaration of '{var_name}' in method '{method_name}'",
                    file=stream
                )
            else:
                seen.add(var_name)


def check_duplicate_functions(symbol_table, stream=None):
    """
    Ελέγχει διπλές δηλώσεις ΣΥΝΑΡΤΗΣΕΩΝ στο global scope (δεν επιτρέπεται overloading).
    Αν εμφανιστεί δεύτερη φορά το ίδιο όνομα συνάρτησης -> σφάλμα.
    """
    seen = set()  # ονόματα συναρτήσεων που έχουμε ήδη δει
    for entry in symbol_table.get('global', []):
        func_name = entry['name']
        if func_name in seen:
            print(f"Semantic Error: Duplicate function '{func_name}'", file=stream)
        else:
            seen.add(func_name)

# --- NEW: Division-by-zero semantic check ------------------------------------

def check_division_by_zero(ast, stream=None):
    """
    Εντοπίζει περιπτώσεις DIV με διαιρέτη '0' 
    """
    if not ast or ast[0] != 'program':
        return

    methods = ast[1]
    for method in methods:
        if not method or method[0] != 'method':
            continue

        _, _, method_name, _, body = method
        _, decls, stmts = body

        # 1) Έλεγχος σε αρχικοποιήσεις δηλώσεων
        for d in decls:
            if not d or d[0] != 'decl':
                continue
            # d = ('decl', type, [(name, expr_or_None), ...])
            for (_, init_expr) in d[2]:
                _scan_expr_for_div_zero(init_expr, method_name, stream)

        # 2) Έλεγχος σε όλα τα statements
        _scan_stmts_for_div_zero(stmts, method_name, stream)


# ----------------- Helpers (internal) -----------------

def _is_zero_literal(expr) -> bool:
    if expr == 0:
        return True
    if isinstance(expr, tuple) and expr and expr[0] == 'bool':
        try:
            return int(expr[1]) == 0
        except Exception:
            return False
    return False


def _scan_expr_for_div_zero(expr, method_name: str, stream=None):
    if expr is None:
        return

    if isinstance(expr, int) or isinstance(expr, str):
        return

    if isinstance(expr, tuple) and expr:
        tag = expr[0]

        if tag == 'mulop':
            # ('mulop', op, L, R)
            _, op, L, R = expr
            if op == '/':
                if _is_zero_literal(R) and stream:
                    print(f"Semantic Error: Division by zero in method '{method_name}'", file=stream)
            # Συνέχισε να σαρώνεις και τα δύο σκέλη για nested /0
            _scan_expr_for_div_zero(L, method_name, stream)
            _scan_expr_for_div_zero(R, method_name, stream)
            return

        if tag == 'add':
            # ('add', '+|-', L, R)
            _, _, L, R = expr
            _scan_expr_for_div_zero(L, method_name, stream)
            _scan_expr_for_div_zero(R, method_name, stream)
            return

        if tag == 'relop':
            # ('relop', op, L, R)
            _, _, L, R = expr
            _scan_expr_for_div_zero(L, method_name, stream)
            _scan_expr_for_div_zero(R, method_name, stream)
            return

        if tag == 'call':
            # ('call', fname, [arg1, arg2, ...])
            _, _, actuals = expr
            for a in actuals:
                _scan_expr_for_div_zero(a, method_name, stream)
            return

        # Οποιοδήποτε άλλο tuple που ίσως προστεθεί μελλοντικά:
        # σάρωσε όλα τα υπο-μέρη που είναι εκφράσεις (συνήθως από το index 1+)
        for part in expr[1:]:
            _scan_expr_for_div_zero(part, method_name, stream)


def _scan_stmts_for_div_zero(stmts, method_name: str, stream=None):
    if not stmts:
        return

    for s in stmts:
        if not s:
            continue
        tag = s[0]

        if tag == 'assign_stmt':
            # ('assign_stmt', ('assign', id, expr))
            _, assign = s
            _, _, e = assign
            _scan_expr_for_div_zero(e, method_name, stream)

        elif tag == 'return_stmt':
            # ('return_stmt', expr)
            _, e = s
            _scan_expr_for_div_zero(e, method_name, stream)

        elif tag == 'if_stmt':
            # ('if_stmt', cond, then_stmt, else_stmt_or_empty)
            _, cond, then_s, else_s = s
            _scan_expr_for_div_zero(cond, method_name, stream)
            _scan_stmt_or_block_for_div_zero(then_s, method_name, stream)
            if else_s and else_s[0] != 'empty_stmt':
                _scan_stmt_or_block_for_div_zero(else_s, method_name, stream)

        elif tag == 'while_stmt':
            # ('while_stmt', cond, body_stmt)
            _, cond, body_s = s
            _scan_expr_for_div_zero(cond, method_name, stream)
            _scan_stmt_or_block_for_div_zero(body_s, method_name, stream)

        elif tag == 'block':
            # ('block', [stmts...])
            _, inner = s
            _scan_stmts_for_div_zero(inner, method_name, stream)

        # 'break_stmt' / 'empty_stmt' δεν περιέχουν εκφράσεις, οπότε skip


def _scan_stmt_or_block_for_div_zero(node, method_name: str, stream=None):
    if not node:
        return
    if node[0] == 'block':
        _scan_stmts_for_div_zero(node[1], method_name, stream)
    else:
        _scan_stmts_for_div_zero([node], method_name, stream)