"""
verificador_ll1.py  --  ARMLANG (INFO1148, Proyecto)

Script AUXILIAR para contrastar los calculos hechos a mano en el informe:
  * conjuntos FIRST, FOLLOW y de prediccion
  * tabla predictiva LL(1) y deteccion de conflictos
  * analisis predictivo dirigido por la tabla (con traza y mensajes de error)

No reemplaza al parser del proyecto (descenso recursivo, en parser.py).
Uso:  python verificador_ll1.py            -> imprime todo
      python verificador_ll1.py "WHEN peso > 5 THEN { }"   -> analiza esa entrada
"""
import re
import sys

EPS = 'eps'
FIN = '$'

# (numero, lado izquierdo, lado derecho). Lado derecho vacio = epsilon.
GRAMATICA = [
    (1,  'programa',     ['regla', 'reglas']),
    (2,  'reglas',       ['regla', 'reglas']),
    (3,  'reglas',       []),
    (4,  'regla',        ['WHEN', 'condicion', 'THEN', 'bloque']),
    (5,  'bloque',       ['{', 'sentencias', '}']),
    (6,  'sentencias',   ['sentencia', 'sentencias']),
    (7,  'sentencias',   []),
    (8,  'sentencia',    ['accion', ';']),
    (9,  'sentencia',    ['si']),
    (10, 'accion',       ['MOVER', 'articulacion', 'NUM']),
    (11, 'accion',       ['ABRIR', 'PINZA']),
    (12, 'accion',       ['CERRAR', 'PINZA']),
    (13, 'articulacion', ['BASE']),
    (14, 'articulacion', ['BRAZO']),
    (15, 'si',           ['IF', 'condicion', 'bloque', 'sino']),
    (16, 'sino',         ['ELSE', 'sino_cuerpo']),
    (17, 'sino',         []),
    (18, 'sino_cuerpo',  ['si']),
    (19, 'sino_cuerpo',  ['bloque']),
    (20, 'condicion',    ['conjuncion', 'condicion_r']),
    (21, 'condicion_r',  ['OR', 'conjuncion', 'condicion_r']),
    (22, 'condicion_r',  []),
    (23, 'conjuncion',   ['negacion', 'conjuncion_r']),
    (24, 'conjuncion_r', ['AND', 'negacion', 'conjuncion_r']),
    (25, 'conjuncion_r', []),
    (26, 'negacion',     ['NOT', 'negacion']),
    (27, 'negacion',     ['primario']),
    (28, 'primario',     ['(', 'condicion', ')']),
    (29, 'primario',     ['comparacion']),
    (30, 'comparacion',  ['ID', 'OP_REL', 'valor']),
    (31, 'valor',        ['NUM']),
    (32, 'valor',        ['TRUE']),
    (33, 'valor',        ['FALSE']),
]

NO_TERMINALES = ['programa', 'reglas', 'regla', 'bloque', 'sentencias',
                 'sentencia', 'accion', 'articulacion', 'si', 'sino',
                 'sino_cuerpo', 'condicion', 'condicion_r', 'conjuncion',
                 'conjuncion_r', 'negacion', 'primario', 'comparacion', 'valor']

TERMINALES = ['WHEN', 'THEN', 'IF', 'ELSE', 'MOVER', 'ABRIR', 'CERRAR',
              'BASE', 'BRAZO', 'PINZA', 'AND', 'OR', 'NOT', 'TRUE', 'FALSE',
              'ID', 'NUM', 'OP_REL', ';', '(', ')', '{', '}']

INICIAL = 'programa'


# ---------------------------------------------------------------- FIRST/FOLLOW
def calcular_first():
    first = {nt: set() for nt in NO_TERMINALES}
    cambio = True
    while cambio:
        cambio = False
        for _, a, der in GRAMATICA:
            antes = len(first[a])
            first[a] |= first_de_cadena(der, first)
            cambio |= len(first[a]) != antes
    return first


def first_de_cadena(cadena, first):
    res = set()
    for s in cadena:
        if s in TERMINALES:
            res.add(s)
            return res
        res |= first[s] - {EPS}
        if EPS not in first[s]:
            return res
    res.add(EPS)
    return res


def calcular_follow(first):
    follow = {nt: set() for nt in NO_TERMINALES}
    follow[INICIAL].add(FIN)
    cambio = True
    while cambio:
        cambio = False
        for _, a, der in GRAMATICA:
            for i, s in enumerate(der):
                if s not in NO_TERMINALES:
                    continue
                resto = first_de_cadena(der[i + 1:], first)
                nuevo = resto - {EPS}
                if EPS in resto:
                    nuevo |= follow[a]
                if not nuevo <= follow[s]:
                    follow[s] |= nuevo
                    cambio = True
    return follow


def calcular_pred(first, follow):
    pred = {}
    for n, a, der in GRAMATICA:
        f = first_de_cadena(der, first)
        p = f - {EPS}
        if EPS in f:
            p |= follow[a]
        pred[n] = p
    return pred


def orden(conjunto):
    """Ordena un conjunto de terminales segun TERMINALES (y $ al final)."""
    return sorted(conjunto, key=lambda t: TERMINALES.index(t) if t in TERMINALES else 99)


