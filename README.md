# ARMLANG

Analizador léxico y sintáctico para un lenguaje de reglas de control de un brazo clasificador. El parser predictivo por descenso recursivo valida la entrada y construye un árbol de sintaxis abstracta (AST); no ejecuta movimientos ni verifica rangos físicos.

## Requisitos

Python 3.10 o posterior y biblioteca estándar; no se necesitan paquetes adicionales. La ejecución y las pruebas se verificaron con Python 3.12.3.

Ejecutar los comandos desde esta carpeta.

## Ejecución

```bash
python3 main.py --archivo ejemplos/clasificacion.arm
python3 main.py --texto 'WHEN peso > 5 THEN { CERRAR PINZA; }'
python3 main.py --archivo ejemplos/invalido.arm
```

Las opciones `--archivo` y `--texto` son excluyentes y una es obligatoria. Los archivos se leen en UTF-8. Una entrada válida muestra `Entrada válida.` y el AST jerárquico. Un error léxico o sintáctico se muestra en la salida de error con su posición desde cero. El código de salida es 0 en caso válido, 1 para errores del lenguaje y 2 para errores de argumentos o lectura.

## Formato del lenguaje

Un programa contiene una o más reglas `WHEN condición THEN { sentencias }`. Las condiciones admiten comparaciones de identificadores con enteros no negativos o `TRUE`/`FALSE`, operadores `>`, `<`, `>=`, `<=`, `==`, `!=`, y operadores lógicos `NOT`, `AND` y `OR`, con esa precedencia. Se pueden usar paréntesis. Las palabras reservadas no distinguen mayúsculas de minúsculas.

Las acciones son `MOVER BASE número;`, `MOVER BRAZO número;`, `ABRIR PINZA;` y `CERRAR PINZA;`. Una sentencia condicional usa `IF condición { ... }`, opcionalmente seguida de `ELSE { ... }` o `ELSE IF condición { ... }`. Los bloques pueden estar vacíos y las acciones terminan en punto y coma.

```text
WHEN peso > 5 THEN {
  IF peso < 10 { MOVER BASE 60; }
  ELSE { CERRAR PINZA; }
}
```

## Pruebas

```bash
python3 pruebas.py
python3 verificador_ll1.py
```

El primer comando ejecuta las comprobaciones del núcleo y de la interfaz, incluidos los 27 casos del informe. Requiere `main.tex`, desde el que se leen las entradas de esos casos, y devuelve un código distinto de cero si alguna prueba falla. El segundo calcula los conjuntos y la tabla LL(1) como comprobación auxiliar.

## Archivos principales

- `lexico.py`: tokens y errores léxicos.
- `parser.py`: análisis predictivo y errores sintácticos.
- `arbol.py`: nodos e impresión del AST.
- `main.py`: interfaz de terminal.
- `pruebas.py` y `verificaciones/`: pruebas automatizadas.
- `ejemplos/`: entradas válidas e inválidas.
- `main.tex` y `figuras/`: fuente y recursos del informe.
