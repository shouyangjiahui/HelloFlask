from db_sqlite3 import *
from flask import flash, Flask, make_response, redirect, render_template, request, send_from_directory, session, url_for, send_file
from io import BytesIO
import json
import math
import openpyxl
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import random
import re
from sqlalchemy import create_engine
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'abcdefghijklmnopqrstuvwxyz'


# 检查登录状态
def check_login():
    return False if 'username' not in session else True
    # if 'username' not in session:
    #     return False
    # else:
    #     return True


# 验证码图片
def validate_picture():
    width = 120
    heighth = 60
    im = Image.new('RGB', (width, heighth), 'white')  # 生成一个新的图片对象
    font = ImageFont.truetype('arial.ttf', 40)  # 设置字体
    draw = ImageDraw.Draw(im)  # 创建draw对象
    str = ''
    # 输出每一个文字
    for item in range(5):
        text = random.choice(app.secret_key)
        str += text
        draw.text((5 + random.randint(4, 7) + 20 * item, 5 + random.randint(3, 7)),
                  text=text, fill='black', font=font)
    # 增加干扰线
    for _ in range(8):
        x1 = random.randint(0, width / 2)
        y1 = random.randint(0, heighth / 2)
        x2 = random.randint(0, width)
        y2 = random.randint(heighth / 2, heighth)
        draw.line(((x1, y1), (x2, y2)), fill='black', width=1)
    im = im.filter(ImageFilter.FIND_EDGES)  # 模糊 + 滤镜
    return im, str  # 返回验证码图片和验证码字符串


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/code')
def get_code():
    image, str = validate_picture()
    # 将验证码图片以二进制形式写入在内存中，避免将图片都放在文件夹中，占用大量磁盘
    buf = BytesIO()
    image.save(buf, 'jpeg')
    buf_str = buf.getvalue()
    # 把二进制作为response发回前端，并设置首部字段
    response = make_response(buf_str)
    response.headers['Content-Type'] = 'image/jpeg'
    # 将验证码字符串储存在session中
    session['image'] = str
    return response


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '')
    password = request.form.get('pwd', '')
    # 合法性检测
    if username == "":
        return render_template('login.html', error="用户名不可以为空")
    if password == "":
        return render_template('login.html', error="密码不可以为空")
    # 验证验证码
    user_input = request.form.get('captcha_input', '')
    captcha_text = session.get('image', '')
    if user_input.lower() != captcha_text.lower():
        # 验证码错误，保留原始的用户名和密码
        return render_template('login.html', error='验证码错误', username=username, password=password)
    # 进行密码解密
    result, _ = get_sql2(f"select * from users where username = '{request.form['username']}' ")
    if len(result) > 0:
        session['username'] = result[0][0]
        encoded_pwd = result[0][1]
        if check_password_hash(str(encoded_pwd), str(request.form['pwd'])):
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="用户名或密码错误", username=username)
    else:
        return render_template('login.html', error="用户名或密码错误", username=username)


@app.route('/goback')
def goback():
    return redirect(url_for('index'))


@app.route('/', methods=['GET'])
def index():
    msg = request.args.get('msg', '')
    if not check_login():
        return redirect(url_for('login'))
    
    page = int(request.args.get('page', 1))  # 默认显示第一页
    per_page = int(request.args.get('per_page', 5))  # 默认每页显示5条数据

    sql = "select s.*, p.stu_profession" \
          " from student_info s inner join stu_profession p on s.stu_profession_id = p.stu_profession_id"
    str_where = []
    stu_name = ''
    stu_id = ''
    if 'stu_name' in request.args:
        stu_name = request.args['stu_name']
        if stu_name != '':
            # % 匹配任意多个字符 _ 匹配任意一个字符
            str_where.append(f" stu_name like '%{stu_name}%'")
    if 'stu_id' in request.args:
        stu_id = request.args['stu_id']
        if stu_id != '':
            str_where.append(f" stu_id = '{stu_id}'")
    if len(str_where) > 0:
        sql = sql + ' where' + ' and'.join(str_where)

    mid_res, _ = get_sql2(sql)
    num_row = len(mid_res)  # 符合条件的记录数量
    start_index = (page - 1) * per_page
    sql += f' limit {start_index}, {per_page}'
    result, fields = get_sql2(sql)
    total_pages = math.ceil(num_row / per_page)  # 使用 math.ceil 向上取整

    if num_row > 0 and msg == '' and (stu_name != "" or stu_id != ""):
        msg = "查询成功!"
    elif str_where != '' and num_row == 0:
        msg = "查询失败!"
    return render_template('index.html', datas=result, fields=fields, page=page, per_page=per_page, total_pages=total_pages, 
                           msg=msg, stu_id=stu_id, stu_name=stu_name)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if not check_login():
        return redirect(url_for('login'))

    if request.method == "GET":
        datas, _ = get_sql2("select * from stu_profession")
        return render_template('add.html', datas=datas)
    else:
        stu_id = request.form['stu_id']
        stu_name = request.form['stu_name']
        stu_age = request.form['stu_age']

        # 验证学号是否为九位数字
        if not stu_id.isdigit() or len(stu_id) != 9:
            return "学号必须是九位数字"

        # 验证姓名是否由汉语或英语字符组成且不超过二十个字符
        name_regex = "^[\u4e00-\u9fa5a-zA-Z]{1,20}$"
        if not re.match(name_regex, stu_name):
            return '姓名必须是汉语或者英语字符且不超过二十个字符'

        # 验证年龄是否为数字且在一到一百二十之间
        try:
            stu_age = int(stu_age)
            if stu_age < 1 or stu_age > 120:
                return '年龄必须在一到一百二十之间'
        except ValueError:
            return '年龄必须为数字'

        data = dict(
            stu_id=request.form['stu_id'],
            stu_name=request.form['stu_name'],
            stu_sex=request.form['stu_sex'],
            stu_age=request.form['stu_age'],
            stu_origin=request.form['stu_origin'],
            stu_profession_id=request.form['stu_profession']
        )

        if insert_data(data, "student_info"):
            return redirect(url_for("index", msg='添加成功'))
        else:
            return redirect(url_for("index", msg='学号已存在，添加失败'))


