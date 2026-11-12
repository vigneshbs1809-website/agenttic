import asyncio

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
print("Testing selector loop...", flush=True)

async def f():
    print("INSIDE ASYNC WITH SELECTOR!", flush=True)

asyncio.run(f())
print("SELECTOR LOOP WORKS!", flush=True)

