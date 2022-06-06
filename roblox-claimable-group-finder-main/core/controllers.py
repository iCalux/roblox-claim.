from .workers import worker_func
from .threads import log_notifier, stat_updater
from .utils import slice_list, slice_range, parse_proxy_string
from multiprocessing import Process, Queue
from threading import Thread

class Controller:
    def __init__(self, arguments):
        self.arguments = arguments
        self.workers = []
        self.proxies = []
        self.count_queue = Queue()
        self.log_queue = Queue()
        
        if self.arguments.proxy_file:
            self.load_proxies()

        self.start_stat_updater()
        self.start_log_notifier()
        self.start_workers()

    def load_proxies(self):
        proxies = set()
        with self.arguments.proxy_file as fp:
            line_num = 0
            while (line := fp.readline()):
                try:
                    proxy = parse_proxy_string(line.rstrip())
                    if not proxy in proxies:
                        proxies.add(proxy)
                except Exception as err:
                    print(f"Error while parsing line {line_num+1} in proxy file: {err!r}")
                finally:
                    line_num += 1
        assert proxies, "Proxy file is empty."
        self.proxies.extend(proxies)

    def start_log_notifier(self):
        thread = Thread(
            target=log_notifier,
            name="LogNotifier",
            daemon=True,
            args=(self.log_queue, self.arguments.webhook_url))
        thread.start()

    def start_stat_updater(self):            
        thread = Thread(
            target=stat_updater,
            name="StatUpdater",
            daemon=True,
            args=(self.count_queue,))
        thread.start()

    def start_workers(self):
        for worker_num in range(self.arguments.workers):
            worker = Process(
                target=worker_func,
                name=f"Worker-{worker_num}",
                daemon=True,
                kwargs=dict(
                    thread_count=self.arguments.threads,
                    log_queue=self.log_queue,
                    count_queue=self.count_queue,
                    proxy_list=slice_list(self.proxies, worker_num, self.arguments.workers),
                    timeout=self.arguments.timeout,
                    gid_ranges=[
                        slice_range(gid_range, worker_num, self.arguments.workers)
                        for gid_range in self.arguments.range
                    ],
                    gid_cutoff=self.arguments.cut_off,
                    gid_chunk_size=self.arguments.chunk_size
                )
            )
            self.workers.append(worker)
        
        for worker in self.workers:
            worker.start()

    def join_workers(self):
        for worker in self.workers:
            worker.join()