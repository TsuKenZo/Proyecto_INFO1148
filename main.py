"""Interfaz de terminal del analizador ARMLANG."""
import argparse
import sys

from arbol import imprimir_ast
from lexico import ErrorLexico, tokenizar
from parser import ErrorSintactico, Parser


def main(argv=None):
    argumentos = argparse.ArgumentParser(description='Analizador sintáctico ARMLANG')
    entrada = argumentos.add_mutually_exclusive_group(required=True)
    entrada.add_argument('--archivo', metavar='RUTA')
    entrada.add_argument('--texto')
    opciones = argumentos.parse_args(argv)
    try:
        if opciones.archivo is not None:
            with open(opciones.archivo, encoding='utf-8', newline='') as archivo:
                texto = archivo.read()
        else:
            texto = opciones.texto
    except (OSError, UnicodeError) as error:
        print(f'Error al leer el archivo: {error}', file=sys.stderr)
        return 2
    try:
        arbol = Parser(tokenizar(texto), len(texto)).analizar()
    except (ErrorLexico, ErrorSintactico) as error:
        print(error, file=sys.stderr)
        return 1
    print('Entrada válida.')
    imprimir_ast(arbol)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
