from typing import Any, Dict, List, Tuple, Optional
import hashlib

class MixalGenerator:
    def __init__(self, symbol_table: Optional[Dict]=None, entry: str="main"):
        self.symbol_table = symbol_table or {} #Φορτώση πίνακα συμβόλων. Αν δεν δοθεί, βάλε κενό dict.
        self.entry = entry #σημείο εκκίνησης προγραμματος
        self.code: List[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]] = [] #λίστα με tuples με (label, opcode, operand, comment) είτε sting είτε None
        self.data: List[Tuple[str, str, str, str]] = [] # λίστα με Tuple με (label, opcode, value, comment) 

        # pools & maps
        self.const_pool: Dict[int, str] = {}        # const -> μοναδικό label στη data (π.χ. 5 -> K0001) για καθε νουμερο που εμφανιζεται
        self.var_addr: Dict[str, str] = {}          # fully-qualified όνομα var (π.χ. "main_x" και add2_x) -> μοναδικό label στη data για να ξεχωριζω 
        self.func_label: Dict[str, str] = {}        # όνομα συνάρτησης -> μοναδικό label εισόδου (για κλήση με JMP) π.χ "main" -> "MAIN"
        self.ret_label: Dict[str, str] = {}         # όνομα συνάρτησης -> μοναδικό label επιστροφής (STJ ... / JMP 0)

        self.labels = 0 #μετρητής label για να αυξανω value 
        self.current_method: Optional[str] = None # ποια μεθδοδο παραγω τωρα χρειαζεται για να ξερω σε ποιο scope γραφω
        self.loop_end_stack: List[str] = []   # Στοίβα με labels "τέλους while" ώστε το 'break' να κάνει JMP στο σωστό τέλος, σε εμφωλευμένα loops (push στο enter, pop στο exit του while).

        # κραταω τα labels που εχουν ψρησιμοποιηθει και επισης μηκος <=10 και αν χρειαστει χρησιμοποιω τη uniquify να προσθετει suffix αν βρει δεσμευμενη λεξη
        self.used_labels: set[str] = set()

        #Ωστε να μην χρησιμοποιηθουν αυτες οι δευσμενευμενς λεξεις για labels(χρησιμοποιειται στη μεθοδο _uniquify)
        self.RESERVED = {
            "ADD","SUB","MUL","DIV","LDA","STA","LDX","STX","STJ","TXA","TAX",
            "CMPA","CMPX","JE","JNE","JL","JG","JLE","JGE","JMP","JSJ","HLT","NOP",
            "ORIG","CON","END"
        }

    # --------------- label helpers ---------------
    '''
    Καθορίζει ένα προτεινόμενο όνομα Label οπου θα ειναι ολα κεφαλαια(ρίχνει οτι δεν εινια γραμμα ή ψηφιο)
    Αν ξεκιναει με ψηφιο πρόσθεσε μπροστα το γραμμα L.
    Δεν εγκυαται μοναδικοτητα (αυτο γινεται στη _uniquify)
    '''
    def _sanitize_label(self, s: str) -> str:
        s = "".join(ch for ch in str(s).upper() if ch.isalnum())
        if not s or s[0].isdigit():
            s = "L" + s
        return s

    def _uniquify(self, base: str) -> str:
        """
        Κάνει το label μοναδικό, με όριο 10 χαρακτήρων του MIXAL.
        Αν υπάρχει σύγκρουση (ή RESERVED), προσθέτει μικρό hex suffix ('1', '2', ..., 'A', ...) κρατοντας το <=10.
        """
        base = self._sanitize_label(base)
        base = base[:10]  # αρχικό κόψιμο πρωρα 10 chars

        cand = base
        i = 1
        while cand in self.used_labels or cand in self.RESERVED or not cand:
            # Μικρό hex suffix 
            suf = f"{i:X}"[-2:]  # 1–2 hex chars
            keep = max(1, 10 - len(suf))
            cand = (base[:keep] + suf)[:10]
            i += 1
        self.used_labels.add(cand)
        return cand

    def _get_func_label(self, name: str) -> str:
        '''
        Για καθε ονομα συναρτησης παράγει μοναδικό label εισόδου για τη συνρτηση name.
        Αν δεν υπάρχει στο self.func_label, το δημιουργεί με _uniquify(name)
        '''
        if name not in self.func_label:
            self.func_label[name] = self._uniquify(name)
        return self.func_label[name]

    def _get_ret_label(self, func_name: str) -> str:
        '''
        Επιστρέφει το μοναδικό label επιστροφής της συνάρτησης 'func_name'.
        Χρήση στον prologue: STJ RET_F(0:2) (αποθήκευση διεύθυνσης επιστροφής).
        Χρήση στο return: JMP RET_F (self-modifying jump).
        Έτσι υλοποιείται ο μηχανισμός κλήσης/επιστροφής σε MIXAL χωρίς εγγενή call/ret.
        '''
        if func_name not in self.ret_label:
            self.ret_label[func_name] = self._uniquify(f"RET_{func_name}")
        return self.ret_label[func_name]

    # ---------------- low-level emit ----------------
    def _new_label(self, prefix="L"):
        '''
        Δημιουργεί νέο μοναδικό label με μετρητή.
        prefix: προθεματικό (π.χ. 'L', 'IF', 'ELSE', 'WH' κ.λπ.)
        self.labels: αυξάνεται για κάθε νέο label (L0001, L0002, ...)
        _uniquify: διασφαλίζει τους κανόνες MIXAL (<=10 chars, όχι reserved, όχι διπλό)
        '''
        self.labels += 1
        return self._uniquify(f"{prefix}{self.labels:04d}")

    def _emit(self, lab, op, operand="", comment=""):
        '''
        Προσθετει μια γραμμη στον πινακα self.code
        lab: label (ή None). Αν δοθεί, ΠΡΕΠΕΙ ήδη να είναι μοναδικό.
        Αποθηκεύει την τετράδα (lab, op, operand, comment) στον ενδιάμεσο buffer self.code
        χωρίς να κάνει formatting(γινεται στο render).
        '''
        self.code.append((lab, op or "", operand or "", comment or ""))

    def _label(self, lab):
        # Ποτέ «γυμνό» label: βάλε NOP ώστε να υπάρχει operator
        # lab εδώ θεωρείται ΗΔΗ μοναδικό (φροντίδα από _uniquify / δημιουργούς του lab)
        self._emit(lab, "NOP", "", "label")

    def _render(self):
        #Μετατρέπει το self.code σε τελικό MIXAL κείμενο με στοίχιση στηλών.
        lines = []
        for lab, op, operand, cmt in self.code:
            labf  = f"{lab:10s}" if lab else " " * 10   
            opf   = f"{op:8s}"   if op else " " * 8
            operf = f"{operand:18s}" if operand else " " * 18
            lines.append(f"{labf} {opf}{operf}")
        return "\n".join(lines)

    # ---------------- symbols / data ----------------
    def _fq(self, varname: str) -> str:
        '''
        Επιστρέφει fully-qualified όνομα μεταβλητής στο τρέχον scope/μέθοδο.
        Π.χ. αν self.current_method == 'main' και varname == 'x' => 'main_x'.
        Χρησιμοποιείται για να αποφύγουμε συγκρούσεις ονομάτων μεταξύ μεθόδων.
        '''
        return f"{self.current_method}_{varname}"

    def _reserve_var(self, fq_name: str):
        # Δημιουργεί/επιστρέφει ΜΟΝΑΔΙΚΟ label για δεδομένη fully-qualified μεταβλητή στο data section
        # Αν υπαρχει ηδη , επιστρεφει το υπαρχον label
        if fq_name not in self.var_addr:
            lab = self._uniquify(fq_name)
            self.var_addr[fq_name] = lab
            self.data.append((lab, "CON", "0", ""))  # 1 λέξη/μεταβλητή
        return self.var_addr[fq_name]

    def _reserve_var_for(self, varname: str):
        '''
        Παίρνει απλό όνομα (στο τρέχον scope) και το κάνει fully-qualified μέσω _fq.
        Έπειτα καλεί _reserve_var gia τη δέσμευση μνήμης/label.
        '''
        return self._reserve_var(self._fq(varname))

    def _const(self, value: int) -> str:
        '''
        Για κάθε ακέραιο ν δημιουργησε μια φορα ενα label (K0001,K0002)
        και αποθηκευουμε στο data section
        Δε φτιαχνουμε duplicates για ιδιους αεραιους
        '''
        v = int(value)
        if v not in self.const_pool:
            lab = self._uniquify(f"K{len(self.const_pool)+1:04d}")
            self.const_pool[v] = lab
            self.data.append((lab, "CON", str(v), ""))
        return self.const_pool[v]

    def _ensure_in_mem(self, expr) -> str:
        # Επέστρεψε label μνήμης που περιέχει την τιμή του expr
        if isinstance(expr, int):                       #int-> επιστρέφει label της σταθεράς (μέσω _const).
            return self._const(expr)
        if isinstance(expr, str):                       #str (ID)-> επιστρέφει label μεταβλητής τρέχοντος scope (μέσω _reserve_var_for).
            # αναγνώστης αναγνωριστικού: τρέχουσα μέθοδος
            return self._reserve_var_for(expr)         
        if isinstance(expr, tuple) and expr and expr[0] == 'bool':  #('bool', v)-> όπως οι σταθερές: _const(0 ή 1).
            return self._const(int(expr[1]))
        # Αλλιώς: υπολόγισε στο A και κάνε spill σε προσωρινή
        tmp = self._reserve_var(self._fq(f"TMP{self.labels+1}"))  # προσωρινό label, μοναδικό
        self._expr_into_A(expr)                                   # A <- value(expr)
        self._emit(None, "STA", tmp, "spill")                     # [tmp] <- A
        return tmp

    def _label_for(self, method: str, varname: str) -> str:
        # Επέστρεψε το ΠΡΑΓΜΑΤΙΚΟ (unique) label για var/param άλλης μεθόδου
        fq = f"{method}_{varname}"
        return self._reserve_var(fq)

    # ---------------- public ----------------
    def gen_program(self, ast_program) -> str:
        # Header (κομματι του code)
        self._emit(None, "ORIG", "2000", "code")  # Θέτουμε την αρχική διεύθυνση του ΚΩΔΙΚΑ. Συμβατικά 2000 (θα μπορούσε να είναι άλλη),
        self._label(self._uniquify("START"))      # Δημιουργούμε ένα σταθερό entry anchor.
        self._emit(None, "JMP", self._get_func_label(self.entry), "jump to entry")   #Jump στην είσοδο της συνάρτησης entry ('main').

        # Methods
        methods = ast_program[1] if (ast_program and ast_program[0] == 'program') else [] # Παίρνουμε από το AST τη λίστα μεθόδων: ('program', [method, method, ...])
        for m in methods:
            if m and m[0] == 'method':
                self._gen_method(m)

        # Exit
        self._label(self._uniquify("EXIT")) # Σημείο τερματισμού προγράμματος
        self._emit(None, "HLT", "", "program end")

        # Data section Κομματι του data
        self._emit(None, "ORIG", "3000", "data")  # Μεταφέρουμε τον assembler pointer στο χώρο data (3000).
        self.code.extend(self.data)

        # Footer
        self._emit(None, "END", list(self.used_labels)[0] if "START" not in self.used_labels else "START", "") # Η END ζητά label εκκίνησης για τον assembler (entry point).
        return self._render() # Τελικό render σε string για στοίχιση στηλών.

    # ---------------- method / body ----------------
    def _gen_method(self, m):
        # ('method', type, name, params, body)
        _, ret_type, name, params, body = m  # m είναι AST node μορφής: ('method', return_type, name, params, body)
        self.current_method = name           # Κρατάμε ποια μέθοδο παράγουμε τώρα (χρήσιμο για fully-qualified labels π.χ. main_x)

        funclab = self._get_func_label(name)# Πάρε/φτιάξε ΜΟΝΑΔΙΚΟ label για τη συνάρτηση και "πιάσ’ το" με ένα NOP
        self._label(funclab)                # ώστε ο loader/άλλες JMP να μπορούν να έρθουν εδώ.
       


        # --- prologue: αποθήκευση διεύθυνσης επιστροφής στο RET label ---
        # prologue: STJ RET(0:2) → γράφει μόνο τη διεύθυνση της εντολής "JMP 0" στο RET_<name>,
        # ώστε αργότερα το "JMP RET_<name>" να επιστρέψει στον καλούντα (self-modifying jump).
        ret_lbl = self._get_ret_label(name)
        self._emit(None, "STJ", f"{ret_lbl}(0:2)", "save return addr into RET")

        # Δεσμευσε αποθηκευτικό χώρος(data section) για όλες τις τοπικές & παραμέτρους της μεθόδου και αποκτηση μοναδικου label.
        # Αυτό δημιουργεί μοναδικά labels (π.χ. MAIN_X) και μία λέξη μνήμης για καθεμία.
        #πριν απο stmt γιατι θα χρησιμοποιηθουν
        for entry in self.symbol_table.get(name, []):
            if entry['kind'] in ('var', 'param'):
                self._reserve_var_for(entry['name'])

        # Αρχικοποιήσεις από decls στο body = ('body', decls, stmts) (int a=5, b; κ.λπ.)
        decls = body[1]
        self._gen_decl_inits(decls)

        # Statements
        stmts = body[2]
        for s in stmts:
            self._gen_stmt(s)

        # --- Επιστροφή: σημείο με την "JMP 0" που έχει ήδη τροποποιηθεί από το STJ ---
        # Όταν γίνει "JMP RET_<name>" (σε return μη-main), θα εκτελεστεί αυτή η εντολή,
        # της οποίας η διεύθυνση έχει γραφτεί στο prologue, άρα θα γυρίσουμε στον καλούντα.-
        self._emit(ret_lbl, "JMP", "0", "return to caller (address was STJ-ed)")

    def _gen_decl_inits(self, decls):
        # decl = ('decl', type, [(name, expr_or_None), ...])
        for d in decls:
            if not d or d[0] != 'decl':
                continue
            var_list = d[2]
            for (vname, expr) in var_list:
                # 1) Δέσμευση μνήμης & label για τη μεταβλητή (αν δεν υπάρχει ήδη -> CON 0 στο data)
                self._reserve_var_for(vname)
                 # 2) Αν υπάρχει αρχικοποιητής, υπολόγισέ τον και γράψε την τιμή στη μεταβλητή
                if expr is not None:
                     # Υπολόγισε την έκφραση: το αποτέλεσμα θα βρίσκεται στον A
                    self._expr_into_A(expr) 
                    # Αποθήκευσε την τιμή του A στη διεύθυνση της μεταβλητής
                    # (ξανακαλούμε reserve για να πάρουμε σίγουρα το σωστό label)
                    self._emit(None, "STA", self._reserve_var_for(vname), f"init {vname}") 

    # ---------------- statements ----------------
    def _gen_stmt(self, s):
        if not s:
            return
        tag = s[0]

        # ---------------- assignment: x = expr;
        if tag == 'assign_stmt':
            _, assign = s                         # ('assign_stmt', ('assign', varname, expr))
            _, varname, expr = assign
            self._expr_into_A(expr)               # Υπολόγισε τη δεξιά πλευρά -> αποτέλεσμα στο A
            self._emit(None, "STA",
                    self._reserve_var_for(varname),
                    f"{varname} = expr")       # Αποθήκευσε A στη μνήμη της varname (label της)

        # ---------------- return [expr];
        elif tag == 'return_stmt':
            _, expr = s
            if expr is not None:
                self._expr_into_A(expr)           # Η τιμή επιστροφής στο A (συμβατικά)
            # Αν είναι η entry (main): πήδα στο EXIT (κάνει HLT).
            # Αλλιώς: πήδα στο RET_<func> (self-modifying jump “επιστροφή στον καλούντα”).
            if (self.current_method or "").lower() == (self.entry or "").lower():
                self._emit(None, "JMP", "EXIT")   # Τερματισμός προγράμματος
            else:
                self._emit(None, "JMP",
                        self._get_ret_label(self.current_method))  # Επιστροφή στον καλούντα

        # ---------------- if (cond) then_stmt else else_stmt;
        elif tag == 'if_stmt':
            _, cond, then_stmt, else_stmt = s
            L_else = self._new_label("ELSE")      # Πού θα πάμε αν cond == false
            L_end  = self._new_label("ENDIF")     # Τέλος if-else

            self._cond_jump_false(cond, L_else)   # Αν cond ψευδής -> πήδα στο ELSE
            self._gen_stmt_or_block(then_stmt)    # then-κλάδος
            self._emit(None, "JMP", L_end)        # Παράκαμψε το else
            self._label(L_else)                   # ELSE:
            if else_stmt and else_stmt[0] != 'empty_stmt':
                self._gen_stmt_or_block(else_stmt)
            self._label(L_end)                    # ENDIF:

        # ---------------- while (cond) body;
        elif tag == 'while_stmt':
            _, cond, body_stmt = s
            L_top = self._new_label("WH")         # Αρχή βρόχου
            L_end = self._new_label("WEND")       # Έξοδος βρόχου

            self._label(L_top)                    # WH:
            self._cond_jump_false(cond, L_end)    # Αν cond ψευδής -> έξοδος
            self.loop_end_stack.append(L_end)     # Για υποστήριξη break (nested-safe)
            self._gen_stmt_or_block(body_stmt)    # Σώμα
            self.loop_end_stack.pop()
            self._emit(None, "JMP", L_top)        # Επανάληψη
            self._label(L_end)                    # WEND:

        # ---------------- break;
        elif tag == 'break_stmt':
            if self.loop_end_stack:
                self._emit(None, "JMP", self.loop_end_stack[-1], "break")  # Πήδα στο WEND του τρέχοντος loop
            else:
                # Δεν θα έρθει ποτέ εδώ αν τα semantics τερματίζουν σε 'break' εκτός loop,
                # αλλά κρατάμε ασφαλές NOP για να μη σπάσει ο κώδικας.
                self._emit(None, "NOP", "", "break outside loop (caught by semantics)")

        # ---------------- { ... }  (block)
        elif tag == 'block':
            self._gen_block(s)                    # Παράγει τα εσωτερικά statements σειριακά

        # ---------------- ;  (κενή εντολή)
        elif tag == 'empty_stmt':
            self._emit(None, "NOP", "", "empty")  # Καμία ενέργεια

        # ---------------- μελλοντικές επεκτάσεις
        else:
            self._emit(None, "NOP", "", f"TODO stmt {tag}")  # Placeholder για μη υλοποιημένα


    def _gen_stmt_or_block(self, node):
        # Helper: δέχεται είτε ΜΟΝΟ statement είτε BLOCK ('block', [stmts...])
        if not node:
            return
        if node[0] == 'block':
            # Αν είναι block, παράγαγε όλα τα εσωτερικά statements με τη σειρά
            self._gen_block(node)
        else:
            # Αλλιώς, είναι απλό statement: παράγαγε κώδικα γι’ αυτό το ένα
            self._gen_stmt(node)

    def _gen_block(self, block_node):
        # block_node: ('block', [stmt1, stmt2, ...])
        # Δεν ανοίγει νέο scope (οι δηλώσεις γίνονται στην αρχή της μεθόδου στη γλώσσα σου)
        for s in block_node[1]:
            # Σειριακά codegen για κάθε statement του block
            self._gen_stmt(s)


    # ---------------- conditions ----------------
    def _cond_jump_false(self, cond, target_label: str):
        """
        Σκοπός: Για χρήση σε έλεγχο ροής (if/while).
        Αν η cond είναι ΨΕΥΔΗΣ, κάνε JMP στο target_label.
        """
        # Περίπτωση 1: Ρητή σύγκριση (relop): ('relop', op, left, right)
        if isinstance(cond, tuple) and cond and cond[0] == 'relop':
            _, op, left, right = cond

            # Βάλε το right σε μνήμη (αν είναι άμεσος αριθμός/έκφραση) και πάρε τη διεύθυνση
            addrR = self._ensure_in_mem(right)

            # Φόρτωσε το left στο A και σύγκρινε A ? right
            self._expr_into_A(left)
            self._emit(None, "CMPA", addrR, f"compare {op}")

            # Επιλογή JUMP όταν η συνθήκη ΔΕΝ ισχύει (false-branch)
            jfalse = {
                '==': "JNE",   # όχι ίσα  -> false
                '!=': "JE",    # ίσα      -> false
                '<':  "JGE",   # A >= R   -> false
                '<=': "JG",    # A >  R   -> false
                '>':  "JLE",   # A <= R   -> false
                '>=': "JL",    # A <  R   -> false
            }[op]

            # Αν είναι false, πηδάμε στο target
            self._emit(None, jfalse, target_label)

        else:
            # Περίπτωση 2: Αυθαίρετη έκφραση: θεωρούμε 0=false, μη-0=true
            self._expr_into_A(cond)                # A = cond
            z = self._const(0)
            self._emit(None, "CMPA", z, "cond != 0 ?")
            self._emit(None, "JE", target_label)   # A == 0 -> false -> πήδα

    def _relop_into_boolA(self, op, left, right):
        """
        Σκοπός: Υπολόγισε (left op right) ως τιμη και βάλε 0/1 στο A.
        Χρήσιμο όταν το αποτέλεσμα της σύγκρισης χρησιμοποιείται σε έκφραση (π.χ. x = (a<b);)
        """
        # Προετοιμασία συγκρίσεως A ? right
        addrR = self._ensure_in_mem(right)
        self._expr_into_A(left)
        self._emit(None, "CMPA", addrR, f"relop {op}")

        # Labels για κλασικό pattern: if true -> A=1 else A=0
        L_true = self._new_label("T")
        L_end  = self._new_label("E")

        # Επιλογή JUMP όταν η συνθήκη είναι ΑΛΗΘΗΣ (true-branch)
        jtrue = {
            '==': "JE",
            '!=': "JNE",
            '<':  "JL",
            '<=': "JLE",
            '>':  "JG",
            '>=': "JGE",
        }[op]

        # Αν είναι true -> πήδα στο L_true
        self._emit(None, jtrue, L_true)

        # false-path: A = 0
        self._emit(None, "LDA", self._const(0), "false -> 0")
        self._emit(None, "JMP", L_end)

        # true-path: A = 1
        self._label(L_true)
        self._emit(None, "LDA", self._const(1), "true -> 1")

        # τέλος (συγκεντρώνει τα δύο μονοπάτια)
        self._label(L_end)

    # ---------------- expressions ----------------
    def _expr_into_A(self, e, want_wide: bool = False) -> bool:
        # Στόχος: Υπολόγισε την έκφραση e και βάλε το αποτέλεσμα στο A.
        # Επιστρέφει True αν το αποτέλεσμα είναι "wide" (χρησιμοποιεί A:X), αλλιώς False.

        if e is None:
            self._emit(None, "LDA", self._const(0), "nil->0")
            return False

        if isinstance(e, int):
            # Ακέραια σταθερά: φόρτωσε από constant pool (label K0001 κ.λπ.)
            self._emit(None, "LDA", self._const(e), f"A={e}")
            return False

        if isinstance(e, str):
            # Αναγνωριστικό: φόρτωσε τη μεταβλητή/παράμετρο της τρέχουσας μεθόδου
            self._emit(None, "LDA", self._reserve_var_for(e), f"A={e}")
            return False

        if isinstance(e, tuple) and e:
            tag = e[0]

            if tag == 'bool':
                # Boolean literal: φόρτωσε 0/1
                self._emit(None, "LDA", self._const(int(e[1])), "A=bool")
                return False

            if tag == 'add':
                # Πρόσθεση/Αφαίρεση: A = L (+|-) R
                _, op, L, R = e
                addrR = self._ensure_in_mem(R)    # εξασφάλισε ότι το R έχει διεύθυνση μνήμης
                self._expr_into_A(L)              # A = L
                if op == '+':
                    self._emit(None, "ADD", addrR, "A=L+R")
                else:
                    self._emit(None, "SUB", addrR, "A=L-R")
                return False                      # αποτέλεσμα στο A (όχι wide)

            if tag == 'mulop':
                _, op, L, R = e
                addrR = self._ensure_in_mem(R)    # R πρέπει να είναι σε μνήμη

                if op == '*':
                    # Πολλαπλασιασμός: A:X = L * R
                    self._expr_into_A(L, want_wide=True)     # ετοίμασε L "wide"
                    self._emit(None, "MUL", addrR, "A:X = L * R")
                    if want_wide:
                        # Ο καλών ζήτησε wide -> κράτα A:X ως έχει
                        return True
                    else:
                        # "Συμπύκνωσε": πάρε το low μέρος από X και βάλε το στο A
                        tmpx = self._reserve_var(self._fq("TMPX")) #To Χ κραταει το Low part το A το high 
                        self._emit(None, "STX", tmpx, "save low part from X") # Στο τελος παρε την τιμη απο το X και περασε την στο  A
                        self._emit(None, "LDA", tmpx, "A = low part in X")
                        return False

                else:  # '/'
                    # Διαίρεση: (A:X)/R -> A=quotient, X=remainder
                    wide = self._expr_into_A(L, want_wide=True)  # προσπάθησε να έχεις ήδη A:X
                    if wide:
                        # Έχουμε έγκυρο A:X -> DIV κατευθείαν
                        self._emit(None, "DIV", addrR, "(A:X)/R -> A=quot, X=rem")
                        return False
                    # Αλλιώς, "συνθέτουμε" A:X = 0:A  (βάζουμε το μέρισμα στο X)
                    tmpd = self._reserve_var(self._fq("TMPDIV")) 
                    self._emit(None, "STA", tmpd, "save dividend") #Α: πηλίκο
                    self._emit(None, "LDA", self._const(0), "A=0 for DIV")
                    self._emit(None, "LDX", tmpd, "X=dividend low") #Χ= υπολοιπο
                    self._emit(None, "DIV", addrR, "(A:X)/R -> A=quot, X=rem") #x = Α (η μεταβλητη μου παινρει το πηλικο)
                    return False

            if tag == 'call':
                # Κλήση συνάρτησης ως ΕΚΦΡΑΣΗ: στο τέλος το αποτέλεσμα θα είναι στο A.
                # e = ('call', callee, actuals)
                _, callee, actuals = e

                # Πάρε από το symbol table τα ονόματα των ΠΑΡΑΜΕΤΡΩΝ του callee, με τη σειρά τους.
                # (Οι σημασιολογικοί έλεγχοι έχουν ήδη επιβάλει ίδιο πλήθος actuals/params.)
                param_names = [
                    entry['name']
                    for entry in self.symbol_table.get(callee, [])
                    if entry['kind'] == 'param'
                ]

                # Πέρασμα ορισμάτων "by name": για κάθε actual υπολόγισε την τιμή (στο A)
                # και κάνε STA στο label της αντίστοιχης παραμέτρου του callee.
                for i, arg in enumerate(actuals):
                    if i >= len(param_names):
                        break  # ασφαλιστική δικλείδα· κανονικά δεν συμβαίνει λόγω semantic check
                    p = param_names[i]
                    dst = self._label_for(callee, p)          # πραγματική θέση μνήμης της παραμέτρου callee.p
                    self._expr_into_A(arg)                    # υπολόγισε το actual_i -> A (αριστερά-πριν-δεξιά, σειριακά)
                    self._emit(None, "STA", dst, f"arg -> {callee}.{p}")  # αποθήκευσέ το στην παράμετρο

                # Κλήση της ρουτίνας: JMP στο label εισόδου της συνάρτησης.
                # Ο μηχανισμός επιστροφής γίνεται με STJ RET(0:2) στο prologue και JMP RET στο return.
                self._emit(None, "JMP", self._get_func_label(callee), f"call {callee}")

                # Σύμβαση: η τιμή επιστροφής της συνάρτησης βρίσκεται στον A.
                return False  # όχι wide αποτέλεσμα· ο καλών μπορεί να κάνει STA αν χρειάζεται


            if tag == 'relop':
                # Σύγκριση ως ΤΙΜΗ (όχι ως branch): βάλε 0 (false) ή 1 (true) στο A.
                # e = ('relop', op, L, R), op ∈ {'==','!=','<','<=','>','>='}
                _, op, L, R = e
                self._relop_into_boolA(op, L, R)  # LDA L; CMPA R; jump-logic -> LDA 0/1
                return False  # αποτέλεσμα στο A (0/1), δεν χρησιμοποιεί A:X


        # Fallback για μη-υλοποιημένες μορφές εκφράσεων
        self._emit(None, "NOP", "", "TODO expr")
        return False
