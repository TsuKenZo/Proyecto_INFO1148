"""Descenso recursivo de ARMLANG: 19 métodos para las 33 producciones.

Los FIRST/FOLLOW se transcriben del informe. No importa el verificador LL(1).
Construye el AST durante el análisis y se detiene en el primer error.
"""

from collections.abc import Iterable
from typing import NoReturn

from arbol import (
    Abrir, Bloque, Cerrar, Comparacion, Condicion, Mover, No,
    O, Programa, Regla, Sentencia, Si, Y,
)
from lexico import TERMINALES, Token


FIRST_ACCION = frozenset({"MOVER", "ABRIR", "CERRAR"})
FIRST_SENTENCIA = FIRST_ACCION | {"IF"}
FIRST_PRIMARIO = frozenset({"ID", "("})
FIRST_CONDICION = FIRST_PRIMARIO | {"NOT"}
FIRST_VALOR = frozenset({"NUM", "TRUE", "FALSE"})
FOLLOW_SINO = FIRST_SENTENCIA | {"}"}
FOLLOW_CONDICION = frozenset({"THEN", ")", "{"})
FOLLOW_CONJUNCION = FOLLOW_CONDICION | {"OR"}
ORDEN_TERMINALES = {terminal: i for i, terminal in enumerate((*TERMINALES, "$"))}


class ErrorSintactico(Exception):
    """Terminales esperados y token que impidió continuar el análisis."""

    def __init__(self, esperados: Iterable[str], encontrado: Token):
        self.esperados = frozenset(esperados)
        self.encontrado = encontrado
        self.posicion = encontrado.posicion
        ordenados = sorted(self.esperados, key=ORDEN_TERMINALES.__getitem__)
        nombres = ["el fin de la entrada" if t == "$" else t for t in ordenados]
        esperado = nombres[0] if len(nombres) == 1 else (
            ", ".join(nombres[:-1]) + " o " + nombres[-1]
        )
        hallazgo = (
            "se alcanzó el fin de la entrada" if encontrado.tipo == "$"
            else f"se encontró '{encontrado.lexema}'"
        )
        super().__init__(
            f"Error sintáctico en la posición {self.posicion}: "
            f"se esperaba {esperado}, {hallazgo}."
        )


