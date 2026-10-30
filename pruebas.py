"""Ejecuta los casos del informe y las pruebas de integración."""
import unittest

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover('verificaciones', pattern='test_*.py')
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if resultado.wasSuccessful() else 1)
