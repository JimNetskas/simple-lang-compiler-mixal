import ply.yacc as yacc
from lexer import tokens

start = 'PROGRAM'  # Ορίζει το αρχικό μη τερματικό σύμβολο της γραμματικής

def p_PROGRAM(p):
    '''PROGRAM : METH_LIST
               | empty'''
    p[0] = ('program', p[1]) #τυλίγω σε root κόμβο (πάντα επιστρέφω ('program', <λίστα_μεθόδων_ή_κενό>))

def p_meth_list(p):
    '''METH_LIST : METH METH_LIST
                 | METH'''
    if len(p) == 3:
        p[0] = [p[1]] + p[2] #μετατροπη p[1] σε λιστα για να μπορω να προσθεσω και αλλα στοιχεια (αναδρομικός ορισμός λίστας)
    else:
        p[0] = [p[1]]        # βάση: μία μόνο μέθοδος σε λίστα

def p_meth(p):
    '''METH : TYPE ID "(" PARAMS ")" BODY'''
    p[0] = ('method', p[1], p[2], p[4] , p[6])  # ('method', type, name, params_list, ('body', decls, stmts))

def p_params(p):
    '''PARAMS : FORMALS TYPE ID
              | empty'''
    if len(p) == 4:
        p[0] = p[1] + [(p[2], p[3])]  # προσθέτω την “τελευταία” παράμετρο στα FORMALS
    else:
        p[0] = []                     # καμία παράμετρος

def p_formals(p):
    '''FORMALS : FORMALS TYPE ID ',' 
               | empty'''
    if len(p) == 5:
        p[0] = p[1] + [(p[2], p[3])]  # συσσώρευση παραμέτρων που τελειώνουν με κόμμα
    else:
        p[0] = []                     

def p_type(p):
    '''TYPE : INT'''
    p[0] = p[1]       # περνάω τύπο

def p_body(p):
    '''BODY : "{" DECLS STMTS "}" '''
    p[0] = ('body', p[2],p[3])  # ομαδοποιώ δηλώσεις και εντολές σε ενιαίο κόμβο σώματος

def p_decls(p):
    '''DECLS : DECLS DECL
             | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]    # λίστα δηλώσεων 
    else:
        p[0] =[]              

def p_decl(p):
    '''DECL : TYPE ID VARS ";"
            | TYPE ID "=" EXPR VARS ";"'''
    if len(p) == 5:
        p[0] = ('decl', p[1], [(p[2], None)] + p[3])  # πρώτη μεταβλητή χωρίς αρχικοποίηση + ό,τι επιστρέφει το VARS
    else:
        z_expr = p[4]                                  # έκφραση αρχικοποίησης για την πρώτη μεταβλητή
        z_decl = (p[2], z_expr)
        p[0] = ('decl', p[1], [z_decl] + p[5])         # πρώτη μεταβλητή με init + τα υπόλοιπα από VARS

def p_vars(p):
    '''VARS : "," ID VARS
            | ","  ID "=" EXPR VARS
            | empty'''
    if len(p) == 4:
        p[0] = [(p[2], None)] + p[3]                   # καταχώριση επιπλέον ονόματος χωρίς init
    elif len(p) == 6:
        p[0] = [(p[2], p[4])] + p[5]                   # καταχώριση επιπλέον ονόματος με init έκφραση
    else:
        p[0] = []                                      # τέλος λίστας

def p_stmts(p):
    '''STMTS : STMTS STMT
             | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]    # λίστα εντολών (αναδρομική συσσώρευση)
    else:
        p[0] = []               

def p_stmt(p):
    '''STMT : ASSIGN ";"
            | RETURN EXPR ";"
            | IF "(" EXPR ")" STMT
            | IF "(" EXPR ")" STMT ELSE STMT
            | WHILE "(" EXPR ")" STMT
            | BREAK ";"
            | BLOCK
            | ";"'''
    if len(p) == 3:
        if p.slice[1].type == 'BREAK':
            p[0] = ('break_stmt',)                      # break statement
        else:
            p[0] = ('assign_stmt', p[1])               # ανάθεση (ASSIGN ';')
    elif len(p) == 4:
        p[0] = ('return_stmt', p[2])                   # return έκφραση
    elif len(p) == 6 and p[1] == 'if':
        p[0] = ('if_stmt', p[3], p[5], ('empty_stmt',)) # if χωρίς else → else = empty_stmt
    elif len(p) == 8:
        p[0] = ('if_stmt', p[3], p[5], p[7])           # if με else
    elif len(p) == 6 and p[1] == 'while':
        p[0] = ('while_stmt', p[3], p[5])              # while (cond) stmt
    elif len(p) == 2:
        if p[1] == ';':
            p[0] = ('empty_stmt',)                     # κενή εντολή
        else:
            p[0] = p[1]                                # BLOCK περνάει ως έχει

