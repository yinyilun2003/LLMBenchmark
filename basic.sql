-- 创建用户表
CREATE TABLE benchmark_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100),
    permission_group INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 查询所有数据
SELECT * FROM benchmark_users;

-- 查询字段
SELECT email FROM benchmark_users;

SELECT * FROM benchmark_users WHERE permission_group >= 18;

-- 插入一条记录（INSERT）
INSERT INTO benchmark_users ( email, permission_group)
VALUES ('alice@example.com', 25);

-- 更新记录（UPDATE）
UPDATE benchmark_users SET permission_group = 26 WHERE email = 'alice@example.com';

-- 删除记录（DELETE）
DELETE FROM benchmark_users WHERE permission_group < 18;

-- 分页查询（LIMIT / OFFSET）
SELECT * FROM benchmark_users ORDER BY id LIMIT 10 OFFSET 0;

-- 查询数据表
SELECT tablename
FROM pg_catalog.pg_tables
WHERE schemaname = 'public';

-- 删除数据表
DROP TABLE benchmark_users;