import uvicorn
from fastapi import FastAPI
# from kafka_producer import send_log_to_kafka
# import time

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Hello, FastAPI"}

# @app.middleware("http")
# async def log_requests(request, call_next):
#     start_time = time.time()

#     response = await call_next(request)

#     process_time = time.time() - start_time
#     log_data = {
#         "method": request.method,
#         "url": str(request.url),
#         "status_code": response.status_code,
#         "process_time_ms": round(process_time * 1000, 2),
#         "client_ip": request.client.host
#         # 可扩展为：用户ID、JWT解码内容等
#     }
#     send_log_to_kafka(log_data)
#     return response

if __name__ == "__main__":
    uvicorn.run(app, port=8000)