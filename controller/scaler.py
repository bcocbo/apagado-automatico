import boto3, os, time, subprocess, datetime, pytz, croniter, asyncio, logging, uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from tenacity import retry, stop_after_attempt, wait_exponential
import json

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Métricas Prometheus
scaling_operations = Counter(
    'namespace_scaling_operations_total',
    'Total namespace scaling operations',
    ['namespace', 'operation', 'status']
)

scaling_duration = Histogram(
    'namespace_scaling_duration_seconds',
    'Time spent scaling namespaces',
    ['namespace', 'operation']
)

active_namespaces = Gauge(
    'namespace_active_count',
    'Number of active namespaces'
)

controller_errors = Counter(
    'controller_errors_total',
    'Total controller errors',
    ['error_type']
)

# Configuración
aws_region = os.environ.get('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=aws_region)
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'NamespaceSchedules'))
tz = pytz.timezone(os.environ.get('TIMEZONE', 'UTC'))
system_ns = set(os.environ.get('SYSTEM_NAMESPACES', 'kube-system,kube-public,kube-node-lease,default,argocd,kyverno,encendido-eks,karpenter').split(','))

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")
                
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
            
    def on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker opened after {self.failure_count} failures")

class RollbackManager:
    def __init__(self):
        self.rollback_history = {}
        
    def save_state(self, namespace: str, deployments: List[Dict]):
        """Guardar estado antes de operación de escalado"""
        self.rollback_history[namespace] = {
            'timestamp': datetime.utcnow().isoformat(),
            'deployments': deployments
        }
        logger.info("State saved for rollback", namespace=namespace, deployments_count=len(deployments))
        
    def rollback(self, namespace: str):
        """Restaurar estado anterior"""
        if namespace not in self.rollback_history:
            logger.error("No rollback data available", namespace=namespace)
            return False
            
        previous_state = self.rollback_history[namespace]
        try:
            for deployment in previous_state['deployments']:
                subprocess.run([
                    "kubectl", "scale", "deploy", deployment['name'], 
                    "-n", namespace, f"--replicas={deployment['replicas']}"
                ], check=True)
            logger.info("Rollback completed successfully", namespace=namespace)
            return True
        except Exception as e:
            logger.error("Rollback failed", namespace=namespace, error=str(e))
            controller_errors.labels(error_type="rollback_failed").inc()
            return False

# Instancias globales
circuit_breaker = CircuitBreaker()
rollback_manager = RollbackManager()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_namespaces():
    """Obtener lista de namespaces excluyendo los del sistema"""
    try:
        result = subprocess.check_output([
            "kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"
        ]).decode().split()
        namespaces = [ns for ns in result if ns not in system_ns]
        active_namespaces.set(len(namespaces))
        logger.info("Retrieved namespaces", count=len(namespaces), namespaces=namespaces)
        return namespaces
    except subprocess.CalledProcessError as e:
        logger.error("Failed to get namespaces", error=str(e))
        controller_errors.labels(error_type="kubectl_error").inc()
        raise

def get_deployment_state(namespace: str) -> List[Dict]:
    """Obtener estado actual de deployments en un namespace"""
    try:
        deps = subprocess.check_output([
            "kubectl", "get", "deploy", "-n", namespace, 
            "-o", "jsonpath={range .items[*]}{.metadata.name},{.spec.replicas}{\"\\n\"}{end}"
        ]).decode().strip().split('\n')
        
        deployments = []
        for dep_info in deps:
            if dep_info:
                name, replicas = dep_info.split(',')
                deployments.append({
                    'name': name,
                    'replicas': int(replicas) if replicas else 0
                })
        return deployments
    except subprocess.CalledProcessError as e:
        logger.error("Failed to get deployment state", namespace=namespace, error=str(e))
        return []

