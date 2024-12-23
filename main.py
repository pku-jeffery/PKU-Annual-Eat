import os
import re
import json
import random
import threading
import webbrowser
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import requests
import platform
from datetime import datetime
from flask import Flask, jsonify, request, send_file
app = Flask(__name__)

def generate_image(use_password, account, hallticket, sdate, edate):
    all_data = dict()

    # 默认日期
    default_sdate = "2024-01-01"
    default_edate = "2024-12-31"

    def is_valid_date(date_str):
        """检查日期是否符合YYYY-MM-DD格式且为有效日期"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    def format_date(date_str):
        """确保日期始终以两位数显示月份和日期"""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%d")  # 格式化为YYYY-MM-DD

    # 获取用户输入的开始日期
    if not is_valid_date(sdate):
        sdate = default_sdate
    else:
        sdate = format_date(sdate)

    # 获取用户输入的结束日期
    if not is_valid_date(edate):
        edate = default_edate
    else:
        edate = format_date(edate)

    # 发送请求，得到加密后的字符串
    url = f"https://card.pku.edu.cn/Report/GetPersonTrjn"
    post_data = {
        "sdate": sdate,
        "edate": edate,
        "account": account,
        "page": "1",
        "rows": "9000",
    }

    if use_password:
        # 不知道为什么，有时候可能失败，失败的话重试几次
        for _ in range(3):
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'https://card.pku.edu.cn/User/Account',
            })

            login_url = 'https://iaaa.pku.edu.cn/iaaa/oauthlogin.do'
            login_data = {
                'appid': 'card_auth',
                'userName': account,
                'password': hallticket,
                'redirUrl': 'http://sfrzcard.pku.edu.cn/ias/prelogin?sysid=WXXY'
            }
            redirect_url = 'http://sfrzcard.pku.edu.cn/ias/prelogin?sysid=WXXY'
            response = session.post(login_url, data=login_data)
            result = json.loads(response.text)
            if not result['success']:
                return False
            response = session.get(redirect_url + '&_rand=' + str(random.random()) + '&token=' + result['token'])
            match = re.search(r'value="([a-fA-F0-9]{32})"', response.text)
            if not match:
                return generate_image
            
            ssoticketid = match.group(1)
            response = session.post('https://card.pku.edu.cn/cassyno/index', data={'ssoticketid': ssoticketid})  # 获取 Cookies 
            # print(response.text)
            # print(session.cookies)

            response = session.post('https://card.pku.edu.cn/User/GetCardInfo', data={'json': 'true'})
            try:
                real_account = json.loads(json.loads(response.text)['Msg'])['query_card']['card'][0]['account']
            except TypeError:
                continue

            post_data['account'] = real_account
            response = session.post(url, data=post_data)
            break
    else:
        cookie = {
            "hallticket": hallticket,
        }
        response = requests.post(url, cookies=cookie, data=post_data)
        print(response.text)

    try:
        data = json.loads(response.text)["rows"]
    except json.decoder.JSONDecodeError:
        return False

    # 整理数据
    for item in data:
        try:
            if(item["TRANAMT"] < 0):
                if item["MERCNAME"].strip() in all_data:
                    all_data[item["MERCNAME"].strip()] += abs(item["TRANAMT"])
                else: 
                    all_data[item["MERCNAME"].strip()] = abs(item["TRANAMT"])
        except Exception as e:
            pass
    all_data = {k: round(v, 2) for k, v in all_data.items()}
    summary = f"统计总种类数：{len(all_data)}\n总消费次数：{len(data)}\n总消费金额：{round(sum(all_data.values()), 1)}"
    print(summary)
    # 输出结果
    all_data = dict(sorted(all_data.items(), key=lambda x: x[1], reverse=False))
    
    if platform.system() == "Darwin":
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
    elif platform.system() == "Linux":
        plt.rcParams['font.family'] = ['Droid Sans Fallback', 'DejaVu Sans']
    else:
        plt.rcParams['font.sans-serif'] = ['SimHei']
        
    plt.figure(figsize=(12, len(all_data) / 66 * 18))
    plt.barh(list(all_data.keys()), list(all_data.values()))
    for index, value in enumerate(list(all_data.values())):
        plt.text(value + 0.01 * max(all_data.values() or [0]),
                index,
                str(value),
                va='center')
        
    # plt.tight_layout()
    plt.xlim(0, 1.2 * max(all_data.values() or [0]))
    plt.title(f"白鲸大学食堂消费情况\n({post_data['sdate']} 至 {post_data['edate']})")
    plt.xlabel("消费金额（元）")
    plt.text(0.8, 0.1, summary, ha='center', va='center', transform=plt.gca().transAxes)
    plt.savefig("result.png", bbox_inches='tight', dpi=300)
    # plt.show()
    return True


index_html = '''
<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>食堂消费统计</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }

        form {
            background: #ffffff;
            padding: 50px;
            border-radius: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }

        h2 {
            text-align: center;
            margin-bottom: 20px;
            color: #333333;
        }

        label {
            display: block;
            margin-bottom: 8px;
            color: #555555;
        }

        input, select {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #dddddd;
            border-radius: 4px;
            box-sizing: border-box;
        }

        button {
            width: 100%;
            padding: 10px;
            background-color: #007BFF;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }

        button:hover {
            background-color: #0056b3;
        }

        button:active {
            background-color: #003f7f;
        }
    </style>
    <script>
        function updateLabels() {
            const type1 = document.getElementById('loginType').value === 'type1';
            document.querySelector('label[for="username"]').textContent = type1 ? "账号：" : "学号：";
            document.querySelector('label[for="password"]').textContent = type1 ? "Hallticket：" : "密码：";
        }

        function saveToCookies() {
            document.cookie = `loginType=${document.getElementById('loginType').value}; path=/; max-age=31536000`;
            document.cookie = `username=${document.getElementById('username').value}; path=/; max-age=31536000`;
            document.cookie = `password=${document.getElementById('password').value}; path=/; max-age=31536000`;
            document.cookie = `startDate=${document.getElementById('startDate').value}; path=/; max-age=31536000`;
            document.cookie = `endDate=${document.getElementById('endDate').value}; path=/; max-age=31536000`;
        }

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        function populateFromCookies() {
            const loginType = getCookie('loginType');
            const username = getCookie('username');
            const password = getCookie('password');
            const startDate = getCookie('startDate');
            const endDate = getCookie('endDate');

            if (loginType) document.getElementById('loginType').value = loginType;
            if (username) document.getElementById('username').value = username;
            if (password) document.getElementById('password').value = password;
            if (startDate) document.getElementById('startDate').value = startDate;
            if (endDate) document.getElementById('endDate').value = endDate;

            updateLabels();
        }


        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('loginType').addEventListener('change', updateLabels);
            document.querySelector('form').addEventListener('submit', saveToCookies);
            populateFromCookies();
        });
    </script>
</head>
<body>
    <form action="/generate" method="GET" target="_blank">
        <h2>生成食堂消费统计</h2>

        <label for="loginType">鉴权方式：</label>
        <select id="loginType" name="loginType">
            <option value="type1">Cookie</option>
            <option value="type2">用户名密码</option>
        </select>

        <label for="username">Username:</label>
        <input type="text" id="username" name="username" required>

        <label for="password">Password:</label>
        <input type="text" id="password" name="password" required>

        <label for="startDate">开始日期：</label>
        <input type="date" id="startDate" name="startDate" value="2024-01-01" required>

        <label for="endDate">结束日期：</label>
        <input type="date" id="endDate" name="endDate" value="2024-12-31" required>

        <button type="submit">生成</button>
    </form>
</body>
</html>
'''
image_html = '''
<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>消费情况</title>
    <style>
        body {
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .responsive-img {
            max-width: 100vw;
            max-height: 90vh;
            width: auto;
            height: auto;
            display: block;
        }
    </style>
</head>
<body>
    <img src="/image" alt="消费情况" class="responsive-img">
</body>
</html>
'''

@app.route('/', methods=['GET'])
def input_acount_info():
    # with open('index.html', 'r', encoding='utf-8') as file:
    #     return file.read()
    return index_html

@app.route('/generate', methods=['GET'])
def generate():
    use_password = request.args.get('loginType', '') == 'type2'
    account = request.args.get('username', '')
    passcode = request.args.get('password', '')
    sdate = request.args.get('startDate', '2024-01-01')
    edate = request.args.get('endDate', '2024-12-31')
    if generate_image(use_password, account, passcode, sdate, edate):
        # with open('image.html', 'r', encoding='utf-8') as file:
        #     return file.read()
        return image_html
    return '获取失败，请检查输入的鉴权信息是否正确，或者刷新页面重试'

@app.route('/image', methods=['GET'])
def get_image():
    return send_file(os.getcwd() + '/result.png', mimetype='image/png')

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    app.run(debug=False)