import os
import sqlite3
import random
import datetime
import base64
import json
from flask import Flask, render_template
from flask import g, request
from flask import send_file

DATABASE = 'danarchy.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def execute_db(cmd):
    con = sqlite3.connect(DATABASE)
    c = con.cursor()
    c.execute(cmd)
    con.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    ##########################################################################

    #defualt route to server
    @app.route('/')
    def main():
        cur = get_db().cursor()
        return render_template('index.html')

    ##########################################################################

    #admin panel related sockets
    @app.route('/admin')
    def admin():
        return render_template('admin.html')

    @app.route('/auth',methods=['GET', 'POST'])
    def auth():
        with open('secretkey.txt') as f:
            serverkey = f.read()
            if serverkey == request.json['psk']:
                return "true"
            else:
                return "false"
    
    @app.route('/moderate',methods=['GET', 'POST'])
    def moderate():
        mod_type = request.json['type']
        mod_action = request.json['action']

        if mod_action == 'no_render_norep' or mod_action == 'delete_norep':
            mod_id = request.json['id']
        else:
            mod_id = str(query_db('select content_id from reports where id="'+request.json['id']+'"')[0][0])
            
        try:
            if mod_action == 'delete':
                try:
                    if mod_type == 'post':
                        execute_db('update main set deleted="1" where id="'+mod_id+'"')
                    elif mod_type == 'comment':
                        execute_db('update comments set deleted="1" where id="'+mod_id+'"')
                    execute_db('DELETE FROM reports WHERE content_id="'+mod_id+'"')
                    return 'ok'
                except Exception as e:
                    print(e)
                    return 'bad'
            elif mod_action == 'dismiss':
                try:
                    execute_db('DELETE FROM reports WHERE content_id="'+mod_id+'"')
                    return 'ok'
                except Exception as e:
                    print(e)
                    return 'bad'
            elif mod_action == 'no_render':
                try:
                    if mod_type == 'post':
                        execute_db('update main set deleted="2" where id="'+mod_id+'"')
                    elif mod_type == 'comment':
                        execute_db('update comments set deleted="2" where id="'+mod_id+'"')
                    execute_db('DELETE FROM reports WHERE content_id="'+mod_id+'"')
                    return 'ok'
                except:
                    return 'bad'
        except Exception as e:
            print(e)
            return 'bad'
        return 'wtf'
    
    #test http requests
    @app.route('/test',methods=['GET', 'POST'])
    def test():
        return 'recieved'

    ##########################################################################

    #report related endpoints
    @app.route('/fetchreports')
    def fetchreports():
        return json.dumps(query_db('select * from reports'))

    @app.route('/report',methods=['GET', 'POST'])
    def report():
        try:
            if request.json['type'] == 'post':
                execute_db('insert into reports (content_id,reason,content,type) values ('+request.json['id']+',"'+request.json['reason']+'","'+query_db('select content from main where id="'+request.json['id']+'"')[0][0]+'","'+request.json['type']+'")')
                return json.dumps('ok')
            elif request.json['type'] == 'comment':
                execute_db('insert into reports (content_id,reason,content,type) values ('+request.json['id']+',"'+request.json['reason']+'","'+query_db('select content from comments where id="'+request.json['id']+'"')[0][0]+'","'+request.json['type']+'")')
                return json.dumps('ok')
            else:
                return json.dumps('bad')
        except:
            return json.dumps('bad')

    @app.route('/fetchnumreps')
    def fetchnumreps():
        return json.dumps(query_db('SELECT COUNT(*) FROM reports')[0][0])

    ##########################################################################
    
    #on server close execute these commands
    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    ##########################################################################

    #endpoints for post fetching:
    @app.route('/fetchposts',methods=['GET', 'POST'])
    def fetchposts():
        order = request.json['order']
        if order == 'old':
            return json.dumps(query_db('select * from main where deleted != 3'))
        elif order == 'new':
            return json.dumps(query_db('select * from main where deleted != 3 order by ID desc'))
        elif order == 'pop':
            return json.dumps(query_db('select * from main where deleted != 3 order by likes desc'))
        else:
            return 'bad request'

    ##########################################################################

    #endpoints for comments:
    @app.route('/commentsnew',methods=['GET', 'POST'])
    def comments():
        return json.dumps(query_db('select * from comments where post="'+request.json['id']+'"'))
    
    @app.route('/fetchallcomments',methods=['GET', 'POST'])
    def allcomments():
        return json.dumps(query_db('select * from comments'))

    @app.route('/numcomments',methods=['GET', 'POST'])
    def numcomments():
        return str(query_db('select comment_count from main where id="'+request.json['id']+'"')[0][0])

    @app.route('/comment',methods=['GET', 'POST'])
    def leavecomment():
        req = request.json
        #execute the comment to the comment table
        execute_db('insert into comments (id,post,content,likes,stamp,user,deleted) values ('+str(query_db('SELECT Count(*) FROM comments')[0][0])+',"'+req["POST"]+'","'+req["CONTENT"]+'",0,"'+str(datetime.datetime.now())[0:19]+'","'+req["USER"]+'",false)')
        #update main table comment amount to reflect new comment count
        execute_db('update main set comment_count=('+str((query_db('select comment_count from main where id="'+req['POST']+'"')[0][0])+1)+') where id="'+req['POST']+'"')
        return "commented"

    ##########################################################################

    #endpoints for laughing:
    @app.route('/laugh',methods=['GET', 'POST'])
    def laugh():
        if request.json['type'] == 'post':
            val = json.dumps(query_db('select likes from main where id="'+request.json['id']+'"')[0][0])
            execute_db('update main set likes=('+str( int(val) + 1)+') where id="'+request.json['id']+'"')
            return str(int(val)+1)
        elif request.json['type'] == 'comment':
            val = json.dumps(query_db('select likes from comments where id="'+request.json['id']+'"')[0][0])
            execute_db('update comments set likes=('+str( int(val) + 1)+') where id="'+request.json['id']+'"')
            return str(int(val)+1)
        else:
            return 'ERROR SOME SHIT GOIN ON IN THE SERVER' 
    
    ##########################################################################

    #endpoints for posting:
    @app.route('/post',methods=['GET', 'POST'])
    def post():
        req = request.json
        postid = str(query_db('SELECT Count(*) FROM main')[0][0])
        execute_db('insert into main (ID,USER,CONTENT,LIKES,STAMP,deleted,comment_count) values ('+postid+',"'+req['USER']+'","'+req['CONTENT']+'",'+ str(0)+',"'+str(datetime.datetime.now())[0:19]+'",0,0)')
        if req['attachment'] != 'none':
            attachmentid = str(query_db('SELECT Count(*) FROM attachments')[0][0])
            newfilename =  attachmentid + '.' + req['attachment'].split('.')[1]
            with open("static/attachments/"+newfilename,"wb") as fh:
                print(req)
                print(str(req['bytes']))
                print(base64.b64decode(req['bytes']))
                fh.write(base64.b64decode(req['bytes']))
            execute_db('insert into attachments (postid,name) values ('+postid+',"'+newfilename+'")')
            execute_db('update main set attachmentid=("'+attachmentid+'") where id="'+postid+'"')
        return "done"

    ##########################################################################

    #endpoints for attachments:
    @app.route('/getattachment',methods=['GET', 'POST'])
    def getattachment():
        req = request.json
        return json.dumps([('http://76.181.32.163:5000/static/attachments/'+query_db('select name from attachments where id="'+req['id']+'"')[0][0]),(query_db('select id from main where attachmentid="'+req['id']+'"')[0][0]),query_db('select likes from main where attachmentid="'+req['id']+'"')[0][0],(query_db('select comment_count from main where attachmentid="'+req['id']+'"')[0][0])])

    ##########################################################################
    
    return app