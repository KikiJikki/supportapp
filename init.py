#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask,render_template,request
import sys, socket, datetime, requests
from pymongo import MongoClient
from urllib.parse import quote_plus as quote
from bson.objectid import ObjectId
from config import bxtoken
from bitrix24 import *
from werkzeug.debug import DebuggedApplication
from themes import themes
from bs4 import BeautifulSoup as b



app = Flask(__name__)
app.config["CACHE_TYPE"] = "null"
application = DebuggedApplication(app, evalex=False)

client = MongoClient('localhost', 27017)
db = client.opros
collopros = db.opros
collsipid = db.sip_id
collproject = db.project
colltechpc = db.techpc
collusers = db.users
bx24=Bitrix24(bxtoken)
x = []

def quote():
    r = requests.get('http://ibash.org.ru/random.php')
    html = b(r.text,'html.parser')
    citt = html.find('div', class_='quote')
    quote = citt.text
    return quote


@app.route('/')
def hello():
     return render_template('index.html')



@app.route('/iptel', methods=['GET','POST'])
def iptel():

#--- вылавливаем данные с урла
    
    now = datetime.datetime.now()
    incall = str(request.args.get('incall'))
    techuser = str(request.args.get('techuser'))
    res_str = incall.replace('sip:', '')
    sep = '@'
    rest = res_str.split(sep, 1)[0]
    incall = rest
    print('START return incall from url ' + incall)
#---- добавляем запись звонка в коллекцию opros
    
    query = {"techuser": techuser }
    for value in colltechpc.find(query):
        resulttechpc = str(value['techpc'])

    result = collopros.insert_one(
            {
                "sip_id": incall,
                "date": now.strftime("%d-%m-%y %H:%M"),
                }
            )
    callid = str(result.inserted_id)

    print ('insert first info to db  ' + callid)
    sock = socket.socket()
    print('socket open ' + resulttechpc)
    sock.connect((resulttechpc,23927))
    print('socket is open')
    data = callid.encode()
    sock.sendall(bytes(data))
    data = sock.recv(1024)
    print ('send data to support pc ')
    sock.close()
    return ('iptel function end')

@app.route('/stat')
def stat():
    print('user visit to STATISTICS site')
    resUser = {}
    allCount = 0
    users = []
   
    query = {'user': {'$exists': 'true'}}
    
    for value in collusers.find(query, {'_id': 0,'userfordb': 1}):
        users.append(value['userfordb'])

    for userCount in users:
        query = {"user": userCount}
        resUser[userCount] = collopros.count_documents(query)
        allCount = allCount + collopros.count_documents(query)
   
    resThemes = {}
    for themesCount in themes:
        query = {"themes": themesCount}
        resThemes[themesCount] = collopros.count_documents(query)
        
    return render_template('stat.html', 
            resUser = resUser, 
            resThemes = resThemes, 
            themesCount = themesCount, 
            allCount = allCount)
            

@app.route('/call', methods=['GET','POST'])
def callid():
    city = str('нет в списке')
    callid = str(request.args.get('callid'))
    user = str(request.args.get('user'))
    query = {"_id": ObjectId(callid) }

    print ('  return incomming url from support pc ' + callid + ' ' + user)
#--- ищем город по номеру

    for value in collopros.find(query):
        resultsipid = value['sip_id']
    query = {"sip_id": resultsipid }
    print('  search in db sip incomming sip id  ' + resultsipid) 
    
    for value in collsipid.find(query):
        city = value['name']
    print ('  user enter to call web site')
    print ('  search history call and wait commit bitrix task from support')
    return render_template('main.html', 
            city=city,
            callid=callid,
            collection=collopros,
            resultsipid=resultsipid,
            user=user,
            )

@app.route('/savebitrix', methods=['POST','GET'])
def savebitrix():
    if request.method == 'POST':
#----   достаем данные из урла
               
        print('   was commit bitrix task')
        
        city = str(request.args.get('city'))
        callid = str(request.args.get('callid'))
        resultsipid = str(request.args.get('sip'))
        user = str(request.args.get('user'))
#----  достаем данные из форм

        worker = str(request.form.get('worker'))
        comment = str(request.form.get('comment'))
        header = request.form.getlist('checkbox')
        hostname = str(request.form.get('hostname')) 
        header = str(",".join(header))
        
        query = {"user": user }
        for value in collusers.find(query):
            resultbitrixid = str(value['bitrixid'])
            resultuserfordb = str(value['userfordb'])

#----- пробуем сделать себя по дефолту воркером
        
        print('   return variables from url bitrix task')

        if worker == '999':
            worker = resultbitrixid

        print ('   find self worker  ' + worker )

# ---- Меняем данные о звонке согласно опросу

        query = {"_id": ObjectId(callid) }
        result = { "$set": { 'sip_id': resultsipid, 'user': resultuserfordb, 'themes': header } }
        modify = collopros.update_one(query,result)

        print ('   modify data to db ' )       

        description = "Город/Отдел:  " + city + " \n Телефон:  " + resultsipid + " \n Имя компьютера: " + hostname + "\n " + comment
        description = str(description)

#----  по дефолту херачим группу проекта ТП оптовых компаний - общая группа

        project = "42"
        
        query = {"city": city }
        for value in collproject.find(query):
            project = value['project']
        project = str(project)

        auditor = [732]
    
#----- наш любимый битрикс
        now = datetime.datetime.now()
        date_time = now.strftime("%y-%m-%d")
        date_time = str(date_time + " 19:00")
        taskstatus = 'Заявка сохранена'
        color = 'black'
        worker = str(worker)
        if 'Бесполезный звонок' in header or 'Повторный звонок' in header:
            print('   useless call option selected')
            taskstatus = 'Заявка не сохранена'
            color = 'white'
        else:
            try:
                bx24.callMethod('tasks.task.add', fields={
                    'TITLE': header, 
                    'DESCRIPTION': description, 
                    'CREATED_BY': resultbitrixid, 
                    'AUDITORS': auditor, 
                    'RESPONSIBLE_ID': worker, 
                    'GROUP_ID': project , 
                    'DEADLINE': date_time
                    })
                print ('   insert data to bitrix END')
            except BitrixError as error1:
                taskstatus = 'Всё плохо, заявка не сохранилась'
                color = 'red'
                print ('   ERROR insert data to bitrix END')
        
    return render_template('savebitrix.html',
            color=color,
            comment=comment,
            taskstatus = taskstatus,
            city=city,
            header=header,
            sip=resultsipid,
            callid=callid,
            quote = quote()
            )


        







