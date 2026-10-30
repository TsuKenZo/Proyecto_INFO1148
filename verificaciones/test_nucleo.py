"""Comprobaciones del paso 5, mediante la API; no sustituyen pruebas.py.

Desde la raíz: python3 -m unittest discover -s verificaciones -v
Solo biblioteca estándar. El informe conserva las entradas V/I/L originales.
"""

from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
from io import StringIO
from pathlib import Path
import re
import unittest

from arbol import Abrir, Bloque, Cerrar, Comparacion, Mover, No, O, Programa, Regla, Si, Y
from lexico import ErrorLexico, RESERVADAS, Token, tokenizar
from parser import ErrorSintactico, Parser
import verificador_ll1 as referencia


RAIZ = Path(__file__).resolve().parents[1]


def casos_del_informe():
    """Extrae las entradas de sus tablas, sin copiar ni modificar sus textos."""
    casos = []
    for linea in (RAIZ / "main.tex").read_text(encoding="utf-8").splitlines():
        if not re.match(r"^[VIL]\d+ &", linea):
            continue
        columnas = linea.split("&")
        nombre, celda = columnas[0].strip(), columnas[1].strip()
        if nombre == "L1":
            entrada = ""
        else:
            if not celda.startswith(r"\tm{") or not celda.endswith("}"):
                raise AssertionError(f"Formato de entrada no reconocido: {nombre}")
            entrada = celda[4:-1]
            for escapado, literal in [(r"\_", "_"), (r"\{", "{"), (r"\}", "}")]:
                entrada = entrada.replace(escapado, literal)
        casos.append((nombre, entrada, columnas[2].strip() == "Aceptada"))
    return casos


def analizar(texto):
    return Parser(tokenizar(texto), len(texto)).analizar()


def resultado(texto):
    try:
        analizar(texto)
    except (ErrorLexico, ErrorSintactico) as error:
        return False, str(error)
    return True, None


class NucleoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        first = referencia.calcular_first()
        cls.tabla = referencia.construir_tabla(
            referencia.calcular_pred(first, referencia.calcular_follow(first))
        )

    def test_27_casos_del_informe_y_mensajes_del_auxiliar(self):
        casos = casos_del_informe()
        self.assertEqual(
            [nombre for nombre, _, _ in casos],
            [f"V{i}" for i in range(1, 11)]
            + [f"I{i}" for i in range(1, 11)]
            + [f"L{i}" for i in range(1, 8)],
        )
        for nombre, entrada, esperado in casos:
            with self.subTest(caso=nombre):
                obtenido, mensaje = resultado(entrada)
                auxiliar, mensaje_auxiliar, _ = referencia.analizar(entrada, self.tabla)
                self.assertEqual(obtenido, esperado)
                self.assertEqual((obtenido, mensaje), (auxiliar, mensaje_auxiliar))

    def test_ejemplo_del_contrato(self):
        self.assertEqual(
            analizar("WHEN peso > 5 THEN { CERRAR PINZA; }"),
            Programa([Regla(Comparacion("peso", ">", 5), Bloque([Cerrar("PINZA")]))]),
        )

    def test_tokens_lexemas_posiciones_y_operador_mas_largo(self):
        texto = "\r\nwhen Peso>=05 then{abrir pinza;}\t"
        self.assertEqual(tokenizar(texto), [
            Token("WHEN", "when", 2), Token("ID", "Peso", 7),
            Token("OP_REL", ">=", 11), Token("NUM", "05", 13),
            Token("THEN", "then", 16), Token("{", "{", 20),
            Token("ABRIR", "abrir", 21), Token("PINZA", "pinza", 27),
            Token(";", ";", 32), Token("}", "}", 33),
        ])
        self.assertEqual(
            [t.lexema for t in tokenizar(">= <= == != > <")],
            [">=", "<=", "==", "!=", ">", "<"],
        )

    def test_reservadas_completas_y_limites_de_identificadores(self):
        for reservada in RESERVADAS:
            with self.subTest(reservada=reservada):
                self.assertEqual(tokenizar(reservada.lower())[0].tipo, reservada)
                self.assertEqual(tokenizar(reservada + "x")[0].tipo, "ID")
        self.assertEqual(tokenizar("_sensor2"), [Token("ID", "_sensor2", 0)])

    def test_token_inmutable_y_lista_del_llamador_sin_modificar(self):
        texto = "WHEN p == 1 THEN {}  \r\n"
        tokens = tokenizar(texto)
        copia = tokens.copy()
        parser = Parser(tokens, len(texto))
        with self.assertRaises(FrozenInstanceError):
            tokens[0].tipo = "ID"
        parser.analizar()
        self.assertEqual(tokens, copia)
        self.assertEqual(parser.actual, Token("$", "", len(texto)))

    def test_caracteres_fuera_del_alfabeto(self):
        # Incluye dígitos Unicode: [0-9]+ no debe comportarse como \d+.
        for simbolo in ["@", "-", ".", "#", "ñ", "١", "５", "\v", "\f", "\u00a0"]:
            with self.subTest(simbolo=repr(simbolo)):
                with self.assertRaises(ErrorLexico) as capturado:
                    tokenizar("WHEN " + simbolo)
                self.assertEqual(capturado.exception.simbolo, simbolo)
                self.assertEqual(capturado.exception.posicion, 5)
                self.assertEqual(resultado("WHEN " + simbolo),
                                 referencia.analizar("WHEN " + simbolo, self.tabla)[:2])

    def test_mensajes_adicionales_de_la_seccion_9(self):
        entradas = [
            "WHEN peso @ 5 THEN { }",
            "WHEN peso > 5 THEN { IF peso < 100 MOVER BASE 60; }",
        ]
        for entrada in entradas:
            with self.subTest(entrada=entrada):
                self.assertEqual(resultado(entrada),
                                 referencia.analizar(entrada, self.tabla)[:2])

    def test_entrada_vacia_blancos_y_fin_con_posicion_original(self):
        for texto in ["", " \t\r\n", "WHEN p > 5 THEN { \r\n  "]:
            with self.subTest(texto=texto):
                with self.assertRaises(ErrorSintactico) as capturado:
                    analizar(texto)
                error = capturado.exception
                self.assertEqual(error.posicion, len(texto))
                self.assertEqual(error.encontrado, Token("$", "", len(texto)))
                self.assertIsInstance(error.esperados, frozenset)

    def test_error_estructurado_y_mensaje_con_varios_esperados(self):
        texto = "WHEN peso > THEN {}"
        with self.assertRaises(ErrorSintactico) as capturado:
            analizar(texto)
        error = capturado.exception
        self.assertEqual(error.esperados, frozenset({"NUM", "TRUE", "FALSE"}))
        self.assertEqual(error.encontrado, Token("THEN", "THEN", 12))
        self.assertEqual(str(error), "Error sintáctico en la posición 12: "
                         "se esperaba TRUE, FALSE o NUM, se encontró 'THEN'.")

    def test_precedencia_agrupacion_y_asociacion_izquierda(self):
        a, b, c = [Comparacion(nombre, "==", 1) for nombre in "abc"]
        for texto, esperado in [
            ("a == 1 OR b == 1 AND c == 1", O(a, Y(b, c))),
            ("(a == 1 OR b == 1) AND c == 1", Y(O(a, b), c)),
            ("NOT a == 1 AND b == 1", Y(No(a), b)),
            ("NOT (a == 1 OR b == 1)", No(O(a, b))),
            ("NOT NOT a == 1", No(No(a))),
            ("a == 1 OR b == 1 OR c == 1", O(O(a, b), c)),
            ("a == 1 AND b == 1 AND c == 1", Y(Y(a, b), c)),
        ]:
            with self.subTest(condicion=texto):
                ast = analizar(f"WHEN {texto} THEN {{}}")
                self.assertEqual(ast.reglas[0].condicion, esperado)

    def test_else_del_if_externo_y_cadena_else_if(self):
        casos = {nombre: texto for nombre, texto, _ in casos_del_informe()}
        externo = analizar(casos["L5"]).reglas[0].bloque.sentencias[0]
        self.assertIsInstance(externo, Si)
        self.assertEqual(externo.sino, Bloque([Abrir()]))
        interno = externo.entonces.sentencias[0]
        self.assertIsNone(interno.sino)
        cadena = analizar(casos["V7"]).reglas[0].bloque.sentencias[0]
        self.assertEqual(cadena.entonces, Bloque([Mover("BASE", 60)]))
        self.assertIsInstance(cadena.sino, Si)
        self.assertEqual(cadena.sino.entonces, Bloque([Mover("BASE", 120)]))
        self.assertEqual(cadena.sino.sino, Bloque([Mover("BASE", 180)]))

    def test_orden_tipos_de_valores_y_ausencia_de_validacion_semantica(self):
        texto = ("when Sensor == true then {mover base 500;cerrar pinza;abrir pinza;}"
                 "WHEN otro != FALSE THEN {} WHEN numero == 001 THEN {}")
        reglas = analizar(texto).reglas
        self.assertEqual([r.condicion.identificador for r in reglas],
                         ["Sensor", "otro", "numero"])
        self.assertIs(reglas[0].condicion.valor, True)
        self.assertIs(reglas[1].condicion.valor, False)
        self.assertIs(type(reglas[2].condicion.valor), int)
        self.assertEqual(reglas[2].condicion.valor, 1)
        self.assertEqual(reglas[0].bloque.sentencias,
                         [Mover("BASE", 500), Cerrar(), Abrir()])
        self.assertEqual(reglas[1].bloque, Bloque([]))

    def test_listas_largas_no_consumen_recursion_de_python(self):
        ast = analizar("WHEN p == 1 THEN {" + "ABRIR PINZA;" * 1200 + "}")
        self.assertEqual(len(ast.reglas[0].bloque.sentencias), 1200)
        ast = analizar("WHEN p == 1 THEN {}" * 1200)
        self.assertEqual(len(ast.reglas), 1200)
        ast = analizar("WHEN " + " OR ".join(["p == 1"] * 1200) + " THEN {}")
        condicion, cantidad = ast.reglas[0].condicion, 1
        while isinstance(condicion, O):
            cantidad += 1
            condicion = condicion.izquierda
        self.assertEqual(cantidad, 1200)

    def test_mutaciones_de_tokens_contra_tabla_independiente(self):
        # Borrar o insertar tokens detecta errores de epsilon y consumo total.
        bases = [
            "WHEN p > 1 THEN { MOVER BASE 0; ABRIR PINZA; }",
            "WHEN NOT (a == 1 OR b != FALSE) THEN {} WHEN c < 5 THEN {}",
            "WHEN p > 1 THEN { IF p < 5 {} ELSE IF q == TRUE {} ELSE {} }",
        ]
        for base in bases:
            lexemas = [t.lexema for t in tokenizar(base)]
            variantes = []
            for i in range(len(lexemas)):
                variantes.append(" ".join(lexemas[:i] + lexemas[i + 1:]))
            for i in range(len(lexemas) + 1):
                for insertado in ["ELSE", ";", "}", "AND"]:
                    variantes.append(" ".join(lexemas[:i] + [insertado] + lexemas[i:]))
            for entrada in variantes:
                with self.subTest(entrada=entrada):
                    aceptada, mensaje, _ = referencia.analizar(entrada, self.tabla)
                    self.assertEqual(resultado(entrada), (aceptada, mensaje))

    def test_api_no_imprime_y_implementa_los_19_no_terminales(self):
        salida = StringIO()
        with redirect_stdout(salida):
            analizar("WHEN p == 1 THEN {}")
        self.assertEqual(salida.getvalue(), "")
        for nombre in referencia.NO_TERMINALES:
            self.assertTrue(callable(getattr(Parser, nombre)))


if __name__ == "__main__":
    unittest.main()
