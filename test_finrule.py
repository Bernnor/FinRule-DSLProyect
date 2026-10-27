"""
Módulo test_finrule.py (Pruebas Automatizadas con pytest)
==========================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este módulo implementa la suite completa de pruebas unitarias y de integración
utilizando el framework pytest. Comprueba de forma asertiva los 5 escenarios
sintéticos de prueba de concepto (C1 a C5) detallados en la Tabla VIII del
documento de especificación, así como las restricciones semánticas estáticas,
la ordenación por prioridad y el cortocircuito lógico.
"""

import pytest

from ast_models import Politica, Decision, Comparacion, Conjuncion, Disyuncion
from parser import parse_finrule, FinRuleSyntaxError
from semantic_validator import (
    SemanticValidator,
    validar_politica,
    FinRuleSemanticError,
    UndefinedAttributeError,
    TypeMismatchError,
    DuplicateRuleError,
)
from interpreter import FinRuleInterpreter, EvaluadorCondicionesVisitor
from code_generator import compilar_a_python


# Política oficial de crédito de consumo según la sección III.C del documento
CODIGO_POLITICA_OFICIAL = """
politica "CREDITO_CONSUMO" version "1.0" {
  regla "R01_FRAUDE" prioridad 100
    cuando alerta_fraude == verdadero
    entonces revision("ALERTA_OPERACION_SOSPECHOSA");
 
  regla "R02_IDENTIDAD" prioridad 90
    cuando identidad_verificada == falso
    entonces revision("IDENTIDAD_PENDIENTE");
 
  regla "R03_DOCUMENTOS" prioridad 85
    cuando documentos_verificados == falso
    entonces revision("DOCUMENTACION_INCOMPLETA");
 
  regla "R04_MORA_ALTA" prioridad 80
    cuando dias_mora_vigente >= 30
    entonces rechazar("MORA_ELEVADA");
 
  regla "R05_MORA_LEVE" prioridad 75
    cuando dias_mora_vigente > 0
    entonces revision("MORA_PENDIENTE");
 
  regla "R06_ENDEUDAMIENTO" prioridad 70
    cuando ratio_cuota_ingreso > 0.40
    entonces revision("CAPACIDAD_DE_PAGO");
 
  regla "R07_PUNTAJE" prioridad 60
    cuando puntaje_riesgo < 600
    entonces revision("PUNTAJE_PARA_REVISION");
 
  regla "R08_PREAPROBACION" prioridad 10
    cuando alerta_fraude == falso y
           identidad_verificada == verdadero y
           documentos_verificados == verdadero y
           dias_mora_vigente == 0 y
           ratio_cuota_ingreso <= 0.40 y
           puntaje_riesgo >= 600
    entonces aprobar("ELEGIBLE_PRELIMINAR");
 
  defecto revision("CASO_NO_CLASIFICADO");
}
"""


@pytest.fixture(scope="module")
def politica_compilada() -> Politica:
    """Fixture que parsea y valida semánticamente la política oficial una sola vez."""
    politica = parse_finrule(CODIGO_POLITICA_OFICIAL)
    validar_politica(politica, estricto=True)
    return politica


@pytest.fixture(scope="module")
def interprete_oficial(politica_compilada: Politica) -> FinRuleInterpreter:
    """Fixture que inicializa el intérprete con la política oficial compilada."""
    return FinRuleInterpreter(politica_compilada)


# ==============================================================================
# SUITE 1: Los 5 Escenarios Sintéticos de la Especificación (Tabla VIII)
# ==============================================================================

def test_escenario_c1_perfil_elegible(interprete_oficial: FinRuleInterpreter):
    """
    Escenario C1: Perfil elegible
    Datos: Sin alerta, identidad y documentos verificados, mora 0, ratio 0.28, puntaje 710.
    Resultado esperado: Preaprobación técnica ('aprobar', 'ELEGIBLE_PRELIMINAR').
    Regla determinante esperada: 'R08_PREAPROBACION'.
    """
    expediente_c1 = {
        "alerta_fraude": False,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.28,
        "puntaje_riesgo": 710,
        "monto_solicitado": 10000.0,
        "producto": "consumo",
    }

    decision = interprete_oficial.evaluar(expediente_c1)

    assert decision.tipo == "aprobar", f"Se esperaba 'aprobar', se obtuvo '{decision.tipo}'"
    assert decision.motivo == "ELEGIBLE_PRELIMINAR", f"Motivo incorrecto: '{decision.motivo}'"
    assert decision.regla_determinante == "R08_PREAPROBACION"


