import ply.lex as lex
from ply.lex import TOKEN
import re

reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'read': 'READ',
    'print': 'PRINT',
    'int': 'INT',
    'true': 'BOOLEAN',
    'false': 'BOOLEAN',
    'return': 'RETURN',
    'break' : 'BREAK'
}

tokens = [
    'ID', 'NUM',
    'EQ', 'NE', 'LE', 'GE', 'LT', 'GT'
] + list(set(reserved.values()))

literals = ['+', '-', '*', '/', '=', '(', ')', '{', '}', ';', ',', '[', ']']

# Σύνθετοι τελεστές
t_EQ = r'=='
t_NE = r'!='
t_LE = r'<='
t_GE = r'>='
t_LT = r'<'
t_GT = r'>'

# Αγνόηση whitespace
t_ignore = ' \t'

# Χειρισμός νέας γραμμής
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value) 

# Αγνόηση σχολίων //
def t_comment(t):
    r'//[^\n]*'
    pass

@TOKEN(r'[0-9]+')
def t_NUM(t):
    raw = t.value

    # Απόρριψη αν ξεκινά με 0 και ακολουθεί τουλάχιστον ένα ψηφίο μέχρι το τέλος (π.χ. 01, 0012 κτλπ)
    if re.match(r'0[0-9]+$', raw):
        print(f"[Lexer Error] Illegal number '{raw}' at line {t.lineno}") #Εκτυπώση μήνυμα λάθους με το προβληματικό literal και τη γραμμή
        return None

    t.value = int(raw) #Μεταροπή σε integer
    return t



# Αναγνώριση αναγνωριστικών ή λέξεων-κλειδιών
#Ελεγχος ότι ξεκινάει απο γράμμα και μετα 0+ χαρακτηες νουμερα underscore κτλπ.
@TOKEN(r'[a-zA-Z][a-zA-Z0-9_]*') 
def t_ID(t):
    if t.value in ['true', 'false']:
        t.type = 'BOOLEAN'
        t.value = 1 if t.value == 'true' else 0 
    else:
        #Αν ειναι λεξη-κελιδι, επεστρεψε το όνομα του keyword token αλλιως βαλε τιμη ID
        t.type = reserved.get(t.value, 'ID') 
    return t

# Χειρισμός σφαλμάτων
def t_error(t):
    print(f"[Lexer Error] Illegal character '{t.value[0]}' at line {t.lineno}")
    t.lexer.skip(1) #αποφυγη λουπας
    

# Δημιουργία lexer
lexer = lex.lex()
