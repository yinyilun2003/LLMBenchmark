import asyncio
from sqlalchemy.orm import Session
from database import models, database
import json
from datetime import datetime

async def process_task(task: models.Task, db: Session):
    try:
        params = json.loads(task.params)
        wait = int(params.get("wait", 1))
        task.status = "running"
        db.commit()

        await asyncio.sleep(abs(wait))
        
        if wait >= 0:
            task.status = "finished"
            task.result = f"等待 {wait} 秒后成功完成"
        else:
            task.status = "failed"
            task.result = f"等待 {abs(wait)} 秒后失败"
        
        task.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        task.status = "failed"
        task.result = f"任务处理异常: {str(e)}"
        task.updated_at = datetime.utcnow()
        db.commit()


async def worker_loop():
    while True:
        db = next(database.get_db())
        task = db.query(models.Task).filter(models.Task.status == "pending").first()
        if task:
            await process_task(task, db)
        else:
            await asyncio.sleep(10)
