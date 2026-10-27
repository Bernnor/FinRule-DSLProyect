"""
Módulo code_generator.py (Compilador / Generador de Código Python)
==================================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo implementa la funcionalidad descrita en la Sección VI.B del documento:
Generación de código Python nativo a partir del AST de FinRule DSL.
Traduce las reglas ordenadas por prioridad en una cadena de estructuras
'if / elif / else' altamente optimizadas para ejecución en entornos de alta
concurrencia sin sobrecarga de interpretación en tiempo real.
"""

from typing import List
from ast_models import (
    Politica,
    Regla,
    Expresion,
    Comparacion,
    Conjuncion,
    Disyuncion,
    Negacion,
    Accion,
)


class PythonCodeGenerator:
    """
    Compilador de AST FinRule a código fuente Python autónomo.
    """

    def __init__(self, politica: Politica):
        self.politica = politica
        # Ordenación por prioridad descendente
        self.reglas_ordenadas: List[Regla] = sorted(
            politica.reglas,
            key=lambda r: r.prioridad,
            reverse=True
        )

    def generar_codigo(self) -> str:
        """Genera el script Python completo como cadena de texto."""
        lineas = [
            '"""',
            f'Código Python autogenerado a partir de FinRule DSL',
            f'Política: {self.politica.nombre} (Versión: {self.politica.version})',
            'Compilado para entornos de alta concurrencia y microservicios.',
            '"""',
            '',
            'from typing import Any, Dict',
            '',
            '',
            'def evaluar_expediente(expediente: Dict[str, Any]) -> Dict[str, str]:',
            '    """',
            f'    Evalúa el expediente crediticio bajo la política {self.politica.nombre}.',
            '    Retorna un diccionario con tipo, motivo y regla_determinante.',
            '    """',
        ]

        primera = True
        for regla in self.reglas_ordenadas:
            prefijo = "if" if primera else "elif"
            primera = False
            cond_str = self._traducir_expresion(regla.condicion)
            lineas.append(f"    # Regla: {regla.nombre} (Prioridad: {regla.prioridad})")
            lineas.append(f"    {prefijo} {cond_str}:")
            lineas.append(f"        return {{")
            lineas.append(f'            "tipo": "{regla.accion.tipo}",')
            lineas.append(f'            "motivo": "{regla.accion.motivo}",')
            lineas.append(f'            "regla_determinante": "{regla.nombre}",')
            lineas.append(f"        }}")
            lineas.append("")

        # Cláusula por defecto
        defecto = self.politica.defecto.accion
        lineas.append("    # Cláusula por defecto (Fallback seguro)")
        lineas.append("    else:")
        lineas.append(f"        return {{")
        lineas.append(f'            "tipo": "{defecto.tipo}",')
        lineas.append(f'            "motivo": "{defecto.motivo}",')
        lineas.append(f'            "regla_determinante": "DEFECTO",')
        lineas.append(f"        }}")
        lineas.append("")

        return "\n".join(lineas)

    def _traducir_expresion(self, expr: Expresion) -> str:
        """Traduce recursivamente un nodo de expresión a expresión condicional de Python."""
        if isinstance(expr, Comparacion):
            val_repr = repr(expr.valor)
            # En Python, el acceso al diccionario se expresa con expediente.get(...)
            return f"(expediente.get('{expr.campo}') {expr.operador} {val_repr})"
        elif isinstance(expr, Conjuncion):
            partes = [self._traducir_expresion(c) for c in expr.condiciones]
            return f"({' and '.join(partes)})"
        elif isinstance(expr, Disyuncion):
            partes = [self._traducir_expresion(c) for c in expr.condiciones]
            return f"({' or '.join(partes)})"
        elif isinstance(expr, Negacion):
            sub = self._traducir_expresion(expr.condicion)
            return f"(not {sub})"
        else:
            raise ValueError(f"Expresión no soportada para compilación: {type(expr)}")


def compilar_a_python(politica: Politica) -> str:
    """Función de utilidad para compilar un AST de FinRule a código fuente Python."""
    generador = PythonCodeGenerator(politica)
    return generador.generar_codigo()
