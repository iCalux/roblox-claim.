from .threads import group_scanner
from .utils import slice_range
from queue import Queue, Empty
from threading import Thread
from time import sleep

def worker_func(thread_count, log_queue, count_queue, proxy_list, gid_ranges,
                **thread_kwargs):    
    local_count_queue = Queue()
    proxy_iter = __import__("itertools").cycle(proxy_list)
    threads = []

    for thread_num in range(thread_count):
        thread = Thread(
            target=group_scanner,
            name=f"Scanner-{thread_num}",
            daemon=True,
            kwargs=dict(
                log_queue=log_queue,
                count_queue=local_count_queue,
                proxy_iter=proxy_iter,
                gid_ranges=[
                    slice_range(gid_range, thread_num, thread_count)
                    for gid_range in gid_ranges
                ],
                **thread_kwargs
            )
        )
        threads.append(thread)
    
    for thread in threads:
        thread.start()
    
    try:
        while any(t.is_alive() for t in threads):
            chunk = []
            while True:
                try:
                    ts, count = local_count_queue.get(block=False)
                    chunk.append((ts, count))
                except Empty:
                    break
            if chunk:
                count_queue.put(chunk)
            sleep(1)
    except KeyboardInterrupt:
        pass