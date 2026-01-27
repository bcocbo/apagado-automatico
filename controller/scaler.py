import boto3, os, time, subprocess, datetime, pytz, croniter
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
tz = pytz.timezone(os.environ['TIMEZONE'])
system_ns = set(os.environ['SYSTEM_NAMESPACES'].split(','))

def get_namespaces():
    return [ns for ns in subprocess.check_output(["kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"]).decode().split() if ns not in system_ns]

def scale(ns, to_zero):
    action = "Apagado" if to_zero else "Encendido"
    deps = subprocess.check_output(["kubectl", "get", "deploy", "-n", ns, "-o", "custom-columns=NAME:.metadata.name", "--no-headers"]).decode().split()
    for dep in deps:
        if to_zero:
            current = subprocess.check_output(["kubectl", "get", "deploy", dep, "-n", ns, "-o", "jsonpath={.spec.replicas}"]).decode().strip()
            if current and int(current) > 0:
                subprocess.run(["kubectl", "annotate", "deploy", dep, "-n", ns, f"original-replicas={current}", "--overwrite"])
                subprocess.run(["kubectl", "scale", "deploy", dep, "-n", ns, "--replicas=0"])
        else:
            orig = subprocess.check_output(["kubectl", "get", "deploy", dep, "-n", ns, "-o", "jsonpath={.metadata.annotations.original-replicas}"]).decode().strip()
            if orig:
                subprocess.run(["kubectl", "scale", "deploy", dep, "-n", ns, f"--replicas={orig}"])
                subprocess.run(["kubectl", "annotate", "deploy", dep, "-n", ns, "original-replicas-"])
    subprocess.run(["kubectl", "create", "event", "-n", ns, "--type=Normal", f"--reason=Auto{action}", f"{action} automático"])

while True:
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
                    scale(ns, False)  # Encender si dentro del rango
                elif now.time() >= shutdown:
                    scale(ns, True)
            else:
                # Default: Lun-Vie 13:00-20:00 UTC (8AM-3PM -05)
                if now.weekday() < 5 and now.time() >= datetime.strptime("13:00", "%H:%M").time() and now.time() < datetime.strptime("20:00", "%H:%M").time():
                    scale(ns, False)
                elif now.weekday() >= 5 or now.time() >= datetime.strptime("20:00", "%H:%M").time():
                    scale(ns, True)
    time.sleep(300)  # Cada 5 min