def scale(ns, to_zero):
    """Escalar deployments en un namespace"""
    action = "shutdown" if to_zero else "startup"
    operation_start = time.time()
    
    try:
        with scaling_duration.labels(namespace=ns, operation=action).time():
            # Guardar estado antes de escalar
            if to_zero:
                current_state = get_deployment_state(ns)
                rollback_manager.save_state(ns, current_state)
            
            # Usar circuit breaker para la operación
            circuit_breaker.call(_perform_scaling, ns, to_zero)
            
        scaling_operations.labels(namespace=ns, operation=action, status="success").inc()
        logger.info("Scaling operation completed", 
                   namespace=ns, action=action, duration=time.time() - operation_start)
        
    except Exception as e:
        scaling_operations.labels(namespace=ns, operation=action, status="error").inc()
        controller_errors.labels(error_type="scaling_error").inc()
        logger.error("Scaling operation failed", 
                    namespace=ns, action=action, error=str(e))
        
        # Intentar rollback en caso de error
        if to_zero:
            logger.info("Attempting rollback due to scaling failure", namespace=ns)
            rollback_manager.rollback(ns)

def _perform_scaling(ns, to_zero):
    """Realizar la operación de escalado real"""
    action = "Apagado" if to_zero else "Encendido"
    
    deps = subprocess.check_output([
        "kubectl", "get", "deploy", "-n", ns, 
        "-o", "custom-columns=NAME:.metadata.name", "--no-headers"
    ]).decode().split()
    
    for dep in deps:
        if to_zero:
            current = subprocess.check_output([
                "kubectl", "get", "deploy", dep, "-n", ns, 
                "-o", "jsonpath={.spec.replicas}"
            ]).decode().strip()
            
            if current and int(current) > 0:
                subprocess.run([
                    "kubectl", "annotate", "deploy", dep, "-n", ns, 
                    f"original-replicas={current}", "--overwrite"
                ], check=True)
                subprocess.run([
                    "kubectl", "scale", "deploy", dep, "-n", ns, "--replicas=0"
                ], check=True)
        else:
            orig = subprocess.check_output([
                "kubectl", "get", "deploy", dep, "-n", ns, 
                "-o", "jsonpath={.metadata.annotations.original-replicas}"
            ]).decode().strip()
            
            if orig:
                subprocess.run([
                    "kubectl", "scale", "deploy", dep, "-n", ns, f"--replicas={orig}"
                ], check=True)
                subprocess.run([
                    "kubectl", "annotate", "deploy", dep, "-n", ns, "original-replicas-"
                ], check=True)
    
    # Crear evento en Kubernetes
    subprocess.run([
        "kubectl", "create", "event", "-n", ns, "--type=Normal", 
        f"--reason=Auto{action}", f"{action} automático"
    ], check=True)

def health_check():
    """Health check endpoint"""
    try:
        # Verificar conectividad a DynamoDB
        table.meta.client.describe_table(TableName=table.name)
        
        # Verificar conectividad a Kubernetes
        subprocess.check_output(["kubectl", "version", "--client"], timeout=5)
        
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

