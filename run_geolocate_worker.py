from redis import Redis
from rq import Worker, Queue, Connection

if __name__ == '__main__':
    redis_conn = Redis()
    with Connection(redis_conn):
        worker = Worker(['geolocation'])
        worker.work()
