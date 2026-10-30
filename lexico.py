"""Tokenización de ARMLANG con posiciones de carácter desde cero.

Usa expresiones regulares de la especificación; no agrega el fin de entrada.
No requiere bibliotecas externas ni imprime al importar o tokenizar.
"""

from dataclasses import dataclass
import re


# El orden coincide con el informe y permite ordenar mensajes del parser.
TERMINALES = (
    "WHEN", "THEN", "IF", "ELSE", "MOVER", "ABRIR", "CERRAR",
    "BASE", "BRAZO", "PINZA", "AND", "OR", "NOT", "TRUE", "FALSE",
    "ID", "NUM", "OP_REL", ";", "(", ")", "{", "}",
)
RESERVADAS = frozenset(TERMINALES[:15])

PATRON = re.compile(
    r"(?P<NUM>[0-9]+)"
    r"|(?P<OP_REL>>=|<=|==|!=|>|<)"
    r"|(?P<SEPARADOR>[;(){}])"
    r"|(?P<ID>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<ESPACIO>[ \t\r\n]+)"
    r"|(?P<ERROR>.)",
    re.DOTALL,
)


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    posicion: int


class ErrorLexico(Exception):
    """Primer carácter que no puede formar un token del lenguaje."""

    def __init__(self, simbolo: str, posicion: int):
        self.simbolo = simbolo
        self.posicion = posicion
        super().__init__(
            f"Error léxico: símbolo no reconocido '{simbolo}' "
            f"en la posición {posicion}."
        )


def tokenizar(texto: str) -> list[Token]:
    """Convierte texto a tokens; lanza ErrorLexico ante un símbolo inválido."""
    tokens = []
    for coincidencia in PATRON.finditer(texto):
        tipo = coincidencia.lastgroup
        lexema = coincidencia.group()
        if tipo == "ESPACIO":
            continue
        if tipo == "ERROR":
            raise ErrorLexico(lexema, coincidencia.start())
        if tipo == "SEPARADOR":
            tipo = lexema
        elif tipo == "ID" and lexema.upper() in RESERVADAS:
            tipo = lexema.upper()
        tokens.append(Token(tipo, lexema, coincidencia.start()))
    return tokens
