def build_symbol_table(ast):
    # Κατασκευάζει και επιστρέφει τον πίνακα συμβόλων (symbol table) από το AST.
    symbol_table = {}
    symbol_table["global"] = []  # Global scope: λίστα με όλες τις συναρτήσεις του προγράμματος

    if not ast or ast[0] != 'program':
        # Αν το AST δεν είναι έγκυρο/αναμενόμενο, επέστρεψε μόνο το global.
        return symbol_table

    methods = ast[1] #Παίρνει τη λίστα με τις μεθόδους του προγράμματος από το AST.

    for method in methods:
        if method[0] == 'method':
            # Μορφή κόμβου: ('method', return_type, name, params, body)
            _, return_type, name, params, body = method

            # Δημιουργία πίνακα (scope) για κάθε μέθοδο: θα περιέχει params & locals ως entries.
            symbol_table[name] = []
            
            # Καταχώρηση της συνάρτησης στο global (για semantic checks & codegen)
            global_entry = {
                'name': name,
                'kind': 'function',
                'type': return_type,
                'params': [param[1] for param in params]  # Κρατάμε μόνο τα ονόματα των παραμέτρων int x κρατα το x
            }
            symbol_table["global"].append(global_entry) #για να γνωριζουμει το global ολες τις συναρτησεις

            # Καταχώρηση παραμέτρων στο scope της μεθόδου
            for param in params:
                if isinstance(param, tuple) and param[0] == 'int': #Επιβεβαιωση ότι κάθε στοιχείο είναι tuple της μορφής ('int', μεταβλητη).
                    param_name = param[1]
                    entry = {
                        'name': param_name,
                        'type': 'int',
                        'kind': 'param'  # Σύμβολο τύπου "παράμετρος"
                    }
                    symbol_table[name].append(entry)

            # Καταχώρηση τοπικών μεταβλητών από τις δηλώσεις του σώματος
            _, decls, _ = body  # body = ('body', decls, stmts)
            for decl in decls:
                if decl[0] == 'decl':
                    var_list = decl[2]  # Λίστα: [(var_name, init_expr_or_None), ...]
                    for var in var_list:
                        var_name = var[0]
                        entry = {
                            'name': var_name,
                            'type': 'int',
                            'kind': 'var'  # Σύμβολο τύπου "τοπική μεταβλητή"
                        }
                        symbol_table[name].append(entry)

    return symbol_table
