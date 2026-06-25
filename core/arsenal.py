"""
core/arsenal.py — Lógica de procesamiento de comandos estilo Arsenal-NG.
"""

import re

def obtener_placeholders(comando: str):
    """Extrae los {{campos}} del comando."""
    return re.findall(r"\{\{(.*?)\}\}", comando)

def procesar_comando(comando: str, valores: dict):
    """Reemplaza placeholders por valores reales o valores por defecto."""
    
    # Manejar campos con default: {{user|admin}}
    placeholders = obtener_placeholders(comando)
    final_cmd = comando
    
    for p in placeholders:
        original_p = "{{" + p + "}}"
        
        if "|" in p:
            nombre, default = p.split("|", 1)
            # Prioridad: valor ingresado > default
            valor = valores.get(nombre) if valores.get(nombre) else default
        else:
            nombre = p
            valor = valores.get(nombre, f"[{nombre.upper()}]")
            
        final_cmd = final_cmd.replace(original_p, str(valor))
        
    return final_cmd