def get_schedules():
    """Obtener todos los horarios configurados"""
    try:
        response = table.scan()
        schedules = []
        
        for item in response['Items']:
            schedule = {
                'id': item.get('schedule_id', item['namespace']),
                'namespace': item['namespace'],
                'enabled': item.get('enabled', True),
                'timezone': item.get('timezone', 'UTC'),
                'startup_time': item.get('startup_time', '08:00'),
                'shutdown_time': item.get('shutdown_time', '17:00'),
                'days_of_week': item.get('days_of_week', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']),
                'metadata': item.get('metadata', {}),
                'created_at': item.get('created_at', ''),
                'updated_at': item.get('updated_at', '')
            }
            schedules.append(schedule)
            
        return schedules
    except Exception as e:
        logger.error("Error getting schedules", error=str(e))
        return []

def create_schedule(schedule_data):
    """Crear un nuevo horario"""
    try:
        schedule_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        item = {
            'namespace': schedule_data['namespace'],
            'schedule_id': schedule_id,
            'enabled': schedule_data.get('enabled', True),
            'timezone': schedule_data.get('timezone', 'UTC'),
            'startup_time': schedule_data['startup_time'],
            'shutdown_time': schedule_data['shutdown_time'],
            'days_of_week': schedule_data['days_of_week'],
            'metadata': schedule_data.get('metadata', {}),
            'created_at': now,
            'updated_at': now
        }
        
        table.put_item(Item=item)
        logger.info("Schedule created", namespace=schedule_data['namespace'], schedule_id=schedule_id)
        
        return {**item, 'id': schedule_id}
    except Exception as e:
        logger.error("Error creating schedule", error=str(e))
        raise e

def get_namespaces_list():
    """Obtener lista de namespaces disponibles"""
    try:
        result = subprocess.check_output([
            "kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"
        ]).decode().split()
        namespaces = [ns for ns in result if ns not in system_ns]
        return namespaces
    except Exception as e:
        logger.error("Error getting namespaces", error=str(e))
        return []

def main():
    """Función principal del controlador"""
    # Iniciar servidor de métricas
    start_http_server(8080)
    logger.info("Started Prometheus metrics server on port 8080")
    
    # Agregar endpoint de health check
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    import json
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                health = health_check()
                self.send_response(200 if health["status"] == "healthy" else 503)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(health).encode())
            elif self.path == '/api/schedules':
                schedules = get_schedules()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(schedules).encode())
            elif self.path == '/api/namespaces':
                namespaces = get_namespaces_list()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(namespaces).encode())
            elif self.path == '/metrics':
                # Prometheus metrics ya están en el puerto 8080
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'# Metrics available on port 8080')
            elif self.path == '/' or self.path == '/frontend':
                # Servir la página del frontend
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html_content = self.get_frontend_html()
                self.wfile.write(html_content.encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_POST(self):
            if self.path == '/api/schedules':
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    schedule_data = json.loads(post_data.decode('utf-8'))
                    
                    new_schedule = create_schedule(schedule_data)
                    
                    self.send_response(201)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(new_schedule).encode())
                except Exception as e:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    error_response = {"error": str(e)}
                    self.wfile.write(json.dumps(error_response).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_OPTIONS(self):
            # Manejar preflight requests para CORS
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        
        def get_frontend_html(self):
            return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Namespace Encendido EKS</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Roboto', sans-serif; background-color: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1976d2, #42a5f5); color: white; padding: 30px 20px; border-radius: 12px; margin-bottom: 30px; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h2 { color: #1976d2; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #1976d2; }
        .stat-number { font-size: 2.5rem; font-weight: bold; color: #1976d2; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 0.9rem; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; color: #333; }
        .form-group input, .form-group select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 1rem; transition: border-color 0.3s; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #1976d2; }
        .days-selector { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
        .day-chip { padding: 8px 16px; border: 2px solid #e0e0e0; border-radius: 20px; cursor: pointer; transition: all 0.3s; font-size: 0.9rem; }
        .day-chip.active { background-color: #1976d2; color: white; border-color: #1976d2; }
        .day-chip:hover { border-color: #1976d2; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background-color: #1976d2; color: white; }
        .btn-primary:hover { background-color: #1565c0; }
        .schedule-list { margin-top: 20px; }
        .schedule-item { background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #1976d2; }
        .schedule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .schedule-title { font-weight: 500; font-size: 1.1rem; }
        .schedule-status { padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 500; }
        .status-active { background-color: #e8f5e8; color: #2e7d32; }
        .status-inactive { background-color: #ffebee; color: #d32f2f; }
        .status-paused { background-color: #fff3e0; color: #f57c00; }
        .schedule-details { color: #666; font-size: 0.9rem; line-height: 1.4; }
        .material-icons { font-size: 1.2rem; }
        .alert { padding: 16px; border-radius: 8px; margin-bottom: 20px; }
        .alert-success { background-color: #e8f5e8; color: #2e7d32; border-left: 4px solid #2e7d32; }
        .alert-error { background-color: #ffebee; color: #d32f2f; border-left: 4px solid #d32f2f; }
        @media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } .stats-grid { grid-template-columns: 1fr; } .header h1 { font-size: 2rem; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎛️ Namespace Encendido EKS</h1>
            <p>Sistema de apagado automático de namespaces para optimización de costos</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-schedules">0</div>
                <div class="stat-label">Horarios Configurados</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-schedules">0</div>
                <div class="stat-label">Horarios Activos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="running-namespaces">0</div>
                <div class="stat-label">Namespaces Encendidos</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="estimated-savings">$0</div>
                <div class="stat-label">Ahorro Estimado/mes</div>
            </div>
        </div>

        <div class="form-grid">
            <div class="card">
                <h2><span class="material-icons">schedule</span> Crear Nuevo Horario</h2>
                <div id="alert-container"></div>
                <form id="schedule-form">
                    <div class="form-group">
                        <label for="namespace">Namespace</label>
                        <select id="namespace" required>
                            <option value="">Seleccionar namespace...</option>
                            <option value="production-app">production-app</option>
                            <option value="staging-app">staging-app</option>
                            <option value="development-app">development-app</option>
                            <option value="testing-app">testing-app</option>
                            <option value="demo-app">demo-app</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="timezone">Zona Horaria</label>
                        <select id="timezone">
                            <option value="America/Bogota">Colombia (UTC-5)</option>
                            <option value="UTC">UTC</option>
                            <option value="America/New_York">New York (UTC-5)</option>
                            <option value="Europe/Madrid">Madrid (UTC+1)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="startup-time">🟢 Hora de Encendido</label>
                        <input type="time" id="startup-time" value="08:00" required>
                    </div>
                    <div class="form-group">
                        <label for="shutdown-time">🔴 Hora de Apagado</label>
                        <input type="time" id="shutdown-time" value="17:00" required>
                    </div>
                    <div class="form-group">
                        <label>📅 Días de la Semana</label>
                        <div class="days-selector">
                            <div class="day-chip active" data-day="monday">L - Lunes</div>
                            <div class="day-chip active" data-day="tuesday">M - Martes</div>
                            <div class="day-chip active" data-day="wednesday">X - Miércoles</div>
                            <div class="day-chip active" data-day="thursday">J - Jueves</div>
                            <div class="day-chip active" data-day="friday">V - Viernes</div>
                            <div class="day-chip" data-day="saturday">S - Sábado</div>
                            <div class="day-chip" data-day="sunday">D - Domingo</div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="business-unit">Unidad de Negocio</label>
                        <input type="text" id="business-unit" placeholder="Ej: Engineering, Marketing">
                    </div>
                    <div class="form-group">
                        <label for="cost-target">Meta de Ahorro (USD/mes)</label>
                        <input type="number" id="cost-target" placeholder="1000">
                    </div>
                    <button type="submit" class="btn btn-primary">
                        <span class="material-icons">add</span> Crear Horario
                    </button>
                </form>
            </div>

            <div class="card">
                <h2><span class="material-icons">list</span> Horarios Configurados</h2>
                <div class="schedule-list" id="schedule-list">
                    <p style="text-align: center; color: #666; padding: 20px;">
                        No hay horarios configurados aún.<br>
                        <small>Crea tu primer horario usando el formulario de la izquierda.</small>
                    </p>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>
                <span class="material-icons">refresh</span> Estado en Tiempo Real
                <span style="margin-left: auto; font-size: 0.9rem; font-weight: normal; color: #666;">
                    <span id="current-time"></span> COT
                </span>
            </h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" style="color: #2e7d32;">0</div>
                    <div class="stat-label">Namespaces Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #1976d2;">0</div>
                    <div class="stat-label">Réplicas Totales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #f57c00;">0</div>
                    <div class="stat-label">Horarios Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" style="color: #d32f2f;">0</div>
                    <div class="stat-label">Namespaces Apagados</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let schedules = [];
        
        // Cargar datos iniciales
        async function loadData() {
            try {
                // Cargar horarios
                const schedulesResponse = await fetch('/api/schedules');
                schedules = await schedulesResponse.json();
                updateSchedulesList();
                updateStats();
                
                // Cargar namespaces
                const namespacesResponse = await fetch('/api/namespaces');
                const namespaces = await namespacesResponse.json();
                updateNamespaceOptions(namespaces);
                
            } catch (error) {
                console.error('Error loading data:', error);
                showAlert('Error cargando datos del servidor', 'error');
            }
        }
        
        function updateNamespaceOptions(namespaces) {
            const select = document.getElementById('namespace');
            select.innerHTML = '<option value="">Seleccionar namespace...</option>';
            
            namespaces.forEach(ns => {
                const option = document.createElement('option');
                option.value = ns;
                option.textContent = ns;
                select.appendChild(option);
            });
        }
        
        function updateSchedulesList() {
            const container = document.getElementById('schedule-list');
            
            if (schedules.length === 0) {
                container.innerHTML = `
                    <p style="text-align: center; color: #666; padding: 20px;">
                        No hay horarios configurados aún.<br>
                        <small>Crea tu primer horario usando el formulario de la izquierda.</small>
                    </p>
                `;
                return;
            }
            
            container.innerHTML = schedules.map(schedule => {
                const status = getScheduleStatus(schedule);
                const daysText = formatDays(schedule.days_of_week);
                
                return `
                    <div class="schedule-item">
                        <div class="schedule-header">
                            <div class="schedule-title">📦 ${schedule.namespace}</div>
                            <div class="schedule-status ${status.class}">${status.text}</div>
                        </div>
                        <div class="schedule-details">
                            🕐 ${schedule.startup_time} - ${schedule.shutdown_time} (${schedule.timezone})<br>
                            📅 ${daysText}<br>
                            ${schedule.metadata.business_unit ? `🏢 ${schedule.metadata.business_unit}<br>` : ''}
                            ${schedule.metadata.cost_savings_target ? `💰 Meta de ahorro: $${schedule.metadata.cost_savings_target}/mes` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats() {
            document.getElementById('total-schedules').textContent = schedules.length;
            document.getElementById('active-schedules').textContent = schedules.filter(s => s.enabled).length;
            document.getElementById('running-namespaces').textContent = schedules.filter(s => getScheduleStatus(s).active).length;
            
            const totalSavings = schedules.reduce((sum, s) => sum + (parseInt(s.metadata?.cost_savings_target) || 0), 0);
            document.getElementById('estimated-savings').textContent = `$${totalSavings}`;
        }
        
        function getScheduleStatus(schedule) {
            if (!schedule.enabled) {
                return { text: '⏸️ Pausado', class: 'status-paused', active: false };
            }
            
            const now = new Date();
            const currentDay = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
            const currentTime = now.toTimeString().slice(0, 5);
            
            if (!schedule.days_of_week.includes(currentDay)) {
                return { text: '📅 Fuera de horario', class: 'status-inactive', active: false };
            }
            
            if (currentTime >= schedule.startup_time && currentTime < schedule.shutdown_time) {
                return { text: '🟢 Activo', class: 'status-active', active: true };
            } else {
                return { text: '🔴 Inactivo', class: 'status-inactive', active: false };
            }
        }
        
        function formatDays(days) {
            const dayMap = {
                'monday': 'L', 'tuesday': 'M', 'wednesday': 'X', 
                'thursday': 'J', 'friday': 'V', 'saturday': 'S', 'sunday': 'D'
            };
            return days.map(day => dayMap[day]).join(', ');
        }
        
        function updateTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('es-CO', {
                timeZone: 'America/Bogota',
                hour: '2-digit',
                minute: '2-digit'
            });
            document.getElementById('current-time').textContent = timeString;
        }
        
        updateTime();
        setInterval(updateTime, 60000);
        
        document.querySelectorAll('.day-chip').forEach(chip => {
            chip.addEventListener('click', function() {
                this.classList.toggle('active');
            });
        });
        
        document.getElementById('schedule-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                namespace: document.getElementById('namespace').value,
                timezone: document.getElementById('timezone').value,
                startup_time: document.getElementById('startup-time').value,
                shutdown_time: document.getElementById('shutdown-time').value,
                days_of_week: Array.from(document.querySelectorAll('.day-chip.active')).map(chip => chip.dataset.day),
                metadata: {
                    business_unit: document.getElementById('business-unit').value,
                    cost_savings_target: document.getElementById('cost-target').value
                }
            };
            
            try {
                const response = await fetch('/api/schedules', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    const newSchedule = await response.json();
                    schedules.push(newSchedule);
                    updateSchedulesList();
                    updateStats();
                    showAlert('Horario creado exitosamente', 'success');
                    
                    // Reset form
                    this.reset();
                    document.querySelectorAll('.day-chip').forEach(chip => {
                        chip.classList.remove('active');
                    });
                    ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].forEach(day => {
                        document.querySelector(`[data-day="${day}"]`).classList.add('active');
                    });
                } else {
                    const error = await response.json();
                    showAlert(`Error creando horario: ${error.error}`, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('Error de conexión con el servidor', 'error');
            }
        });
        
        function showAlert(message, type) {
            const alertContainer = document.getElementById('alert-container');
            const alertClass = type === 'success' ? 'alert-success' : 'alert-error';
            
            alertContainer.innerHTML = `<div class="alert ${alertClass}">${message}</div>`;
            
            setTimeout(() => {
                alertContainer.innerHTML = '';
            }, 4000);
        }
        
        // Cargar datos al iniciar
        loadData();
        
        // Recargar datos cada 30 segundos
        setInterval(loadData, 30000);
    </script>
</body>
</html>'''
    
    # Iniciar servidor de health check en puerto diferente
    health_server = HTTPServer(('0.0.0.0', 8081), HealthHandler)
    health_thread = threading.Thread(target=health_server.serve_forever)
    health_thread.daemon = True
    health_thread.start()
    logger.info("Started health check server on port 8081")
    
    logger.info("Starting namespace controller", timezone=str(tz), system_namespaces=list(system_ns))
    
    while True:
        try:
            now = datetime.now(tz)
            items = table.scan()['Items']
            
            for item in items:
                ns = item['namespace']
                if ns in get_namespaces():
                    schedules = item.get('schedules', [])
                    today = now.date().isoformat()
                    today_sched = next((s for s in schedules if s['date'] == today), None)
                    
                    if today_sched:
                        startup = datetime.strptime(today_sched['startup'], "%H:%M").time()
                        shutdown = datetime.strptime(today_sched['shutdown'], "%H:%M").time()
                        
                        if now.time() >= startup and now.time() < shutdown:
                            scale(ns, False)  # Encender
                        elif now.time() >= shutdown:
                            scale(ns, True)   # Apagar
                    else:
                        # Horario por defecto: Lun-Vie 13:00-20:00 UTC (8AM-3PM -05)
                        if (now.weekday() < 5 and 
                            now.time() >= datetime.strptime("13:00", "%H:%M").time() and 
                            now.time() < datetime.strptime("20:00", "%H:%M").time()):
                            scale(ns, False)  # Encender
                        elif (now.weekday() >= 5 or 
                              now.time() >= datetime.strptime("20:00", "%H:%M").time()):
                            scale(ns, True)   # Apagar
                            
        except Exception as e:
            logger.error("Main loop error", error=str(e))
            controller_errors.labels(error_type="main_loop_error").inc()
            
        time.sleep(300)  # Esperar 5 minutos

if __name__ == "__main__":
    main()