def test_escenario_c2_alerta_fraude(interprete_oficial: FinRuleInterpreter):
    """
    Escenario C2: Alerta de fraude
    Datos: Alerta de fraude verdadera; restantes datos indiferentes para la primera regla.
    Resultado esperado: Revisión humana ('revision', 'ALERTA_OPERACION_SOSPECHOSA').
    Regla determinante esperada: 'R01_FRAUDE'.
    """
    expediente_c2 = {
        "alerta_fraude": True,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.20,
        "puntaje_riesgo": 850,
        "monto_solicitado": 5000.0,
        "producto": "consumo",
    }

    decision = interprete_oficial.evaluar(expediente_c2)

    assert decision.tipo == "revision"
    assert decision.motivo == "ALERTA_OPERACION_SOSPECHOSA"
    assert decision.regla_determinante == "R01_FRAUDE"


def test_escenario_c3_mora_elevada(interprete_oficial: FinRuleInterpreter):
    """
    Escenario C3: Mora elevada
    Datos: Sin alerta, validaciones completas, mora 45 días.
    Resultado esperado: Recomendación de rechazo ('rechazar', 'MORA_ELEVADA').
    Regla determinante esperada: 'R04_MORA_ALTA'.
    """
    expediente_c3 = {
        "alerta_fraude": False,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 45,
        "ratio_cuota_ingreso": 0.35,
        "puntaje_riesgo": 620,
        "monto_solicitado": 8000.0,
        "producto": "consumo",
    }

    decision = interprete_oficial.evaluar(expediente_c3)

    assert decision.tipo == "rechazar"
    assert decision.motivo == "MORA_ELEVADA"
    assert decision.regla_determinante == "R04_MORA_ALTA"


def test_escenario_c4_carga_financiera_alta(interprete_oficial: FinRuleInterpreter):
    """
    Escenario C4: Carga financiera alta
    Datos: Sin alerta, validaciones completas, mora 0, ratio 0.52, puntaje 730.
    Resultado esperado: Revisión humana ('revision', 'CAPACIDAD_DE_PAGO').
    Regla determinante esperada: 'R06_ENDEUDAMIENTO'.
    """
    expediente_c4 = {
        "alerta_fraude": False,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.52,
        "puntaje_riesgo": 730,
        "monto_solicitado": 12000.0,
        "producto": "consumo",
    }

    decision = interprete_oficial.evaluar(expediente_c4)

    assert decision.tipo == "revision"
    assert decision.motivo == "CAPACIDAD_DE_PAGO"
    assert decision.regla_determinante == "R06_ENDEUDAMIENTO"


def test_escenario_c5_documentacion_pendiente(interprete_oficial: FinRuleInterpreter):
    """
    Escenario C5: Documentación pendiente
    Datos: Sin alerta, identidad verificada, pero documentos no verificados (falso).
    Resultado esperado: Revisión humana ('revision', 'DOCUMENTACION_INCOMPLETA').
    Regla determinante esperada: 'R03_DOCUMENTOS'.
    """
    expediente_c5 = {
        "alerta_fraude": False,
        "identidad_verificada": True,
        "documentos_verificados": False,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.25,
        "puntaje_riesgo": 690,
        "monto_solicitado": 7500.0,
        "producto": "consumo",
    }

    decision = interprete_oficial.evaluar(expediente_c5)

    assert decision.tipo == "revision"
    assert decision.motivo == "DOCUMENTACION_INCOMPLETA"
    assert decision.regla_determinante == "R03_DOCUMENTOS"


# ==============================================================================
# SUITE 2: Cláusula por Defecto y Auditoría Regulatoria
# ==============================================================================

def test_clausula_defecto_ejecutada():
    """
    Verifica que si un expediente no coincide con ninguna regla explícita,
    el motor ejecuta obligatoriamente la cláusula por defecto.
    """
    dsl_parcial = """
    politica "POLITICA_ACREDITADA" version "1.0" {
      regla "SOLO_VIP" prioridad 50
        cuando puntaje_riesgo >= 950
        entonces aprobar("CLIENTE_VIP");
      defecto revision("CASO_NO_CLASIFICADO");
    }
    """
    politica = parse_finrule(dsl_parcial)
    interprete = FinRuleInterpreter(politica)

    expediente_ordinario = {
        "puntaje_riesgo": 700
    }
    decision = interprete.evaluar(expediente_ordinario)

    assert decision.tipo == "revision"
    assert decision.motivo == "CASO_NO_CLASIFICADO"
    assert decision.regla_determinante == "DEFECTO"


