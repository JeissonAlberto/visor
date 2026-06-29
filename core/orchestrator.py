"""
core/orchestrator.py — El Cerebro de Comandante para Visor v3.3.
Inspirado en Agent-Orchestrator. Coordina misiones complejas en paralelo.
"""

import concurrent.futures
from core.raptor_eye import hunt_vulnerabilities
from core.guardian_ai import generate_remediation_plan
from core.medusa_shield import scan_for_secrets

class MissionOrchestrator:
    def __init__(self, target=None):
        self.target = target
        self.results = {}

    def execute_security_mission(self):
        """
        Misión de Seguridad Total: Raptor + Guardian + Medusa en paralelo.
        """
        print(f"\n[ORCHESTRATOR] Iniciando Misión de Seguridad sobre: {self.target if self.target else 'Sistema Local'}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Lanzamos agentes especialistas
            future_raptor = executor.submit(hunt_vulnerabilities, self.target) if self.target else None
            future_medusa = executor.submit(scan_for_secrets, ".")
            
            print("  -> [Agente Raptor] Cazando vulnerabilidades...")
            print("  -> [Agente Medusa] Escaneando secretos y fugas...")
            
            if future_raptor:
                self.results['raptor'] = future_raptor.result()
                print("  <- [Agente Raptor] Hallazgos detectados.")
                
                # Encadenamiento lógico: Si hay hallazgos, llamar a Guardian
                print("  -> [Agente Guardian] Orquestando plan de remediación...")
                self.results['guardian'] = generate_remediation_plan(self.results['raptor'])
            
            self.results['medusa'] = future_medusa.result()
            print("  <- [Agente Medusa] Escaneo de integridad completado.")

        return self.results

def run_orchestrated_task(task_type, target=None):
    orchestrator = MissionOrchestrator(target)
    if task_type == "SECURITY_AUDIT":
        return orchestrator.execute_security_mission()
    return None
