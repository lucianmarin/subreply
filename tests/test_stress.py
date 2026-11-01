import concurrent.futures
import time
import requests
import statistics

URL = "http://localhost:8000/api/trending"
NUM_REQUESTS = 1024
CONCURRENT_THREADS = 32

def fetch_url(url):
    start_time = time.time()
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        status_code = response.status_code
        result = "Success"
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        futures = [executor.submit(fetch_url, URL) for _ in range(NUM_REQUESTS)]

        for future in concurrent.futures.as_completed(futures):
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
