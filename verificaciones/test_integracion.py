import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from arbol import formatear_ast
from lexico import tokenizar
from parser import Parser

RAIZ = Path(__file__).resolve().parents[1]


def cli(*args):
    return subprocess.run([sys.executable, str(RAIZ / 'main.py'), *args],
                          capture_output=True, text=True)


class IntegracionTests(unittest.TestCase):
    def test_formato_y_ramas(self):
        texto = 'WHEN p == TRUE THEN { IF p == 1 {} ELSE { ABRIR PINZA; } }'
        ast = Parser(tokenizar(texto), len(texto)).analizar()
        self.assertEqual(formatear_ast(ast), 'Programa\n  Regla\n    Comparacion p == TRUE\n    Bloque\n      Si\n        Comparacion p == 1\n        entonces\n          Bloque\n        sino\n          Bloque\n            Abrir PINZA')

    def test_cli_texto_y_archivo(self):
        resultado = cli('--texto', 'WHEN peso > 5 THEN { CERRAR PINZA; }')
        self.assertEqual(resultado.returncode, 0)
        self.assertIn('Entrada válida.\nPrograma', resultado.stdout)
        self.assertEqual(resultado.stderr, '')
        self.assertEqual(cli('--archivo', str(RAIZ / 'ejemplos/clasificacion.arm')).returncode, 0)
        self.assertEqual(cli('--archivo', str(RAIZ / 'ejemplos/invalido.arm')).returncode, 1)

    def test_errores(self):
        for texto, tipo in [('WHEN @', 'léxico'), ('WHEN p > THEN {}', 'sintáctico')]:
            resultado = cli('--texto', texto)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn(tipo, resultado.stderr)
            self.assertNotIn('Traceback', resultado.stderr)
        self.assertEqual(cli().returncode, 2)
        self.assertEqual(cli('--texto', '', '--archivo', 'x').returncode, 2)
        self.assertEqual(cli('--archivo', '/archivo/inexistente').returncode, 2)
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / 'invalido.arm'
            archivo.write_bytes(b'\xff')
            self.assertEqual(cli('--archivo', str(archivo)).returncode, 2)
