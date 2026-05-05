import requests
from bs4 import BeautifulSoup

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)


from flask import Flask,render_template, request
from datetime import datetime
import random
app = Flask(__name__)

@app.route("/")
def index():
    link = "<h1>歡迎進入吳菀秦的網站首頁</h1>"
    link += "<a href=/mis>課程</a><hr>"
    link += "<a href=/today>今天日期</a><hr>"
    link += "<a href=/about>關於菀秦</a><hr>"
    link += "<a href=/welcome?u=菀秦&dep=靜宜資管>GET傳值</a><hr>"
    link += "<a href=/account>POST傳值(帳號密碼)</a><hr>"
    link += "<a href=/math>數學運算</a><hr>"
    link += "<a href=/cup>擲茭</a><hr>"
    link += "<a href=/read>讀取Firestore資料(根據lab遞減排序，取前4)</a><br>"
    link += "<a href=/search>查詢老師研究室</a><hr>"
    link += "<a href=/movie>查詢即將上映電影</a><hr>"
    link += "<a href=/movie2>讀取開眼電影即將上映影片，寫入Firestore</a><hr>"
    link += "<a href=/searchQ>片名關鍵字查詢資料</a><hr>"
    link += "<a href=/road>易肇事路口排行榜</a><hr>"
    link += "<a href=/weather>縣市天氣查詢</a><hr>"
    return link

@app.route("/road")
def road():
    R = ""
    url = "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
    Data = requests.get(url)
    #print(Data.text)

    JsonData = json.loads(Data.text)
    for item in JsonData:
        R += item["路口名稱"] + ",總共發生" + item["總件數"] + "件事故<br>"
    return R

@app.route("/weather", methods=["GET", "POST"])
def weather():
    if request.method == "POST":
        city = request.form["city"].replace("台", "臺") # 統一轉換成「臺」
        # 使用氣象署不需要授權碼的網頁 JSON 來源 (部分公開路徑)
        # 若連此連結也失效，建議使用 BeautifulSoup 爬取官網
        url = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0032-001?Authorization=rdec-key-123-45678-011121314&format=JSON"
       
        try:
            # 嘗試讀取資料
            Data = requests.get(url)
            JsonData = json.loads(Data.text)
           
            # 找到對應的縣市
            locations = JsonData["cwaopendata"]["dataset"]["location"]
            target_location = None
            for loc in locations:
                if loc["locationName"] == city:
                    target_location = loc
                    break
           
            if target_location:
                # 天氣現象
                weather_state = target_location["weatherElement"][0]["time"][0]["parameter"]["parameterName"]
                # 降雨機率
                rain_chance = target_location["weatherElement"][1]["time"][0]["parameter"]["parameterName"]
               
                res = f"<h2>{city} 目前天氣預報</h2>"
                res += f"天氣狀況：{weather_state}<br>"
                res += f"降雨機率：{rain_chance}%<br>"
                res += "<br><a href='/weather'>重新查詢</a> | <a href='/'>回首頁</a>"
                return res
            else:
                return f"查無 '{city}' 的資料。請輸入完整縣市名（如：臺中市）。<br><a href='/weather'>返回</a>"
               
        except Exception as e:
            return f"資料讀取失敗，原因：{str(e)}<br><a href='/weather'>返回</a>"
    else:
        return """
            <form method='post'>
                縣市天氣查詢（如：臺中市）：<br>
                <input type='text' name='city'>
                <button type='submit'>查詢天氣</button>
            </form>
            <br><a href='/'>回首頁</a>
        """

