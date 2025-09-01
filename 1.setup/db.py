import psycopg2
conn = psycopg2.connect(
    dbname="postgres", user="postgres", password="devpass", host="localhost"
)


print("connect to db successfully!")