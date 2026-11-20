import http.client
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

URL = os.getenv("STRESS_URL") or "http://localhost:8000/trending"
NUM_REQUESTS = int(os.getenv("STRESS_REQUESTS") or 1024)
CONCURRENT_THREADS = int(os.getenv("STRESS_THREADS") or 32)

parsed = urlparse(URL)
PATH = parsed.path + (f"?{parsed.query}" if parsed.query else "") or "/"
CONN_CLS = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
KEEP_ALIVE = {"Connection": "keep-alive"}

thread_local = threading.local()


def get_connection(reset=False):
    if reset and hasattr(thread_local, "conn"):
        thread_local.conn.close()
        del thread_local.conn
    if not hasattr(thread_local, "conn"):
        thread_local.conn = CONN_CLS(parsed.hostname, parsed.port, timeout=10)
    return thread_local.conn


def fetch_url():
    start_time = time.time()
    try:
        conn = get_connection()
        try:
            conn.request("GET", PATH, headers=KEEP_ALIVE)
            response = conn.getresponse()
        except http.client.HTTPException:
            conn = get_connection(reset=True)
            conn.request("GET", PATH, headers=KEEP_ALIVE)
            response = conn.getresponse()
        response.read()
        status_code = response.status
        result = "Success" if status_code == 200 else f"HTTP {status_code}"
    except Exception as e:
        status_code = 0
        result = f"Error: {e}"
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    return duration_ms, status_code, result

def run_stress_test():
    print(f"Starting stress test on {URL}")
    print(f"Requests: {NUM_REQUESTS}, Threads: {CONCURRENT_THREADS}")
    print("-" * 40)

    times = []
    errors = 0

    start_total = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        futures = [executor.submit(fetch_url) for _ in range(NUM_REQUESTS)]

        for future in as_completed(futures):
            duration, status, result = future.result()
            if "Error" in result or status != 200:
                errors += 1
                print(f"Request failed: {result} (Status: {status})")
            else:
                times.append(duration)
                # print(f"Request completed in {duration:.2f} ms")

    total_time = (time.time() - start_total) * 1000

    print("-" * 40)
    print("--- Results ---")
    if times:
        print(f"Total Requests: {NUM_REQUESTS}")
        print(f"Successful: {len(times)}")
        print(f"Failed: {errors}")
        print(f"Total Wall Time: {total_time:.2f} ms")
        print(f"Average Latency: {statistics.mean(times):.2f} ms")
        print(f"Median Latency: {statistics.median(times):.2f} ms")
        print(f"Min Latency: {min(times):.2f} ms")
        print(f"Max Latency: {max(times):.2f} ms")
    else:
        print("No successful requests.")
    print("-" * 40)

if __name__ == "__main__":
    run_stress_test()
