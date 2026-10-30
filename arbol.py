"""Nodos del AST de ARMLANG, según CONTRATO_IMPLEMENTACION.md.

El parser construye estos datos sin ejecutar las acciones del brazo.
Las funciones de impresión corresponden al paso 6 del reparto.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Programa:
    reglas: list[Regla]


@dataclass
class Regla:
    condicion: Condicion
    bloque: Bloque


@dataclass
class Bloque:
    sentencias: list[Sentencia]


@dataclass
class Mover:
    articulacion: str
    angulo: int


@dataclass
class Abrir:
    parte: str = "PINZA"


@dataclass
class Cerrar:
    parte: str = "PINZA"


@dataclass
class Si:
    condicion: Condicion
    entonces: Bloque
    sino: Bloque | Si | None = None


@dataclass
class O:
    izquierda: Condicion
    derecha: Condicion


@dataclass
class Y:
    izquierda: Condicion
    derecha: Condicion


@dataclass
class No:
    operando: Condicion


@dataclass
class Comparacion:
    identificador: str
    operador: str
    valor: int | bool


Condicion = Comparacion | O | Y | No
Sentencia = Mover | Abrir | Cerrar | Si


def formatear_ast(programa: Programa) -> str:
    """Devuelve una representación jerárquica del programa."""
    lineas = []
    pendientes = [(programa, 0)]
    while pendientes:
        nodo, nivel = pendientes.pop()
        prefijo = '  ' * nivel
        hijos = []
        if isinstance(nodo, str):
            lineas.append(prefijo + nodo)
            continue
        if isinstance(nodo, Comparacion):
            valor = str(nodo.valor).upper() if isinstance(nodo.valor, bool) else str(nodo.valor)
            rotulo = f'Comparacion {nodo.identificador} {nodo.operador} {valor}'
        elif isinstance(nodo, Mover):
            rotulo = f'Mover {nodo.articulacion} {nodo.angulo}'
        elif isinstance(nodo, (Abrir, Cerrar)):
            rotulo = f'{type(nodo).__name__} {nodo.parte}'
        else:
            rotulo = type(nodo).__name__
            if isinstance(nodo, Programa):
                hijos = [(x, nivel + 1) for x in nodo.reglas]
            elif isinstance(nodo, Regla):
                hijos = [(nodo.condicion, nivel + 1), (nodo.bloque, nivel + 1)]
            elif isinstance(nodo, Bloque):
                hijos = [(x, nivel + 1) for x in nodo.sentencias]
            elif isinstance(nodo, Si):
                hijos = [(nodo.condicion, nivel + 1), ('entonces', nivel + 1), (nodo.entonces, nivel + 2)]
                if nodo.sino is not None:
                    hijos += [('sino', nivel + 1), (nodo.sino, nivel + 2)]
            elif isinstance(nodo, (O, Y)):
                hijos = [(nodo.izquierda, nivel + 1), (nodo.derecha, nivel + 1)]
            elif isinstance(nodo, No):
                hijos = [(nodo.operando, nivel + 1)]
            else:
                raise TypeError(f'Nodo desconocido: {type(nodo).__name__}')
        lineas.append(prefijo + rotulo)
        pendientes.extend(reversed(hijos))
    return '\n'.join(lineas)


def imprimir_ast(programa: Programa) -> None:
    print(formatear_ast(programa))
