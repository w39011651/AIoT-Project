import mysql.connector

def create_connection():
    connection = mysql.connector.connect(
         host="database-3.chqsqk42y3iv.us-east-1.rds.amazonaws.com",
        user="admin",
        password="33818236",
        database="demo_database",
        table="workout_data"
    )
    return connection

def insert_data(connection, data):
    cursor = connection.cursor()
    data = []
    for i in range(10):
        data.append([f'User{i+1}', 20+i])
    sql = "INSERT INTO sample (name, age) VALUES (%s, %s)"
    for i in range(10):
        cursor.execute(sql, (data[i][0], data[i][1]))
        connection.commit()
    cursor.close()

def fetch_data(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sample")
    result = cursor.fetchall()
    for row in result:
        print(row)
    cursor.close()

if __name__ == "__main__":
    connection = create_connection()
    insert_data(connection, [])
    fetch_data(connection)
    connection.close()