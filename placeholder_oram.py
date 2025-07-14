# oram.py
import random
import time

class PathORAM:
    def __init__(self):
        self.logs = []

    def access(self, op, block_id):
        start = time.time()
        path = random.randint(0, 255)  # Simulated path P(x)
        latency = round(random.uniform(0.08, 0.12), 2) if op == 'PROTECTED' else round(random.uniform(0.01, 0.02), 2)
        log = {
            'time': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'access_type': 'READ',
            'block_id': block_id,
            'path': path,
            'latency': latency,
            'view': op
        }
        self.logs.append(log)
        return log

    def get_logs(self, view):
        return [log for log in self.logs if log['view'] == view]

    def clear_logs(self, view):
        self.logs = [log for log in self.logs if log['view'] != view]