def test_registro_auditoria_completo(interprete_oficial: FinRuleInterpreter):
    """
    Verifica que la ejecución con auditoría genere un registro con trazabilidad
    de las reglas evaluadas y copia del expediente evaluado.
    """
    expediente = {
        "alerta_fraude": True,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.20,
        "puntaje_riesgo": 800,
    }
    auditoria = interprete_oficial.evaluar_con_auditoria(expediente)

    assert auditoria.politica == "CREDITO_CONSUMO"
    assert auditoria.version == "1.0"
    assert auditoria.decision.tipo == "revision"
    assert auditoria.decision.regla_determinante == "R01_FRAUDE"
    assert "R01_FRAUDE" in auditoria.reglas_evaluadas
    assert auditoria.expediente_evaluado["alerta_fraude"] is True
    assert auditoria.timestamp is not None


# ==============================================================================
# SUITE 3: Semántica Estática y Bloqueo de Tipos Incompatibles
# ==============================================================================

def test_semantica_bloquea_atributo_no_declarado():
    """Verifica que referenciar una variable no existente en el diccionario lance error semántico."""
    dsl_invalido = """
    politica "TEST_ATRIBUTO" version "1.0" {
      regla "R01" prioridad 10
        cuando variable_inexistente == verdadero
        entonces revision("ERROR");
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_invalido)
    with pytest.raises(UndefinedAttributeError) as exc_info:
        validar_politica(politica, estricto=True)
    assert "variable_inexistente" in str(exc_info.value)


def test_semantica_bloquea_booleano_comparado_con_entero():
    """
    Verifica que comparar un atributo booleano con un entero o float
    sea bloqueado semánticamente (requisito de la entrega técnica).
    """
    dsl_invalido = """
    politica "TEST_TIPOS" version "1.0" {
      regla "R01" prioridad 10
        cuando alerta_fraude == 1
        entonces revision("TIPO_ERRONEO");
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_invalido)
    with pytest.raises(TypeMismatchError) as exc_info:
        validar_politica(politica, estricto=True)
    assert "alerta_fraude" in str(exc_info.value)


def test_semantica_bloquea_operador_relacional_en_booleano():
    """Verifica que operadores como >, <, >= no se permitan sobre booleanos."""
    dsl_invalido = """
    politica "TEST_OPERADOR" version "1.0" {
      regla "R01" prioridad 10
        cuando alerta_fraude > verdadero
        entonces revision("OPERADOR_INVALIDO");
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_invalido)
    with pytest.raises(TypeMismatchError) as exc_info:
        validar_politica(politica, estricto=True)
    assert "Operador '>'" in str(exc_info.value)


def test_semantica_bloquea_comparacion_entero_con_texto():
    """Verifica el ejemplo del documento: puntaje_riesgo >= 'alto' debe fallar semánticamente."""
    dsl_invalido = """
    politica "TEST_PUNTAJE" version "1.0" {
      regla "R01" prioridad 10
        cuando puntaje_riesgo >= "alto"
        entonces revision("PUNTAJE_TEXTO");
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_invalido)
    with pytest.raises(TypeMismatchError) as exc_info:
        validar_politica(politica, estricto=True)
    assert "puntaje_riesgo" in str(exc_info.value)


