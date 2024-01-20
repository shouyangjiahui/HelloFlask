import sqlite3


def open_db():
    database = 'db/students.db'
    conn = sqlite3.connect(database)
    return conn


def get_sql(conn, sql):
    print(sql)
    cur = conn.cursor()
    cur.execute(sql)
    fields = []  # 保存字段信息
    for field in cur.description:
        fields.append(field[0])
    result = cur.fetchall()  # 保存查询结果
    cur.close()
    return result, fields


def close_db(conn):
    conn.close()


def get_sql2(sql):
    conn = open_db()
    result, fields = get_sql(conn, sql)
    close_db(conn)
    return result, fields


def update_data(data, table_name):
    conn = open_db()
    cur = conn.cursor()
    values = []
    id_name = list(data.keys())[0]
    for v in list(data)[1:]:
        values.append(f"{v}='{data[v]}'")
    sql = f"update {table_name} set {','.join(values)} where {id_name} = '{data[id_name]}'"
    print(sql)
    cur.execute(sql)

    conn.commit()
    cur.close()
    close_db(conn)


def insert_data(data, table_name):
    conn = open_db()
    cur = conn.cursor()
    field_names = list(data.keys())  # data字典的键
    values = list(data.values())  # data字典的值
    sql_p = f"select * from {table_name} where stu_id = {values[0]}"
    result, _ = get_sql2(sql_p)
    if len(result) > 0:
        return False
    sql = f"insert into {table_name} ({','.join(field_names)}) values ({','.join(['?'] * len(field_names))})"
    print(sql)
    cur.execute(sql, values)
    conn.commit()

    cur.close()
    close_db(conn)
    return True


def delete_data_by_id(id, value, table_name):
    conn = open_db()
    cursor = conn.cursor()
    
    sql = f"delete from {table_name} where {id} = ?"
    cursor.execute(sql, (value,))
    conn.commit()

    cursor.close()
    close_db(conn)


def get_original_data(stu_ids):
    conn = open_db()
    cursor = conn.cursor()

    table_name = 'student_info'
    original_data = []
    for stu_id in stu_ids:
        sql = f"select stu_id, stu_age from {table_name} where stu_id = ?"
        cursor.execute(sql, (stu_id,))
        row = cursor.fetchone()

        if row:
            stu_id, stu_age = row
            original_data.append({'stu_id': stu_id, 'stu_age': stu_age})

    cursor.close()
    close_db(conn)

    return original_data


def insert_pro(name):
    conn = open_db()
    cur = conn.cursor()

    cur.execute("select count(*) from stu_profession")
    count = cur.fetchone()[0]
    next_id = count + 1
    sql = "insert into stu_profession (stu_profession_id, stu_profession) values (?, ?)"
    values = (next_id, name)
    cur.execute(sql, values)
    conn.commit()
    
    cur.close()
    close_db(conn)


def delete_pro(id):
    conn = open_db()
    cur = conn.cursor()

    cur.execute("select stu_profession_id from stu_profession where stu_profession_id=?", (id,))
    deleted_id = cur.fetchone()[0]

    cur.execute("delete from stu_profession where stu_profession_id=?", (id,))

    cur.execute("SELECT MAX(stu_profession_id) FROM stu_profession")
    max_id = cur.fetchone()[0]

    if deleted_id < max_id:
        cur.execute("update stu_profession set stu_profession_id = stu_profession_id - 1 where stu_profession_id > ?", (deleted_id,))
    
    conn.commit()
    cur.close()
    close_db(conn)