# 使用Excel批量添加学生数据
@app.route('/add_by_excel', methods=['POST'])
def add_by_excel():
    excel_file = request.files["file"]
    if excel_file:
        engine = create_engine('sqlite:///db/students.db')
        df = pd.read_excel(excel_file)  # 首行作为数据库的属性
        df.to_sql('student_info', engine, if_exists="append", index=False)
        return "数据已成功添加！"
    return "数据添加失败"


@app.route('/export_to_excel')
def export_to_excel():
    # 获取数据库中的表格数据（这里使用假数据代替）
    data = [
        ['stu_id', 'stu_name', 'stu_sex', 'stu_age', 'stu_origin', 'stu_profession_id']
    ]
    sql = 'select * from student_info'
    res, fields = get_sql2(sql)
    for row in res:
        l_row = []
        for item in row:
            l_row.append(str(item))
        data.append(l_row)
    # 创建一个新的Excel工作簿
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    # 逐行写入数据
    for row in data:
        row = list(row)
        sheet.append(row)
    # 将Excel文件保存到内存中
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    # 返回Excel文件作为响应，并设置相关的响应头
    return send_file(
        output,
        download_name='exported_data.xlsx',
        as_attachment=True,
    )


@app.route('/del', methods=['GET'])
def delete():
    if not check_login():
        return redirect(url_for('login'))
    stu_id = request.args['stu_id']
    delete_data_by_id('stu_id', stu_id, 'student_info')
    return redirect(url_for('index', msg='删除成功'))


@app.route('/operations', methods=['POST', 'GET'])
def batch_operations():
    if not check_login():
        return redirect(url_for('login'))

    action = request.form['action']
    if action == '批量删除':
        checked_sno_list = request.form.getlist('checked_sno')
        for sno in checked_sno_list:
            delete_data_by_id('stu_id', sno, 'student_info')
        flash("批量删除成功.", "success")
        return redirect(url_for('index', msg='批量删除成功'))


@app.route('/update_age', methods=['GET', 'POST'])
def update_age():
    msg = request.args.get('msg', '')
    if not check_login():
        return redirect(url_for('login'))

    page = int(request.args.get('page', 1))  # 默认显示第一页
    per_page = int(request.args.get('per_page', 5))  # 默认每页显示10条数据

    sql = "select s.*, p.stu_profession" \
          " from student_info s inner join stu_profession p on s.stu_profession_id = p.stu_profession_id"
    str_where = []
    stu_name = ''
    stu_id = ''
    if 'stu_name' in request.args:
        stu_name = request.args['stu_name']
        if stu_name != '':
            str_where.append(f" stu_name like '%{stu_name}%'")  # % 匹配任意多个字符 _ 匹配任意一个字符

    if 'stu_id' in request.args:
        stu_id = request.args['stu_id']
        if stu_id != '':
            str_where.append(f" stu_id = '{stu_id}'")

    if len(str_where) > 0:
        sql = sql + ' where' + ' and'.join(str_where)

    mid_res, _ = get_sql2(sql)
    num_row = len(mid_res)  # 符合条件的记录数量
    # print(f"num_row:{num_row}")

    start_index = (page - 1) * per_page
    sql += f' limit {start_index}, {per_page}'

    result, fields = get_sql2(sql)
    # print(f"result:{len(result)}")
    total_pages = math.ceil(num_row / per_page)  # 使用 math.ceil 向上取整

    # print(page, per_page, total_pages)
    if num_row > 0 and msg == '' and (stu_name != "" or stu_id != ""):
        msg = "更新成功"
        flash("更新成功.", "success")
    elif str_where != '' and num_row == 0:
        msg = "查无此人"
        flash('查无此人')

    if 'stu_name' in request.args and 'stu_id' in request.args:
        if not request.args['stu_name'] and not request.args['stu_id']:
            msg = "学号和姓名不能为空！"

    # return render_template('index.html', datas=result, fields=fields)
    return render_template('update_age.html', datas=result, fields=fields, page=page, per_page=per_page, total_pages=total_pages, msg=msg, stu_id=stu_id, stu_name=stu_name)


