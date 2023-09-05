import time

class TimeTracker:
    def __init__(self):
        self.start_time = 0
        self.iterations = 0

    def start(self):
        self.start_time = time.time()
        self.iterations = 0

    def get_iterations_per_sec(self):
        self.iterations += 1
        total_sec = time.time() - self.start_time
        if total_sec == 0:
            total_sec = 0.001
        return self.iterations / total_sec
