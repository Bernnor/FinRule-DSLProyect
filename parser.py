"""
Módulo parser.py (Analizador Léxico y Sintáctico)
=================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo implementa el analizador sintáctico para FinRule DSL utilizando la
librería Lark. Procesa la sintaxis concreta EBNF definida en el documento de
especificación y traduce el código fuente a las estructuras nativas de datos
definidas en ast_models.py mediante el patrón Transformer.
"""

from typing import Any, Union
from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError, UnexpectedInput, UnexpectedToken, UnexpectedCharacters

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


# Gramática formal EBNF de FinRule DSL expresada en formato Lark LALR(1)
FINRULE_GRAMMAR = r'''
    start: programa

    programa: "politica" CADENA "version" CADENA "{" regla+ defecto "}"

    regla: "regla" CADENA "prioridad" ENTERO "cuando" expresion "entonces" accion ";"

    defecto: "defecto" accion ";"

    ?expresion: disyuncion

    ?disyuncion: conjuncion ("o" conjuncion)* -> disyuncion

    ?conjuncion: negacion ("y" negacion)* -> conjuncion

    ?negacion: "no" negacion -> negacion
             | primaria

    ?primaria: comparacion
             | "(" expresion ")"

    comparacion: IDENTIFICADOR OPERADOR literal

    OPERADOR: "==" | "!=" | ">=" | "<=" | ">" | "<"

    accion: TIPO_ACCION "(" CADENA ")"
    TIPO_ACCION: "aprobar" | "rechazar" | "revision"

    ?literal: DECIMAL -> decimal
            | ENTERO -> entero
            | BOOLEANO -> booleano
            | CADENA -> cadena

    BOOLEANO: "verdadero" | "falso"
    DECIMAL: /[0-9]+\.[0-9]+/
    ENTERO: /[0-9]+/
    IDENTIFICADOR: /[a-zA-Z_][a-zA-Z0-9_]*/
    CADENA: /"[^"\r\n]*"/

    %import common.WS
    %ignore WS

    COMMENT: /\/\/[^\n]*/
    %ignore COMMENT
'''


class FinRuleSyntaxError(Exception):
    """Excepción lanzada cuando el código fuente no respeta la gramática formal EBNF."""
    def __init__(self, mensaje: str, linea: int = 0, columna: int = 0):
        super().__init__(f"Error sintáctico en línea {linea}, columna {columna}: {mensaje}")
        self.linea = linea
        self.columna = columna


@v_args(inline=True)
class FinRuleTransformer(Transformer):
    """
    Transformador sintáctico que mapea los nodos del Parse Tree de Lark
    a los nodos de dominio del Árbol de Sintaxis Abstracta (AST) de ast_models.py.
    """

    def CADENA(self, token) -> str:
        # Remueve las comillas dobles delimitadoras
        return str(token)[1:-1]

    def ENTERO(self, token) -> int:
        return int(token)

    def DECIMAL(self, token) -> float:
        return float(token)

    def booleano(self, token) -> bool:
        return str(token) == "verdadero"

    def decimal(self, token) -> float:
        return float(token)

    def entero(self, token) -> int:
        return int(token)

    def cadena(self, token) -> str:
        return str(token)[1:-1]

    def IDENTIFICADOR(self, token) -> str:
        return str(token)

    def OPERADOR(self, token) -> str:
        return str(token)

    def TIPO_ACCION(self, token) -> str:
        return str(token)

    def comparacion(self, campo: str, operador: str, valor: Any) -> Comparacion:
        return Comparacion(campo=str(campo), operador=str(operador), valor=valor)

    def negacion(self, condicion: Expresion) -> Negacion:
        return Negacion(condicion=condicion)

    def conjuncion(self, *items: Expresion) -> Union[Expresion, Conjuncion]:
        if len(items) == 1:
            return items[0]
        return Conjuncion(condiciones=list(items))

    def disyuncion(self, *items: Expresion) -> Union[Expresion, Disyuncion]:
        if len(items) == 1:
            return items[0]
        return Disyuncion(condiciones=list(items))

    def accion(self, tipo: str, motivo: str) -> Accion:
        return Accion(tipo=str(tipo), motivo=str(motivo))

    def regla(self, nombre: str, prioridad: int, condicion: Expresion, accion: Accion) -> Regla:
        return Regla(nombre=str(nombre), prioridad=int(prioridad), condicion=condicion, accion=accion)

    def defecto(self, accion: Accion) -> Defecto:
        return Defecto(accion=accion)

    def programa(self, nombre: str, version: str, *elementos) -> Politica:
        reglas = [elem for elem in elementos if isinstance(elem, Regla)]
        defecto = next(elem for elem in elementos if isinstance(elem, Defecto))
        return Politica(nombre=str(nombre), version=str(version), reglas=reglas, defecto=defecto)

    def start(self, item: Politica) -> Politica:
        return item


class FinRuleParser:
    """
    Fachada del analizador sintáctico. Compila la gramática y expone
    métodos de parseo para texto y archivos.
    """

    def __init__(self):
        self._lark = Lark(
            FINRULE_GRAMMAR,
            parser="lalr",
            transformer=FinRuleTransformer()
        )

    def parse(self, codigo_fuente: str) -> Politica:
        """
        Analiza sintácticamente una cadena de texto en FinRule DSL
        y retorna el nodo raíz Politica del AST.
        
        Lanza:
            FinRuleSyntaxError: Si existe un token inesperado o violación a la EBNF.
        """
        try:
            resultado = self._lark.parse(codigo_fuente)
            return resultado
        except UnexpectedToken as e:
            raise FinRuleSyntaxError(
                f"Token inesperado '{e.token.value}' (se esperaba uno de: {list(e.expected)})",
                linea=e.line,
                columna=e.column,
            ) from e
        except UnexpectedCharacters as e:
            raise FinRuleSyntaxError(
                f"Carácter no reconocido '{e.char}'",
                linea=e.line,
                columna=e.column,
            ) from e
        except UnexpectedInput as e:
            raise FinRuleSyntaxError(
                f"Entrada inesperada en el código",
                linea=getattr(e, 'line', 0),
                columna=getattr(e, 'column', 0),
            ) from e
        except LarkError as e:
            raise FinRuleSyntaxError(str(e)) from e

    def parse_file(self, filepath: str) -> Politica:
        """
        Lee un archivo .finrule con codificación UTF-8 y genera el AST.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            contenido = f.read()
        return self.parse(contenido)


# Instancia singleton precompilada para uso directo
_default_parser = FinRuleParser()


def parse_finrule(codigo: str) -> Politica:
    """Función de utilidad para parsear código FinRule directamente."""
    return _default_parser.parse(codigo)


def parse_finrule_file(filepath: str) -> Politica:
    """Función de utilidad para parsear un archivo FinRule directamente."""
    return _default_parser.parse_file(filepath)