@app.route('/del2/<stu_id>', methods=['GET'])
def delete2(stu_id):
    if not check_login():
        return redirect(url_for('login'))
    delete_data_by_id('stu_id', stu_id, 'student_info')
    return redirect(url_for('index', msg='删除成功'))


# 批量修改专业
@app.route('/update_profession', methods=['GET', 'POST'])
def update_profession():
    if request.method == 'GET':
        sql = "select s.*, p.stu_profession" \
          " from student_info s inner join stu_profession p on s.stu_profession_id = p.stu_profession_id"
        datas, fields = get_sql2(sql)
        pros, _ = get_sql2("select * from stu_profession")
        return render_template('update_profession.html', datas=datas, fields=fields, pros=pros)
    else:
        stu_id = request.form.getlist('stu_id_list')
        for id in stu_id:
            pro_id = request.form[id+"_pro"]
            data = dict(
                stu_id=id,
                stu_profession_id=pro_id
            )
            update_data(data, 'student_info')
        return redirect(url_for('index'))


# 批量修改年龄
@app.route('/save_edited_data', methods=['POST'])
def save_edited_data():
    stu_ids = request.form.getlist('stu_id[]')
    stu_ages = request.form.getlist('stu_age[]')
    for age in stu_ages:
        try:
            age = int(age)
            if age < 1 or age > 120:
                flash('年龄必须在一到一百二十之间')
                return redirect(url_for('update_age'))
        except ValueError:
            flash('年龄必须为整数')
            return redirect(url_for('update_age'))
    data = dict(zip(stu_ids, stu_ages))

    original_data = get_original_data(stu_ids)  # 获取原始数据

    if original_data and original_data[0]['stu_id'] == int(stu_ids[0]):
        print("123")

    modified_data = []  # 用于存储已修改的数据

    for stu_id, new_age in zip(stu_ids, stu_ages):
        stu_id_int = int(stu_id)  # 将stu_id转换为整数
        for student_data in original_data:
            if student_data['stu_id'] == stu_id_int and int(new_age) != student_data['stu_age']:
                data = dict(
                    stu_id=stu_id,
                    stu_age=int(new_age)
                )
                update_data(data, 'student_info')
                modified_data.append(stu_id_int)

    if modified_data:
        flash("修改成功.", "success")
        return redirect(url_for('update_age'))
    else:
        flash('没有数据发生修改')
        return redirect(url_for('update_age'))


@app.route('/update', methods=['GET', 'POST'])
def update():
    if not check_login():
        return redirect(url_for('login'))

    if request.method == 'GET':
        stu_id = request.args['stu_id']
        result, _ = get_sql2(f"select * from student_info where stu_id = '{stu_id}' ")
        datas, _ = get_sql2('select * from stu_profession')
        return render_template('update.html', data=result[0], datas=datas)
    else:
        data = dict(
            stu_id=request.form['stu_id'],
            stu_name=request.form['stu_name'],
            stu_sex=request.form['stu_sex'],
            stu_age=request.form['stu_age'],
            stu_origin=request.form['stu_origin'],
            stu_profession_id=request.form['stu_profession']
        )
        update_data(data, 'student_info')
        return redirect(url_for('index'))


@app.route('/goprofession')
def gopro():
    results, _ = get_sql2("select * from stu_profession")
    # results = select_prof()
    return render_template('addprofession.html', results=results)


@app.route('/save_pro', methods=['POST'])
def save_data():
    if request.method == 'POST':
        my_input_value = request.form.get('myInput')
        if not my_input_value or my_input_value.strip() == "":
            flash("输入不能为空.")
            results, _ = get_sql2("select * from stu_profession")
            # results = select_prof()
            return render_template('addprofession.html', results=results)
        existing_data, _ = get_sql2('select * from stu_profession where stu_profession=' + '"' + my_input_value + '"')
        # existing_data = select_prof_by_name(name=my_input_value)
        if existing_data:
            flash("数据重复，请输入其他值.")
            results, _ = get_sql2("select * from stu_profession")
            # results = select_prof()
            return render_template('addprofession.html', results=results)
        # 调用插入函数将数据插入到数据库
        insert_pro(name=my_input_value)
        # 重新查询数据，以便在页面上显示更新后的结果
        results, _ = get_sql2("select * from stu_profession")
        # results = select_prof()
        # 渲染模板并传递查询结果
        flash("添加成功.", "success")
        return render_template('addprofession.html', results=results)


@app.route('/del_pro/<id>', methods=['GET'])
def delete_prof(id):
    delete_pro(id)
    return redirect(url_for('gopro'))


@app.route('/charts')
def charts():
    sql = "SELECT p.stu_profession, COUNT(s.stu_profession_id) as count FROM student_info s INNER JOIN stu_profession p " \
          "on s.stu_profession_id=p.stu_profession_id GROUP BY p.stu_profession"
    conn = open_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    data = [{"name": row["stu_profession"], "value": row["count"]} for row in data]
    data = json.dumps(data)
    return render_template('charts.html', data=data)


@app.route('/quit')
def quit():
    session.pop('username')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