class Parser:
    """Una instancia por entrada: Parser(tokenizar(texto), len(texto))."""

    def __init__(self, tokens: list[Token], longitud_texto: int):
        self.tokens = [*tokens, Token("$", "", longitud_texto)]
        self.indice = 0

    @property
    def actual(self) -> Token:
        return self.tokens[self.indice]

    def avanzar(self) -> None:
        if self.actual.tipo != "$":
            self.indice += 1

    def error_esperado(self, esperados: Iterable[str]) -> NoReturn:
        raise ErrorSintactico(esperados, self.actual)

    def coincidir(self, esperado: str) -> Token:
        if self.actual.tipo != esperado:
            self.error_esperado({esperado})
        token = self.actual
        self.avanzar()
        return token

    def analizar(self) -> Programa:
        programa = self.programa()
        self.coincidir("$")
        return programa

    def programa(self) -> Programa:
        """(1) programa -> regla reglas."""
        if self.actual.tipo != "WHEN":
            self.error_esperado({"WHEN"})
        primera = self.regla()
        return Programa([primera, *self.reglas()])

    def reglas(self) -> list[Regla]:
        """(2,3) reglas -> regla reglas | epsilon; FOLLOW = {$}."""
        reglas = []
        while self.actual.tipo == "WHEN":
            reglas.append(self.regla())
        if self.actual.tipo != "$":
            self.error_esperado({"WHEN", "$"})
        return reglas

    def regla(self) -> Regla:
        """(4) regla -> WHEN condicion THEN bloque."""
        self.coincidir("WHEN")
        condicion = self.condicion()
        self.coincidir("THEN")
        return Regla(condicion, self.bloque())

    def bloque(self) -> Bloque:
        """(5) bloque -> { sentencias }."""
        self.coincidir("{")
        sentencias = self.sentencias()
        self.coincidir("}")
        return Bloque(sentencias)

    def sentencias(self) -> list[Sentencia]:
        """(6,7) sentencias -> sentencia sentencias | epsilon."""
        sentencias = []
        while self.actual.tipo in FIRST_SENTENCIA:
            sentencias.append(self.sentencia())
        if self.actual.tipo != "}":
            self.error_esperado(FIRST_SENTENCIA | {"}"})
        return sentencias

    def sentencia(self) -> Sentencia:
        """(8,9) sentencia -> accion ; | si."""
        if self.actual.tipo in FIRST_ACCION:
            accion = self.accion()
            self.coincidir(";")
            return accion
        if self.actual.tipo == "IF":
            return self.si()
        self.error_esperado(FIRST_SENTENCIA)

    def accion(self) -> Mover | Abrir | Cerrar:
        """(10–12) MOVER articulacion NUM | ABRIR PINZA | CERRAR PINZA."""
        if self.actual.tipo == "MOVER":
            self.coincidir("MOVER")
            articulacion = self.articulacion()
            angulo = int(self.coincidir("NUM").lexema)
            return Mover(articulacion, angulo)
        if self.actual.tipo == "ABRIR":
            self.coincidir("ABRIR")
            self.coincidir("PINZA")
            return Abrir()
        if self.actual.tipo == "CERRAR":
            self.coincidir("CERRAR")
            self.coincidir("PINZA")
            return Cerrar()
        self.error_esperado(FIRST_ACCION)

    def articulacion(self) -> str:
        """(13,14) articulacion -> BASE | BRAZO."""
        if self.actual.tipo not in {"BASE", "BRAZO"}:
            self.error_esperado({"BASE", "BRAZO"})
        return self.coincidir(self.actual.tipo).tipo

    def si(self) -> Si:
        """(15) si -> IF condicion bloque sino."""
        self.coincidir("IF")
        condicion = self.condicion()
        entonces = self.bloque()
        return Si(condicion, entonces, self.sino())

    def sino(self) -> Bloque | Si | None:
        """(16,17) sino -> ELSE sino_cuerpo | epsilon."""
        if self.actual.tipo == "ELSE":
            self.coincidir("ELSE")
            return self.sino_cuerpo()
        if self.actual.tipo in FOLLOW_SINO:
            return None
        self.error_esperado({"ELSE"} | FOLLOW_SINO)

    def sino_cuerpo(self) -> Si | Bloque:
        """(18,19) sino_cuerpo -> si | bloque."""
        if self.actual.tipo == "IF":
            return self.si()
        if self.actual.tipo == "{":
            return self.bloque()
        self.error_esperado({"IF", "{"})

    def condicion(self) -> Condicion:
        """(20) condicion -> conjuncion condicion_r."""
        if self.actual.tipo not in FIRST_CONDICION:
            self.error_esperado(FIRST_CONDICION)
        return self.condicion_r(self.conjuncion())

    def condicion_r(self, izquierda: Condicion) -> Condicion:
        """(21,22) OR conjuncion condicion_r | epsilon; acumula por izquierda."""
        while self.actual.tipo == "OR":
            self.coincidir("OR")
            izquierda = O(izquierda, self.conjuncion())
        if self.actual.tipo not in FOLLOW_CONDICION:
            self.error_esperado({"OR"} | FOLLOW_CONDICION)
        return izquierda

    def conjuncion(self) -> Condicion:
        """(23) conjuncion -> negacion conjuncion_r."""
        if self.actual.tipo not in FIRST_CONDICION:
            self.error_esperado(FIRST_CONDICION)
        return self.conjuncion_r(self.negacion())

    def conjuncion_r(self, izquierda: Condicion) -> Condicion:
        """(24,25) AND negacion conjuncion_r | epsilon; acumula por izquierda."""
        while self.actual.tipo == "AND":
            self.coincidir("AND")
            izquierda = Y(izquierda, self.negacion())
        if self.actual.tipo not in FOLLOW_CONJUNCION:
            self.error_esperado({"AND"} | FOLLOW_CONJUNCION)
        return izquierda

    def negacion(self) -> Condicion:
        """(26,27) negacion -> NOT negacion | primario."""
        if self.actual.tipo == "NOT":
            self.coincidir("NOT")
            return No(self.negacion())
        if self.actual.tipo in FIRST_PRIMARIO:
            return self.primario()
        self.error_esperado(FIRST_CONDICION)

    def primario(self) -> Condicion:
        """(28,29) primario -> ( condicion ) | comparacion."""
        if self.actual.tipo == "(":
            self.coincidir("(")
            condicion = self.condicion()
            self.coincidir(")")
            return condicion
        if self.actual.tipo == "ID":
            return self.comparacion()
        self.error_esperado(FIRST_PRIMARIO)

    def comparacion(self) -> Comparacion:
        """(30) comparacion -> ID OP_REL valor."""
        identificador = self.coincidir("ID").lexema
        operador = self.coincidir("OP_REL").lexema
        return Comparacion(identificador, operador, self.valor())

    def valor(self) -> int | bool:
        """(31–33) valor -> NUM | TRUE | FALSE."""
        if self.actual.tipo == "NUM":
            return int(self.coincidir("NUM").lexema)
        if self.actual.tipo == "TRUE":
            self.coincidir("TRUE")
            return True
        if self.actual.tipo == "FALSE":
            self.coincidir("FALSE")
            return False
        self.error_esperado(FIRST_VALOR)