@app.route("/movie")
def movie():
    url = "https://www.atmovies.com.tw/movie/next/"
    data = requests.get(url)
    data.encoding = "utf-8"
    sp = BeautifulSoup(data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    R = "<h1>即將上映電影清單</h1>"
    for item in result:
        try:
            # 抓取電影名稱 (從 img 的 alt 屬性)
            name = item.find("img").get("alt")
            # 抓取超連結
            href = "https://www.atmovies.com.tw" + item.find("a").get("href")
            R += f"電影名稱：{name}<br>"
            R += f"介紹連結：<a href='{href}' target='_blank'>{href}</a><br><br>"
        except:
            continue
            
    R += "<br><a href='/'>回到首頁</a>"
    return R

@app.route("/movie2")
def movie2():
  url = "http://www.atmovies.com.tw/movie/next/"
  Data = requests.get(url)
  Data.encoding = "utf-8"
  sp = BeautifulSoup(Data.text, "html.parser")
  result=sp.select(".filmListAllX li")
  lastUpdate = sp.find("div", class_="smaller09").text[5:]

  for item in result:
    picture = item.find("img").get("src").replace(" ", "")
    title = item.find("div", class_="filmtitle").text
    movie_id = item.find("div", class_="filmtitle").find("a").get("href").replace("/", "").replace("movie", "")
    hyperlink = "http://www.atmovies.com.tw" + item.find("div", class_="filmtitle").find("a").get("href")
    show = item.find("div", class_="runtime").text.replace("上映日期：", "")
    show = show.replace("片長：", "")
    show = show.replace("分", "")
    showDate = show[0:10]
    showLength = show[13:]

    doc = {
        "title": title,
        "picture": picture,
        "hyperlink": hyperlink,
        "showDate": showDate,
        "showLength": showLength,
        "lastUpdate": lastUpdate
      }

    db = firestore.client()
    doc_ref = db.collection("電影").document(movie_id)
    doc_ref.set(doc)    
  return "近期上映電影已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate 

@app.route("/searchQ", methods=["POST","GET"])
def searchQ():
    if request.method == "POST":
        MovieTitle = request.form["MovieTitle"]
        info = ""
        db = firestore.client()     
        collection_ref = db.collection("電影")
        docs = collection_ref.order_by("showDate").get()
        for doc in docs:
            if MovieTitle in doc.to_dict()["title"]: 
                info += "片名：" + doc.to_dict()["title"] + "<br>" 
                info += "海報：" + doc.to_dict()["picture"] + "<br>"
                info += "影片介紹：" + doc.to_dict()["hyperlink"] + "<br>"
                info += "片長：" + doc.to_dict()["showLength"] + " 分鐘<br>" 
                info += "上映日期：" + doc.to_dict()["showDate"] + "<br><br>" 
        info += "<br><a href='/'>回到首頁</a>"          
        return info
    else:  
        return render_template("input.html") + "<br><a href='/'>回到首頁</a>"

@app.route("/read")
def read():
    db = firestore.client()

    Temp = ""
    collection_ref = db.collection("靜宜資管2026a")
    docs = collection_ref.order_by("lab",direction=firestore.Query.DESCENDING).limit(4).get()
    for doc in docs:
        Temp += str(doc.to_dict()) + "<br>"

    Temp += "<br><a href='/'>回網站首頁</a>"

    return Temp 


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        keyword = request.form["keyword"]
        db = firestore.client()
        collection_ref = db.collection("靜宜資管2026a")
        docs = collection_ref.get()
        
        result = f"您查詢的關鍵字是：{keyword}<br><br>"
        found = False
        for doc in docs:
            user = doc.to_dict()
            if keyword in user.get("name", ""):
                result += f"{user['name']} 老師的研究室在 {user['lab']}<br>"
                found = True
        
        if not found:
            result += "抱歉，找不到符合條件的老師。"
            
        result += "<br><a href='/search'>重新查詢</a> | <a href='/'>回到首頁</a>"
        return result
    else:
        # 顯示查詢表單
        html = """
            <h1>查詢老師研究室</h1>
            <form action="/search" method="post">
                請輸入要查詢的老師姓名關鍵字：<br>
                <input type="text" name="keyword">
                <input type="submit" value="查詢">
            </form>
            <br><a href="/">回到首頁</a>
        """
        return html


@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>回到網站首頁</a>"

@app.route("/spider1")
def spider1():
    R = ""
    url = "https://wwc2026a.vercel.app/about"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    #print(Data.text)
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select("td a")

    for item in result:
        R += item.text + "<br>" + item.get("href") + "<br><br>"
    return R

@app.route("/today")
def today():
    now = datetime.now()
    year = str(now.year) #取得年份
    month = str(now.month) #取得月份
    day = str(now.day) #取得日期
    now = year + "年" + month + "月" + day + "日"
    return render_template("today.html", datetime = now)

@app.route("/about")
def about():
    return render_template("mis2a.html")

@app.route("/welcome", methods=["GET"])
def welcome():
    x = request.values.get("u")
    y = request.values.get("dep")
    return render_template("welcome.html", name = x, dep = y)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/math")
def math():
    return render_template("math.html")

@app.route('/cup', methods=["GET"])
def cup():
    # 檢查網址是否有 ?action=toss
    #action = request.args.get('action')
    action = request.values.get("action")
    result = None
    
    if action == 'toss':
        # 0 代表陽面，1 代表陰面
        x1 = random.randint(0, 1)
        x2 = random.randint(0, 1)
        
        # 判斷結果文字
        if x1 != x2:
            msg = "聖筊：表示神明允許、同意，或行事會順利。"
        elif x1 == 0:
            msg = "笑筊：表示神明一笑、不解，或者考慮中，行事狀況不明。"
        else:
            msg = "陰筊：表示神明否定、憤怒，或者不宜行事。"
            
        result = {
            "cup1": "/static/" + str(x1) + ".jpg",
            "cup2": "/static/" + str(x2) + ".jpg",
            "message": msg
        }
        
    return render_template('cup.html', result=result)

if __name__ == "__main__":
    app.run(debug=True)
