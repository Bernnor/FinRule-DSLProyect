"""
Módulo interpreter.py (Motor de Ejecución - Patrón Visitor)
============================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo implementa el intérprete dinámico de FinRule DSL aplicando
el patrón de diseño Gang of Four (GoF) "Visitor". Separa de forma estricta
la lógica de negocio y las reglas de evaluación de las definiciones puras
de los datos (nodos del AST en ast_models.py).

Características clave:
- Ordenamiento dinámico de reglas por prioridad de mayor a menor.
- Cortocircuito lógico (short-circuit evaluation) en conjunciones y disyunciones.
- Ejecución con resolución determinista (first-match policy).
- Cláusula por defecto ante expedientes sin coincidencia explícita.
- Generación de trazabilidad y registros de auditoría regulatoria.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

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
    Decision,
    RegistroAuditoria,
)


class FinRuleRuntimeError(Exception):
    """Excepción lanzada ante fallos durante la evaluación dinámica del expediente."""
    pass


class ASTVisitor(ABC):
    """
    Interfaz abstracta del patrón Visitor para recorrer y evaluar
    los nodos de expresiones del AST sin contaminar su definición de dominio.
    """

    @abstractmethod
    def visit_comparacion(self, node: Comparacion, context: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def visit_conjuncion(self, node: Conjuncion, context: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def visit_disyuncion(self, node: Disyuncion, context: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def visit_negacion(self, node: Negacion, context: Dict[str, Any]) -> bool:
        pass


class EvaluadorCondicionesVisitor(ASTVisitor):
    """
    Visitor concreto encargado de evaluar el valor de verdad de las expresiones
    lógicas y comparaciones relacionales sobre los datos del expediente bancario.
    
    Implementa optimización de cortocircuito lógico (short-circuit evaluation):
    - Conjunción ('y'): se detiene en el primer falso.
    - Disyunción ('o'): se detiene en el primer verdadero.
    """

    def __init__(self):
        # Historial de evaluaciones para auditoría y observabilidad
        self.trazas_evaluacion: List[str] = []

    def visit(self, node: Expresion, context: Dict[str, Any]) -> bool:
        """Método despachador polimórfico del Visitor."""
        if isinstance(node, Comparacion):
            return self.visit_comparacion(node, context)
        elif isinstance(node, Conjuncion):
            return self.visit_conjuncion(node, context)
        elif isinstance(node, Disyuncion):
            return self.visit_disyuncion(node, context)
        elif isinstance(node, Negacion):
            return self.visit_negacion(node, context)
        else:
            raise FinRuleRuntimeError(f"Tipo de nodo AST no soportado por el evaluador: {type(node)}")

    def visit_comparacion(self, node: Comparacion, context: Dict[str, Any]) -> bool:
        """
        Evalúa una comparación relacional entre el valor contenido en el expediente
        y el valor literal especificado en la regla.
        """
        campo = node.campo
        operador = node.operador
        valor_regla = node.valor

        if campo not in context:
            raise FinRuleRuntimeError(
                f"El expediente no contiene el atributo requerido '{campo}' para evaluar la condición."
            )

        valor_expediente = context[campo]
        resultado = False

        if operador == "==":
            resultado = (valor_expediente == valor_regla)
        elif operador == "!=":
            resultado = (valor_expediente != valor_regla)
        elif operador == ">":
            resultado = (valor_expediente > valor_regla)
        elif operador == "<":
            resultado = (valor_expediente < valor_regla)
        elif operador == ">=":
            resultado = (valor_expediente >= valor_regla)
        elif operador == "<=":
            resultado = (valor_expediente <= valor_regla)
        else:
            raise FinRuleRuntimeError(f"Operador de comparación desconocido '{operador}'.")

        self.trazas_evaluacion.append(
            f"Evaluar: {campo}({valor_expediente}) {operador} {valor_regla} -> {resultado}"
        )
        return resultado

    def visit_conjuncion(self, node: Conjuncion, context: Dict[str, Any]) -> bool:
        """
        Evalúa una conjunción lógica ('y') aplicando cortocircuito:
        Si alguna condición resulta falsa, se detiene la evaluación de inmediato.
        """
        for i, sub_condicion in enumerate(node.condiciones):
            resultado = self.visit(sub_condicion, context)
            if not resultado:
                self.trazas_evaluacion.append(
                    f"Cortocircuito 'y': Condición #{i+1} fue Falsa; evaluacion detenida."
                )
                return False
        return True

    def visit_disyuncion(self, node: Disyuncion, context: Dict[str, Any]) -> bool:
        """
        Evalúa una disyunción lógica ('o') aplicando cortocircuito:
        Si alguna condición resulta verdadera, se detiene la evaluación de inmediato.
        """
        for i, sub_condicion in enumerate(node.condiciones):
            resultado = self.visit(sub_condicion, context)
            if resultado:
                self.trazas_evaluacion.append(
                    f"Cortocircuito 'o': Condición #{i+1} fue Verdadera; evaluacion detenida."
                )
                return True
        return False

    def visit_negacion(self, node: Negacion, context: Dict[str, Any]) -> bool:
        """Evalúa una negación lógica ('no')."""
        resultado = self.visit(node.condicion, context)
        return not resultado


class FinRuleInterpreter:
    """
    Motor de ejecución de FinRule DSL.
    
    Responsabilidades:
    - Recibir el AST de una política validada.
    - Ordenar las reglas por su prioridad (de mayor a menor).
    - Evaluar secuencialmente las reglas sobre un expediente crediticio simulado.
    - Retornar la recomendación de la primera regla válida (política first-match).
    - Disparar la acción por defecto si ninguna regla coincide.
    """

    def __init__(self, politica: Politica):
        self.politica = politica
        # Ordenación estricta de mayor a menor prioridad
        self.reglas_ordenadas: List[Regla] = sorted(
            politica.reglas,
            key=lambda r: r.prioridad,
            reverse=True
        )
        self.evaluador = EvaluadorCondicionesVisitor()

    def evaluar(self, expediente: Dict[str, Any]) -> Decision:
        """
        Evalúa un expediente crediticio simulado contra las reglas de la política.
        Retorna la Decision correspondiente a la primera regla cumplida o la acción por defecto.
        """
        self.evaluador.trazas_evaluacion.clear()

        for regla in self.reglas_ordenadas:
            condicion_cumplida = self.evaluador.visit(regla.condicion, expediente)
            if condicion_cumplida:
                return Decision(
                    tipo=regla.accion.tipo,
                    motivo=regla.accion.motivo,
                    regla_determinante=regla.nombre,
                )

        # Caso por defecto: Ninguna regla explícita fue satisfecha
        return Decision(
            tipo=self.politica.defecto.accion.tipo,
            motivo=self.politica.defecto.accion.motivo,
            regla_determinante="DEFECTO",
        )

    def evaluar_con_auditoria(self, expediente: Dict[str, Any]) -> RegistroAuditoria:
        """
        Evalúa el expediente y genera un registro completo de auditoría
        incluyendo la lista de reglas analizadas y la justificación regulatoria.
        """
        reglas_evaluadas: List[str] = []
        self.evaluador.trazas_evaluacion.clear()
        decision_final: Optional[Decision] = None

        for regla in self.reglas_ordenadas:
            reglas_evaluadas.append(regla.nombre)
            condicion_cumplida = self.evaluador.visit(regla.condicion, expediente)
            if condicion_cumplida:
                decision_final = Decision(
                    tipo=regla.accion.tipo,
                    motivo=regla.accion.motivo,
                    regla_determinante=regla.nombre,
                )
                break

        if decision_final is None:
            reglas_evaluadas.append("DEFECTO")
            decision_final = Decision(
                tipo=self.politica.defecto.accion.tipo,
                motivo=self.politica.defecto.accion.motivo,
                regla_determinante="DEFECTO",
            )

        return RegistroAuditoria(
            politica=self.politica.nombre,
            version=self.politica.version,
            decision=decision_final,
            expediente_evaluado=dict(expediente),
            reglas_evaluadas=reglas_evaluadas,
        )


def interpretar_politica(politica: Politica, expediente: Dict[str, Any]) -> Decision:
    """Función de conveniencia para evaluar directamente una política sobre un expediente."""
    interprete = FinRuleInterpreter(politica)
    return interprete.evaluar(expediente)