# ---------------------------------------------------------------- tabla LL(1)
def construir_tabla(pred):
    tabla = {}
    for n, a, _ in GRAMATICA:
        for t in pred[n]:
            tabla.setdefault((a, t), []).append(n)
    return tabla


def conflictos(tabla):
    return {k: v for k, v in tabla.items() if len(v) > 1}


# ---------------------------------------------------------------- lexico minimo
RESERVADAS = {'WHEN', 'THEN', 'IF', 'ELSE', 'MOVER', 'ABRIR', 'CERRAR', 'BASE',
              'BRAZO', 'PINZA', 'AND', 'OR', 'NOT', 'TRUE', 'FALSE'}
ESPEC = [('NUM', r'[0-9]+'), ('OP_REL', r'>=|<=|==|!=|>|<'), (';', r';'),
         ('(', r'\('), (')', r'\)'), ('{', r'\{'), ('}', r'\}'),
         ('ID', r'[A-Za-z_][A-Za-z0-9_]*'), ('ESPACIO', r'[ \t\r\n]+'),
         ('ERROR', r'.')]
PATRON = '|'.join('(?P<G%d>%s)' % (i, e) for i, (_, e) in enumerate(ESPEC))


class ErrorLexico(Exception):
    def __init__(self, simbolo, pos):
        self.simbolo, self.pos = simbolo, pos
        super().__init__("Error léxico: símbolo no reconocido '%s' en la posición %d." % (simbolo, pos))


def tokenizar(texto):
    """Devuelve [(terminal, lexema, posicion)]. Lanza ErrorLexico."""
    toks = []
    for m in re.finditer(PATRON, texto, flags=re.DOTALL):
        idx = int(m.lastgroup[1:])
        tipo, lex = ESPEC[idx][0], m.group()
        if tipo == 'ESPACIO':
            continue
        if tipo == 'ERROR':
            raise ErrorLexico(lex, m.start())
        if tipo == 'ID' and lex.upper() in RESERVADAS:
            tipo = lex.upper()
        toks.append((tipo, lex, m.start()))
    return toks


# ---------------------------------------------------------------- analisis
def lista_o(items):
    nombres = ['el fin de la entrada' if t == FIN else t for t in items]
    if len(nombres) == 1:
        return nombres[0]
    return ', '.join(nombres[:-1]) + ' o ' + nombres[-1]


def mensaje_sintactico(pos, esperados, tok):
    if tok[0] == FIN:
        encontrado = 'se alcanzó el fin de la entrada'
    else:
        encontrado = "se encontró '%s'" % tok[1]
    return 'Error sintáctico en la posición %d: se esperaba %s, %s.' % (
        pos, lista_o(orden(esperados)), encontrado)


def analizar(texto, tabla=None, con_traza=False):
    """Analisis predictivo dirigido por tabla.
    Retorna (aceptada, mensaje_o_None, traza)."""
    if tabla is None:
        f = calcular_first()
        tabla = construir_tabla(calcular_pred(f, calcular_follow(f)))
    try:
        toks = tokenizar(texto)
    except ErrorLexico as e:
        return False, str(e), []
    toks.append((FIN, '', len(texto)))
    pila = [FIN, INICIAL]
    i = 0
    traza = []
    paso = 1
    while True:
        cima, tok = pila[-1], toks[i]
        if con_traza:
            traza.append((paso, list(reversed(pila)),
                          [t[0] for t in toks[i:]], None))
        paso += 1
        if cima == FIN and tok[0] == FIN:
            if con_traza:
                traza[-1] = traza[-1][:3] + ('Aceptar',)
            return True, None, traza
        if cima in NO_TERMINALES:
            prods = tabla.get((cima, tok[0]))
            if not prods:
                esp = {t for (nt, t) in tabla if nt == cima}
                return False, mensaje_sintactico(tok[2], esp, tok), traza
            n = prods[0]
            der = [g for g in GRAMATICA if g[0] == n][0][2]
            pila.pop()
            pila.extend(reversed(der))
            if con_traza:
                traza[-1] = traza[-1][:3] + ('Producción %d' % n,)
        else:
            if cima != tok[0]:
                return False, mensaje_sintactico(tok[2], {cima}, tok), traza
            pila.pop()
            i += 1
            if con_traza:
                traza[-1] = traza[-1][:3] + ('Coincidir %s' % cima,)


# ---------------------------------------------------------------- salida
def verificar():
    first = calcular_first()
    follow = calcular_follow(first)
    pred = calcular_pred(first, follow)
    tabla = construir_tabla(pred)
    print('FIRST')
    for nt in NO_TERMINALES:
        print('  %-14s {%s}' % (nt, ', '.join(orden(first[nt] - {EPS}) + ([EPS] if EPS in first[nt] else []))))
    print('FOLLOW')
    for nt in NO_TERMINALES:
        print('  %-14s {%s}' % (nt, ', '.join(orden(follow[nt]))))
    print('PREDICCION')
    for n, a, der in GRAMATICA:
        print('  %2d %-13s -> %-32s {%s}' % (n, a, ' '.join(der) or EPS, ', '.join(orden(pred[n]))))
    c = conflictos(tabla)
    print('Conflictos en la tabla:', c if c else 'ninguno  ->  la gramática es LL(1)')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ok, msg, _ = analizar(sys.argv[1])
        print('Entrada válida.' if ok else msg)
    else:
        verificar()
