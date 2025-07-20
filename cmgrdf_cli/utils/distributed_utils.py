from dask.distributed import Scheduler, Client
import asyncio
import multiprocessing
import os

def run_dask_scheduler(queue):
    async def start_scheduler():
        scheduler = Scheduler(dashboard_address=":0", port = 8786)
        await scheduler.start()
        queue.put(scheduler.address)
        await scheduler.finished()
    asyncio.run(start_scheduler())

def get_schedulerProc_and_client(lxdask_options, ncpu):
    scheduler_address_queue = multiprocessing.Queue()
    scheduler_process = multiprocessing.Process(
        target=run_dask_scheduler,
        args=(scheduler_address_queue,)
    )
    scheduler_process.start()
    try:
        scheduler_address = scheduler_address_queue.get(timeout=30)
        print(f"Dask Scheduler Address received: {scheduler_address}")
    except Exception as e:
        print(f"Error: Did not receive scheduler address from queue within timeout: {e}")
        scheduler_process.terminate()
        scheduler_process.join(timeout=5)
        if scheduler_process.is_alive():
            scheduler_process.kill()
        exit(1)

    os.system(os.path.join(os.environ['CMGRDF'], f"examples/lxdask_worker_submit.py {lxdask_options}"))
    try:
        client = Client(scheduler_address)
        client.run(exec, "import faulthandler\nfaulthandler.enable()")
        client.run(exec, f"import  ROOT")
        client.run(exec, f"ROOT.EnableImplicitMT({ncpu})")

        print(f"Successfully connected to Dask scheduler at: {scheduler_address}")
        print(f"Dask Dashboard Link: {client.dashboard_link}")
    except Exception as e:
        print(f"Error connecting Dask client or running computation: {e}")
    return scheduler_process, client

