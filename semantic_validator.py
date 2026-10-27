"""
Módulo semantic_validator.py (Semántica Estática)
=================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo implementa la capa de verificación y validación semántica estática
sobre el AST generado por el parser, antes de que el motor de ejecución intente
evaluar las reglas. Aplica las restricciones de negocio y tipado definidas
en la sección de Diseño Semántico del documento.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from ast_models import (
    Politica,
    Regla,
    Expresion,
    Comparacion,
    Conjuncion,
    Disyuncion,
    Negacion,
    Accion,
    Defecto,
)


class FinRuleSemanticError(Exception):
    """Excepción base para violaciones de las reglas semánticas estáticas."""
    pass


class UndefinedAttributeError(FinRuleSemanticError):
    """Lanzada cuando una regla referencia un campo ausente en el diccionario."""
    pass


class TypeMismatchError(FinRuleSemanticError):
    """Lanzada cuando los tipos de datos o los operadores de una comparación son incompatibles."""
    pass


class DuplicateRuleError(FinRuleSemanticError):
    """Lanzada cuando existen reglas con nombres duplicados dentro de la misma política."""
    pass


class InvalidConstraintError(FinRuleSemanticError):
    """Lanzada cuando un valor literal viola las restricciones de rango del diccionario."""
    pass


@dataclass
class DefinicionAtributo:
    """Metadatos de un atributo en el diccionario de datos del expediente."""
    tipo_esperado: type
    nombre_tipo: str
    operadores_permitidos: Set[str]
    descripcion: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None


# Diccionario formal de atributos del expediente simulado (Tabla VII de la especificación)
DICCIONARIO_ATRIBUTOS: Dict[str, DefinicionAtributo] = {
    "alerta_fraude": DefinicionAtributo(
        tipo_esperado=bool,
        nombre_tipo="booleano",
        operadores_permitidos={"==", "!="},
        descripcion="Señal externa de posible anomalía",
    ),
    "identidad_verificada": DefinicionAtributo(
        tipo_esperado=bool,
        nombre_tipo="booleano",
        operadores_permitidos={"==", "!="},
        descripcion="Resultado recibido de un sistema de validación de identidad",
    ),
    "documentos_verificados": DefinicionAtributo(
        tipo_esperado=bool,
        nombre_tipo="booleano",
        operadores_permitidos={"==", "!="},
        descripcion="Estado agregado de revisión documental",
    ),
    "dias_mora_vigente": DefinicionAtributo(
        tipo_esperado=int,
        nombre_tipo="entero",
        operadores_permitidos={"==", "!=", ">", "<", ">=", "<="},
        descripcion="Número de días de obligaciones vencidas vigente",
        min_val=0,
    ),
    "ratio_cuota_ingreso": DefinicionAtributo(
        tipo_esperado=float,
        nombre_tipo="decimal",
        operadores_permitidos={"==", "!=", ">", "<", ">=", "<="},
        descripcion="Relación entre carga mensual de deuda e ingreso mensual verificado",
        min_val=0.0,
    ),
    "puntaje_riesgo": DefinicionAtributo(
        tipo_esperado=int,
        nombre_tipo="entero",
        operadores_permitidos={"==", "!=", ">", "<", ">=", "<="},
        descripcion="Escala simulada de puntuación interna de 0 a 1000",
        min_val=0,
        max_val=1000,
    ),
    "monto_solicitado": DefinicionAtributo(
        tipo_esperado=float,
        nombre_tipo="decimal",
        operadores_permitidos={"==", "!=", ">", "<", ">=", "<="},
        descripcion="Monto solicitado para el crédito de consumo",
        min_val=0.01,
    ),
    "producto": DefinicionAtributo(
        tipo_esperado=str,
        nombre_tipo="texto",
        operadores_permitidos={"==", "!="},
        descripcion="Tipo o línea de crédito solicitada (ej. 'consumo')",
    ),
}

ACCIONES_PERMITIDAS: Set[str] = {"aprobar", "rechazar", "revision"}


@dataclass
class ResultadoValidacion:
    """Contenedor de los resultados arrojados por el análisis semántico."""
    es_valido: bool
    errores: List[str]
    advertencias: List[str]


class SemanticValidator:
    """
    Analizador de Semántica Estática.
    Recorre el AST verificando tipos, operadores, unicidad de identificadores,
    existencia de atributos y consistencia de motivos de decisión.
    """

    def __init__(self, diccionario_atributos: Optional[Dict[str, DefinicionAtributo]] = None):
        self.diccionario = diccionario_atributos or DICCIONARIO_ATRIBUTOS
        self.errores: List[str] = []
        self.advertencias: List[str] = []

    def validar(self, politica: Politica) -> ResultadoValidacion:
        """
        Punto de entrada principal para validar una política completa.
        Retorna un ResultadoValidacion con el detalle de errores y advertencias.
        Lanza FinRuleSemanticError ante el primer error crítico si se invoca validar_estricto.
        """
        self.errores.clear()
        self.advertencias.clear()

        # 1. Validación de nombre y versión de la política
        if not politica.nombre or not politica.nombre.strip():
            self.errores.append("La política debe tener un nombre no vacío.")
        if not politica.version or not politica.version.strip():
            self.errores.append("La política debe tener una versión no vacía.")

        # 2. Validación de reglas y unicidad de identificadores
        if not politica.reglas:
            self.errores.append("La política debe contener al menos una regla.")

        nombres_vistos: Set[str] = set()
        prioridades_vistas: Dict[int, str] = {}

        for regla in politica.reglas:
            # Unicidad de nombres de regla
            if regla.nombre in nombres_vistos:
                self.errores.append(
                    f"Identificador de regla duplicado: '{regla.nombre}'. "
                    "Cada regla debe tener un nombre único para trazabilidad."
                )
            else:
                nombres_vistos.add(regla.nombre)

            # Advertencia sobre prioridades compartidas
            if regla.prioridad in prioridades_vistas:
                otra_regla = prioridades_vistas[regla.prioridad]
                self.advertencias.append(
                    f"Prioridad compartida: La regla '{regla.nombre}' tiene la misma prioridad ({regla.prioridad}) "
                    f"que '{otra_regla}'. Esto puede causar comportamiento no determinista."
                )
            else:
                prioridades_vistas[regla.prioridad] = regla.nombre

            # Validación de la acción de la regla
            self._validar_accion(regla.accion, f"Regla '{regla.nombre}'")

            # Validación de la expresión condicional de la regla
            self._validar_expresion(regla.condicion, regla.nombre)

        # 3. Validación de la cláusula por defecto
        if not politica.defecto or not politica.defecto.accion:
            self.errores.append("La política debe definir una cláusula obligatoria 'defecto'.")
        else:
            self._validar_accion(politica.defecto.accion, "Cláusula por defecto")

        return ResultadoValidacion(
            es_valido=len(self.errores) == 0,
            errores=list(self.errores),
            advertencias=list(self.advertencias),
        )

    def validar_estricto(self, politica: Politica) -> None:
        """
        Ejecuta la validación y lanza excepciones específicas inmediatamente
        si se detecta alguna infracción semántica.
        """
        resultado = self.validar(politica)
        if not resultado.es_valido:
            # Priorizar excepciones específicas
            primer_error = resultado.errores[0]
            if "duplicado" in primer_error:
                raise DuplicateRuleError(primer_error)
            elif "no declarado" in primer_error:
                raise UndefinedAttributeError(primer_error)
            elif "incompatible" in primer_error or "no es válido" in primer_error:
                raise TypeMismatchError(primer_error)
            elif "rango" in primer_error or "negativo" in primer_error:
                raise InvalidConstraintError(primer_error)
            else:
                raise FinRuleSemanticError(primer_error)

    def _validar_accion(self, accion: Accion, contexto: str) -> None:
        """Verifica que el tipo de acción sea válido y el motivo no esté vacío."""
        if accion.tipo not in ACCIONES_PERMITIDAS:
            self.errores.append(
                f"{contexto}: Tipo de acción inválido '{accion.tipo}'. "
                f"Debe ser uno de: {sorted(ACCIONES_PERMITIDAS)}."
            )
        if not accion.motivo or not accion.motivo.strip():
            self.errores.append(
                f"{contexto}: El motivo de la acción no puede estar vacío."
            )

    def _validar_expresion(self, expr: Expresion, nombre_regla: str) -> None:
        """Recorre recursivamente los nodos de una expresión."""
        if isinstance(expr, Comparacion):
            self._validar_comparacion(expr, nombre_regla)
        elif isinstance(expr, Conjuncion):
            for c in expr.condiciones:
                self._validar_expresion(c, nombre_regla)
        elif isinstance(expr, Disyuncion):
            for c in expr.condiciones:
                self._validar_expresion(c, nombre_regla)
        elif isinstance(expr, Negacion):
            self._validar_expresion(expr.condicion, nombre_regla)
        else:
            self.errores.append(f"Regla '{nombre_regla}': Nodo de expresión desconocido '{type(expr)}'.")

    def _validar_comparacion(self, comp: Comparacion, nombre_regla: str) -> None:
        """
        Valida que el campo exista en el diccionario y que el operador y el valor
        literal sean estrictamente compatibles con la definición del tipo.
        """
        campo = comp.campo
        operador = comp.operador
        valor = comp.valor

        # Verificación 1: Existencia en el Diccionario
        if campo not in self.diccionario:
            self.errores.append(
                f"Regla '{nombre_regla}': Atributo no declarado en el diccionario: '{campo}'."
            )
            return

        def_attr = self.diccionario[campo]

        # Verificación 2: Operador permitido para este tipo
        if operador not in def_attr.operadores_permitidos:
            self.errores.append(
                f"Regla '{nombre_regla}': Operador '{operador}' no es válido para el campo "
                f"'{campo}' de tipo {def_attr.nombre_tipo}. "
                f"Operadores permitidos: {sorted(def_attr.operadores_permitidos)}."
            )

        # Verificación 3: Compatibilidad de tipos
        # En Python, isinstance(True, int) es True; por tanto, verificamos bool explícitamente primero.
        if def_attr.tipo_esperado is bool:
            if not isinstance(valor, bool):
                self.errores.append(
                    f"Regla '{nombre_regla}': Tipo incompatible para '{campo}'. "
                    f"Se esperaba booleano (verdadero/falso) pero se recibió '{type(valor).__name__}' ({valor})."
                )
        elif def_attr.tipo_esperado is int:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                self.errores.append(
                    f"Regla '{nombre_regla}': Tipo incompatible para '{campo}'. "
                    f"Se esperaba entero pero se recibió '{type(valor).__name__}' ({valor})."
                )
            elif isinstance(valor, float) and not valor.is_integer():
                self.errores.append(
                    f"Regla '{nombre_regla}': Campo '{campo}' es de tipo entero, "
                    f"no debe compararse con decimal fraccionario '{valor}'."
                )
        elif def_attr.tipo_esperado is float:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                self.errores.append(
                    f"Regla '{nombre_regla}': Tipo incompatible para '{campo}'. "
                    f"Se esperaba número decimal pero se recibió '{type(valor).__name__}' ({valor})."
                )
        elif def_attr.tipo_esperado is str:
            if not isinstance(valor, str):
                self.errores.append(
                    f"Regla '{nombre_regla}': Tipo incompatible para '{campo}'. "
                    f"Se esperaba texto entre comillas pero se recibió '{type(valor).__name__}' ({valor})."
                )

        # Verificación 4: Restricciones de dominio / rango numérico
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            if def_attr.min_val is not None and valor < def_attr.min_val:
                self.errores.append(
                    f"Regla '{nombre_regla}': El valor {valor} para '{campo}' viola la "
                    f"restricción de valor mínimo ({def_attr.min_val})."
                )
            if def_attr.max_val is not None and valor > def_attr.max_val:
                self.errores.append(
                    f"Regla '{nombre_regla}': El valor {valor} para '{campo}' viola la "
                    f"restricción de valor máximo ({def_attr.max_val})."
                )


def validar_politica(politica: Politica, estricto: bool = True) -> ResultadoValidacion:
    """Función de utilidad para validar una política con la configuración predeterminada."""
    validador = SemanticValidator()
    if estricto:
        validador.validar_estricto(politica)
    return validador.validar(politica)
