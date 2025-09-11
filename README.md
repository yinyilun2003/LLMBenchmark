# LLMBenchmark
Document: https://docs.google.com/document/d/1Ng3m4Aw53Bcw__B4Gp4M9I-x3Zg1LlR748cfQhpihxE/edit?tab=t.kx0rpsdb8gui#heading=h.juc5wkcb4ct4

### 1. setup - 基础环境配置
1. Python 环境配置

推荐使用 pyenv + venv

安装依赖库：
fastapi uvicorn kafka-python psycopg2-binary
```
pip install fastapi uvicorn kafka-python psycopg2-binary
```
2. FastAPI 最小启动

创建 main.py：
```
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Hello, FastAPI"}

```
启动：

`uvicorn main:app --reload`


访问：http://127.0.0.1:8000

API文档：http://127.0.0.1:8000/docs

3. PostgreSQL 准备

推荐 Docker 快速拉起：

`docker run --name pg-dev -e POSTGRES_PASSWORD=devpass -p 5432:5432 -d postgres`


使用 psycopg2 测试连接

```
import psycopg2
conn = psycopg2.connect(
    dbname="postgres", user="postgres", password="devpass", host="localhost"
)
```

或者使用VScode 相关插件如 SQLtools

4. Kafka 环境说明

Docker 启动 Kafka
`docker-compose -f kafka.yaml up -d`

FastAPI + Kafka 简单log整合
引入`kafka_producer.py` 同时整合为FASTAPI http中间件用于获取log

使用`kafdrop`观察现象