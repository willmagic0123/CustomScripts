#!/usr/bin/env python3
import time
import itertools
import string

charset = list(string.ascii_lowercase) + list(string.ascii_uppercase) + list(string.digits) + list("!@#$%?*()_+-=[]{}")

start_time = time.time_ns()
count = 0

for combo in itertools.product(charset, repeat=4):
    s = ''.join(combo)
    count += 1

end_time = time.time_ns()
elapsed_ns = end_time - start_time
elapsed_ms = elapsed_ns // 1000000
seconds = elapsed_ms // 1000
milliseconds = elapsed_ms % 1000
print(f"PYTHON - Combinaisons: {count} - Temps: {seconds}s {milliseconds}ms")