def test_semantica_bloquea_reglas_con_nombres_duplicados():
    """Verifica que dos reglas con el mismo identificador no sean admitidas."""
    dsl_duplicado = """
    politica "TEST_DUPLICADO" version "1.0" {
      regla "REGLA_REPETIDA" prioridad 50
        cuando dias_mora_vigente > 0
        entonces revision("MOTIVO_1");
      regla "REGLA_REPETIDA" prioridad 40
        cuando dias_mora_vigente > 10
        entonces rechazar("MOTIVO_2");
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_duplicado)
    with pytest.raises(DuplicateRuleError) as exc_info:
        validar_politica(politica, estricto=True)
    assert "REGLA_REPETIDA" in str(exc_info.value)


# ==============================================================================
# SUITE 4: Cortocircuito Lógico y Ordenamiento por Prioridad
# ==============================================================================

def test_cortocircuito_logico_conjuncion():
    """
    Verifica que en una conjunción ('y'), si el primer término es falso,
    no se evalúan los términos siguientes.
    """
    evaluador = EvaluadorCondicionesVisitor()
    # Si intentara evaluar 'campo_inexistente', lanzaría RuntimeError.
    # Gracias al cortocircuito, como alerta_fraude == verdadero es False,
    # la evaluación termina inmediatamente sin tocar campo_inexistente.
    condicion_compuesta = Conjuncion(
        condiciones=[
            Comparacion(campo="alerta_fraude", operador="==", valor=True),
            Comparacion(campo="campo_inexistente", operador="==", valor=999),
        ]
    )
    contexto = {"alerta_fraude": False}

    # No debe lanzar excepción
    resultado = evaluador.visit(condicion_compuesta, contexto)
    assert resultado is False
    assert any("Cortocircuito 'y'" in traza for traza in evaluador.trazas_evaluacion)


def test_cortocircuito_logico_disyuncion():
    """
    Verifica que en una disyunción ('o'), si el primer término es verdadero,
    no se evalúan los términos siguientes.
    """
    evaluador = EvaluadorCondicionesVisitor()
    # El primer término es True; el segundo contiene un campo inexistente.
    condicion_compuesta = Disyuncion(
        condiciones=[
            Comparacion(campo="alerta_fraude", operador="==", valor=True),
            Comparacion(campo="campo_inexistente", operador="==", valor=999),
        ]
    )
    contexto = {"alerta_fraude": True}

    # No debe lanzar excepción
    resultado = evaluador.visit(condicion_compuesta, contexto)
    assert resultado is True
    assert any("Cortocircuito 'o'" in traza for traza in evaluador.trazas_evaluacion)


def test_ordenamiento_dinamico_por_prioridad():
    """
    Verifica que el intérprete ordene las reglas por su atributo prioridad,
    ejecutando primero la de mayor prioridad aunque esté escrita al final del código.
    """
    dsl_desordenado = """
    politica "TEST_PRIORIDAD" version "1.0" {
      regla "REGLA_BAJA" prioridad 10
        cuando dias_mora_vigente >= 0
        entonces revision("BAJA_PRIORIDAD");
        
      regla "REGLA_ALTA" prioridad 99
        cuando dias_mora_vigente >= 0
        entonces aprobar("ALTA_PRIORIDAD");
        
      defecto revision("DEFECTO");
    }
    """
    politica = parse_finrule(dsl_desordenado)
    interprete = FinRuleInterpreter(politica)

    decision = interprete.evaluar({"dias_mora_vigente": 5})

    # Debe disparar REGLA_ALTA porque prioridad 99 > 10
    assert decision.regla_determinante == "REGLA_ALTA"
    assert decision.motivo == "ALTA_PRIORIDAD"


# ==============================================================================
# SUITE 5: Verificaciones Sintácticas (Gramática EBNF)
# ==============================================================================

def test_sintaxis_incorrecta_falta_entonces():
    """
    Verifica el ejemplo del documento donde se omite 'entonces',
    el cual debe provocar un FinRuleSyntaxError inmediato.
    """
    dsl_invalido = """
    politica "DEMO" version "1.0" {
      regla "R01" prioridad 10
        cuando alerta_fraude == verdadero
        revision("REVISAR_ALERTA");
      defecto revision("SIN_COINCIDENCIA");
    }
    """
    with pytest.raises(FinRuleSyntaxError) as exc_info:
        parse_finrule(dsl_invalido)
    assert "Error sintáctico" in str(exc_info.value)


# ==============================================================================
# SUITE 6: Compilador / Generador de Código Python Nativo
# ==============================================================================

def test_generador_codigo_compilado(politica_compilada: Politica):
    """
    Verifica que el generador traduzca el AST a código Python válido
    y que dicho código compilado produzca exactamente las mismas decisiones
    que el intérprete para los escenarios C1 y C2.
    """
    codigo_python = compilar_a_python(politica_compilada)
    assert "def evaluar_expediente(expediente: Dict[str, Any])" in codigo_python
    assert "R01_FRAUDE" in codigo_python

    # Ejecutar el código generado dinámicamente en un namespace aislado
    namespace = {}
    exec(codigo_python, namespace)
    evaluar_func = namespace["evaluar_expediente"]

    # Caso C1: elegible
    exp_c1 = {
        "alerta_fraude": False,
        "identidad_verificada": True,
        "documentos_verificados": True,
        "dias_mora_vigente": 0,
        "ratio_cuota_ingreso": 0.28,
        "puntaje_riesgo": 710,
    }
    res_c1 = evaluar_func(exp_c1)
    assert res_c1["tipo"] == "aprobar"
    assert res_c1["motivo"] == "ELEGIBLE_PRELIMINAR"
    assert res_c1["regla_determinante"] == "R08_PREAPROBACION"

    # Caso C2: alerta de fraude
    exp_c2 = {"alerta_fraude": True}
    res_c2 = evaluar_func(exp_c2)
    assert res_c2["tipo"] == "revision"
    assert res_c2["motivo"] == "ALERTA_OPERACION_SOSPECHOSA"
    assert res_c2["regla_determinante"] == "R01_FRAUDE"