def p_block(p):
    '''BLOCK : "{" STMTS "}"'''
    p[0] = ('block', p[2])                             # μπλοκ εντολών

def p_assign(p):
    '''ASSIGN : ID "=" EXPR'''
    p[0] = ('assign', p[1], p[3])                      # (lhs, expr) κόμβος ανάθεσης (χωρίς ';')

def p_expr(p):
    '''EXPR : ADD_EXPR RELOP ADD_EXPR
            | ADD_EXPR'''
    if len(p) == 4:
        p[0] = ('relop', p[2], p[1], p[3])             # σχεσιακός τελεστής: ('relop', op, left, right)
    else:
        p[0] = p[1]                                    # απλή προώθηση ADD_EXPR

def p_relop(p):
    '''RELOP : LE
             | LT
             | GT
             | GE
             | EQ
             | NE'''
    p[0] = p[1]                                        # περνάω το σύμβολο του τελεστή σχέσης

def p_add_expr(p):
    '''ADD_EXPR : ADD_EXPR ADDOP TERM
                | TERM'''
    if len(p) == 4:
        p[0] = ('add', p[2], p[1], p[3])               # αθροιστικός/αφαιρετικός κόμβος ('add', '+|-', left, right)
    else:
        p[0] = p[1]                                    # προώθηση TERM

def p_addop(p):
    '''ADDOP : "+"
             | "-"'''
    p[0] = p[1]                                        # επιστρέφω τον τελεστή '+' ή '-'

def p_term(p):
    '''TERM : TERM MULOP FACTOR
            | FACTOR'''
    if len(p) == 4:
        p[0] = ('mulop', p[2], p[1], p[3])             # πολλαπλασιασμός/διαίρεση ('mulop','*|/', left, right)
    else:
        p[0] = p[1]                                    # προώθηση FACTOR

def p_mulop(p):
    '''MULOP : "*"
             | "/"'''
    p[0] = p[1]                                        # επιστρέφω τον τελεστή '*' ή '/'

def p_factor(p):
    '''FACTOR : ID "(" ACTUALS ")"
              | "(" EXPR ")"
              | ID
              | NUM
              | BOOLEAN'''
    if len(p) == 2:
        if p.slice[1].type == 'NUM':
            p[0] = p[1]                                # αριθμητικό literal (int)
        elif p.slice[1].type == 'BOOLEAN':
            p[0] = ('bool', p[1])                      # boolean literal ως ('bool', 0|1)
        else:
            p[0] = p[1]                                # αναγνωριστικό (ID)
    elif len(p) == 4:
        p[0] = p[2]                                    # παρενθετική έκφραση: επιστρέφω το εσωτερικό EXPR
    elif len(p) == 5:
        p[0] = ('call', p[1], p[3])                    # κλήση συνάρτησης: ('call', fname, args_list)

def p_actuals(p):
    '''ACTUALS : ARGS EXPR
               | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]                           # ολοκλήρωση λίστας ορισμάτων: ARGS + τελευταίο EXPR
    else:
        p[0] = []                                      # καμία παράμετρος

def p_args(p):
    '''ARGS : ARGS EXPR ","
            | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[2]]                           # συσσώρευση ενδιάμεσων ορισμάτων (με κόμμα στο τέλος)
    else:
        p[0] = []                                      # αρχικοποίηση κενής λίστας ορισμάτων

def p_empty(p):
    'empty :'
    p[0] = []                                      

def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' (line {p.lineno})")  
    else:
        print("Syntax error at EOF")                                 
    raise SyntaxError                                                

parser = yacc.yacc()  # κατασκευή του parser
