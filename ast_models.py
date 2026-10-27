"""
Módulo ast_models.py (Árbol de Sintaxis Abstracta - AST)
=========================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo define las clases del Árbol de Sintaxis Abstracta (AST) que
representan los conceptos puros del metamodelo conceptual de FinRule DSL,
utilizando dataclasses de Python para garantizar inmutabilidad, limpieza y
desacoplamiento total de la sintaxis concreta o de librerías externas.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


@dataclass
class NodoAST(ABC):
    """
    Clase base abstracta para todos los nodos del Árbol de Sintaxis Abstracta.
    Permite tipado uniforme y soporte para el patrón de diseño Visitor.
    """
    pass


@dataclass
class Expresion(NodoAST, ABC):
    """
    Clase base abstracta para cualquier expresión lógica o relacional en FinRule.
    """
    pass


@dataclass
class Comparacion(Expresion):
    """
    Nodo de comparación relacional entre un atributo del expediente y un literal.
    
    Atributos:
        campo (str): Identificador del atributo en el expediente (ej. 'alerta_fraude').
        operador (str): Operador relacional ('==', '!=', '>', '<', '>=', '<=').
        valor (Any): Valor literal de comparación (booleano, entero, decimal o texto).
    """
    campo: str
    operador: str
    valor: Any

    def __repr__(self) -> str:
        val_str = f'"{self.valor}"' if isinstance(self.valor, str) else str(self.valor)
        return f"Comparacion({self.campo} {self.operador} {val_str})"


@dataclass
class Conjuncion(Expresion):
    """
    Nodo de conjunción lógica ('y').
    Agrupa una lista de subexpresiones que deben cumplirse conjuntamente.
    Soporta evaluación con cortocircuito lógico.
    """
    condiciones: List[Expresion]

    def __repr__(self) -> str:
        return f"Conjuncion({' y '.join(repr(c) for c in self.condiciones)})"


@dataclass
class Disyuncion(Expresion):
    """
    Nodo de disyunción lógica ('o').
    Agrupa una lista de subexpresiones donde basta que una se cumpla.
    Soporta evaluación con cortocircuito lógico.
    """
    condiciones: List[Expresion]

    def __repr__(self) -> str:
        return f"Disyuncion({' o '.join(repr(c) for c in self.condiciones)})"


@dataclass
class Negacion(Expresion):
    """
    Nodo de negación lógica ('no').
    Invierte el valor de verdad de la subexpresión contenida.
    """
    condicion: Expresion

    def __repr__(self) -> str:
        return f"Negacion(no {repr(self.condicion)})"


@dataclass
class Accion(NodoAST):
    """
    Nodo que representa la recomendación o acción de negocio a ejecutar.
    
    Atributos:
        tipo (str): Naturaleza de la decisión ('aprobar', 'rechazar', 'revision').
        motivo (str): Código nemotécnico trazable que justifica la recomendación
                      (ej. 'ALERTA_OPERACION_SOSPECHOSA', 'ELEGIBLE_PRELIMINAR').
    """
    tipo: str
    motivo: str

    def __repr__(self) -> str:
        return f"Accion({self.tipo}('{self.motivo}'))"


@dataclass
class Regla(NodoAST):
    """
    Nodo que representa una regla de negocio crediticia o antifraude.
    
    Atributos:
        nombre (str): Identificador único de la regla (ej. 'R01_FRAUDE').
        prioridad (int): Peso numérico para ordenación (mayor valor = mayor prioridad).
        condicion (Expresion): Condición booleana a evaluar sobre el expediente.
        accion (Accion): Decisión recomendada cuando la condición se satisface.
    """
    nombre: str
    prioridad: int
    condicion: Expresion
    accion: Accion

    def __repr__(self) -> str:
        return f"Regla(nombre='{self.nombre}', prioridad={self.prioridad}, accion={self.accion})"


@dataclass
class Defecto(NodoAST):
    """
    Nodo que encapsula la acción por defecto obligatoria para expedientes
    que no coinciden con ninguna de las reglas explícitas de la política.
    """
    accion: Accion

    def __repr__(self) -> str:
        return f"Defecto({self.accion})"


@dataclass
class Politica(NodoAST):
    """
    Nodo raíz del Árbol de Sintaxis Abstracta (AST).
    Representa una política integral versionada que contiene un conjunto de reglas
    y una cláusula por defecto.
    
    Atributos:
        nombre (str): Nombre formal de la política (ej. 'CREDITO_CONSUMO').
        version (str): Versión semántica de la política (ej. '1.0').
        reglas (List[Regla]): Colección de reglas de negocio que componen la política.
        defecto (Defecto): Acción por defecto en caso de no coincidencia.
    """
    nombre: str
    version: str
    reglas: List[Regla]
    defecto: Defecto

    def __repr__(self) -> str:
        return f"Politica(nombre='{self.nombre}', version='{self.version}', total_reglas={len(self.reglas)})"


@dataclass
class Decision(NodoAST):
    """
    Objeto de valor que representa el resultado final de la evaluación de un expediente.
    
    Atributos:
        tipo (str): 'aprobar' | 'rechazar' | 'revision'
        motivo (str): Motivo de negocio que justifica la decisión.
        regla_determinante (Optional[str]): Nombre de la regla que disparó la acción,
                                            o 'DEFECTO' si se ejecutó la cláusula por defecto.
    """
    tipo: str
    motivo: str
    regla_determinante: Optional[str] = None

    def __repr__(self) -> str:
        return f"Decision(tipo='{self.tipo}', motivo='{self.motivo}', regla='{self.regla_determinante}')"


@dataclass
class RegistroAuditoria(NodoAST):
    """
    Entidad de auditoría para trazabilidad regulatoria y cumplimiento bancario.
    Conserva la evidencia completa del proceso de decisión sobre una solicitud.
    """
    politica: str
    version: str
    decision: Decision
    expediente_evaluado: dict
    reglas_evaluadas: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
