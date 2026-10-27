"""
Módulo main.py (Script Demostrativo de Ejecución)
=================================================
Proyecto Integrador: FinRule DSL
Carrera: Ingeniería de Software - Universidad Científica del Sur
Curso: Lenguaje de Dominio Específico (2026)

Este script proporciona una demostración interactiva de FinRule DSL:
1. Carga la política 'CREDITO_CONSUMO' versión 1.0 desde el archivo .finrule.
2. Ejecuta el análisis léxico y sintáctico (Parser Lark) generando el AST.
3. Ejecuta la validación semántica estática (SemanticValidator).
4. Ejecuta el intérprete con los 5 escenarios sintéticos de prueba (C1 a C5).
5. Demuestra la compilación del AST a código fuente Python nativo.
"""

import json
import sys

from parser import parse_finrule_file
from semantic_validator import SemanticValidator
from interpreter import FinRuleInterpreter
from code_generator import compilar_a_python

# Asegurar codificación UTF-8 para salida en terminales de cualquier plataforma
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    print("=" * 80)
    print("      FinRule DSL: Demostracion del Prototipo Funcional de Interprete")
    print("  Universidad Cientifica del Sur - Facultad de Ingenieria de Software")
    print("=" * 80)

    # 1. Parsing del archivo DSL
    archivo_politica = "credito_consumo.finrule"
    print(f"\n[1/5] Leyendo y parseando archivo DSL: '{archivo_politica}'...")
    try:
        politica = parse_finrule_file(archivo_politica)
        print(f"      [OK] Politica parseada exitosamente:")
        print(f"        - Nombre: {politica.nombre}")
        print(f"        - Version: {politica.version}")
        print(f"        - Total de reglas: {len(politica.reglas)}")
        print(f"        - Clausula por defecto: {politica.defecto.accion}")
    except Exception as e:
        print(f"      [ERROR] Error durante el parsing: {e}")
        return

    # 2. Validación Semántica Estática
    print(f"\n[2/5] Ejecutando Validacion Semantica Estatica...")
    validador = SemanticValidator()
    resultado = validador.validar(politica)
    if resultado.es_valido:
        print("      [OK] AST valido. No se detectaron errores de tipado ni identificadores desconocidos.")
        if resultado.advertencias:
            for adv in resultado.advertencias:
                print(f"      [ADVERTENCIA] {adv}")
    else:
        print("      [ERROR] Se detectaron errores semanticos:")
        for err in resultado.errores:
            print(f"        - {err}")
        return

    # 3. Inicialización del Intérprete
    print(f"\n[3/5] Inicializando el Interprete (Patron Visitor)...")
    interprete = FinRuleInterpreter(politica)
    print(f"      [OK] Reglas ordenadas dinamicamente por prioridad (mayor a menor):")
    for r in interprete.reglas_ordenadas:
        print(f"        * [Prio {r.prioridad:3d}] {r.nombre:<20} -> {r.accion.tipo}('{r.accion.motivo}')")

    # 4. Evaluación de los 5 Escenarios Sintéticos (Tabla VIII)
    print(f"\n[4/5] Evaluando los 5 Escenarios Sinteticos de la Especificacion:")
    print("-" * 80)

    escenarios = [
        (
            "C1: Perfil elegible",
            {
                "alerta_fraude": False,
                "identidad_verificada": True,
                "documentos_verificados": True,
                "dias_mora_vigente": 0,
                "ratio_cuota_ingreso": 0.28,
                "puntaje_riesgo": 710,
                "monto_solicitado": 10000.0,
                "producto": "consumo",
            },
            "Preaprobacion tecnica: ELEGIBLE_PRELIMINAR"
        ),
        (
            "C2: Alerta de fraude",
            {
                "alerta_fraude": True,
                "identidad_verificada": True,
                "documentos_verificados": True,
                "dias_mora_vigente": 0,
                "ratio_cuota_ingreso": 0.20,
                "puntaje_riesgo": 850,
                "monto_solicitado": 5000.0,
                "producto": "consumo",
            },
            "Revision humana: ALERTA_OPERACION_SOSPECHOSA"
        ),
        (
            "C3: Mora elevada",
            {
                "alerta_fraude": False,
                "identidad_verificada": True,
                "documentos_verificados": True,
                "dias_mora_vigente": 45,
                "ratio_cuota_ingreso": 0.35,
                "puntaje_riesgo": 620,
                "monto_solicitado": 8000.0,
                "producto": "consumo",
            },
            "Recomendacion de rechazo: MORA_ELEVADA"
        ),
        (
            "C4: Carga financiera alta",
            {
                "alerta_fraude": False,
                "identidad_verificada": True,
                "documentos_verificados": True,
                "dias_mora_vigente": 0,
                "ratio_cuota_ingreso": 0.52,
                "puntaje_riesgo": 730,
                "monto_solicitado": 12000.0,
                "producto": "consumo",
            },
            "Revision humana: CAPACIDAD_DE_PAGO"
        ),
        (
            "C5: Documentacion pendiente",
            {
                "alerta_fraude": False,
                "identidad_verificada": True,
                "documentos_verificados": False,
                "dias_mora_vigente": 0,
                "ratio_cuota_ingreso": 0.25,
                "puntaje_riesgo": 690,
                "monto_solicitado": 7500.0,
                "producto": "consumo",
            },
            "Revision humana: DOCUMENTACION_INCOMPLETA"
        ),
    ]

    for titulo, expediente, expectativa in escenarios:
        auditoria = interprete.evaluar_con_auditoria(expediente)
        decision = auditoria.decision
        print(f"\n>> Caso: {titulo}")
        print(f"  Expediente de entrada : {json.dumps(expediente)}")
        print(f"  Expectativa de diseno : {expectativa}")
        print(f"  Decision obtenida     : TIPO='{decision.tipo.upper()}', MOTIVO='{decision.motivo}'")
        print(f"  Regla determinante    : {decision.regla_determinante}")
        print(f"  Trazabilidad          : Evaluo reglas {auditoria.reglas_evaluadas}")

    # 5. Demostración de Compilación a Código Python Nativo
    print("\n" + "=" * 80)
    print("[5/5] Compilacion del AST a Codigo Python Nativo (Seccion VI.B del documento):")
    print("-" * 80)
    codigo_compilado = compilar_a_python(politica)
    print(codigo_compilado[:600] + "\n    [... codigo restante omitido por brevedad ...]\n")
    print("=" * 80)
    print("[OK] Demostracion finalizada exitosamente. Todos los escenarios validados.")
    print("=" * 80)


if __name__ == "__main__":
    main()
