from flask import Flask, render_template, flash, request, send_file, redirect, url_for, g, session
from werkzeug.security import check_password_hash, generate_password_hash
import os, shutil, hashlib, argparse, json, sqlite3
from urllib.parse import quote, unquote
from PIL import Image
from multiprocessing import Pool, freeze_support

#flask --app fileup --debug run -h 0.0.0.0
#pyinstaller -F --add-data templates:templates --add-data static:static fileup.py

app = Flask(__name__)
app.secret_key = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'
root = 'D:/'
cur_path = "/"
use_auth = False
reg = True
gridview = False
if not os.path.exists('uploads'):
    os.mkdir('uploads')
if not os.path.exists('uploads/cache'):
    os.mkdir('uploads/cache')

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = sqlite3.connect('fileup.db')
        db.row_factory = sqlite3.Row
        g.user = db.execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@app.route('/')
def index():
    g.reg = reg
    if use_auth is False or g.user is not None:
        return redirect('/files')

    return render_template('auth.html')

@app.route('/files/', methods=['GET', 'POST'])
@app.route('/files/<path:url>', methods=['GET', 'POST'])
def files(url=''):
    g.auth = use_auth
    if use_auth is True and g.user is None:
        return redirect('/')
    
    global root
    g.gridview = gridview
    g.drive = root[:2]
    drives = [ chr(x) + ":" for x in range(65,91) if os.path.exists(chr(x) + ":") ]

    path = os.path.join(root, unquote(url))
    if not os.path.exists(path):
        return redirect(url_for('files'))
    if not os.path.exists(path):
        root = os.getcwd() +'/'
        
    if url == '':
        cur_dir = '/files'
    else:
        cur_dir = '/files/' + url
    
    if os.path.isdir(path):
        lists = show_file(path)
    else:
        return send_file(path)
    
    if g.gridview:
        parallel_thumb(lists)
    
    return render_template('index.html', lists=lists, cur_dir=cur_dir, drives=drives)

def show_file(dir):
    dirs = []
    files = []
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isdir(path):
            info = {}
            info['name'] = filename
            info['link'] = quote(filename)
            info['size'] = 'Folder'
            dirs.append(info)
        elif os.path.isfile(path):
            info = {}
            info['name'] = filename
            info['link'] = quote(filename)
            size = os.stat(path).st_size
            info['size'] = sizedisp(size)
            info['type'] = os.path.splitext(filename)[1]
            info['path'] = path
            files.append(info)
        else:
            print('Something is Wrong.')
    return [dirs, files]

@app.route('/api/drives', methods=('POST',))
def get_drives():
    drive = root[:2]
    drives = [ chr(x) + ":" for x in range(65,91) if os.path.exists(chr(x) + ":") ]
    res = {"nowdrive": drive, "alldrives": drives}
    return json.dumps(res)


@app.route('/api/lists', methods=('GET','POST'))
def get_lists():
    path = request.args.get('path')
    if path == None:
        path = ''
    drive = request.args.get('drive')
    if drive == None:
        dir = '/'
    elif drive == '':
        dir = '/'
    elif drive == '/':
        dir = '/' + path
    else:
        dir = drive + ':/' + path

    dirs = []
    files = []
    for name in os.listdir(dir):
        path = os.path.join(dir, name)
        if os.path.isdir(path):
            dirs.append(name)
        elif os.path.isfile(path):
            files.append(name)
        else:
            print('Something is Wrong.')
    lists = {'dirs':dirs, 'files':files}
    return json.dumps(lists, ensure_ascii=False)

@app.route('/api/operate', methods=('POST',))
def operate():
    req = request.json
    print(req)
    res = {'status':'ok','msg':'','redirect':'page'}

    if req['op'] == 'newfolder':
        if req['redirect'] :
            res['redirect'] = req['redirect']
        to_dir = req['to_dir']
        if to_dir == '/':
            to_dir = ''
        path = req['to_drive'] + ':' + to_dir + '/' + req['name']
        flash('new folder created at ' + path)
        os.mkdir(path)
    
    if req['op'] == 'newfile':
        to_dir = req['to_dir']
        if to_dir == '/':
            to_dir = ''
        path = req['to_drive'] + ':' + to_dir + '/' + req['name']
        flash('new file created at ' + path)
        f = open(path, 'x')
        f.close()

    if req['op'] == 'rename':
        to_dir = req['to_dir']
        if to_dir == '/':
            to_dir = ''
        path = req['to_drive'] + ':' + to_dir + '/' + req['oldname']
        dest = req['to_drive'] + ':' + to_dir + '/' + req['newname']
        flash(dest + ' renamed')
        os.rename(path, dest)
    
    if req['op'] == 'delete':
        to_dir = req['to_dir']
        if to_dir == '/':
            to_dir = ''
        delpath = req['to_drive'] + ':' + to_dir + '/'
        deldir = req['deldir']
        delfile = req['delfile']
        
        if deldir != ['']:
            for x in deldir:
                flash(delpath + x + ' deleted.')
                shutil.rmtree(delpath + x)
        if delfile != ['']:
            for x in delfile:
                flash(delpath + x + ' deleted.')
                os.remove(delpath + x)

    if req['op'] == 'move':
        dirlist = req['dirlist']
        filelist = req['filelist']
        from_path = req['from_drive'] +':' + req['from_dir']
        to_path = req['to_drive'] +':' + req['to_dir']

        if dirlist != ['']:
            for dir in dirlist:
                flash('Move ' + from_path + '/' + dir + ' to ' + to_path)
                shutil.move(from_path + '/' + dir, to_path)
        if filelist != ['']:
            for file in filelist:
                flash('Move ' + from_path + '/' + file + ' to ' + to_path)
                shutil.move(from_path + '/' + file, to_path)
    
    if req['op'] == 'copy':
        dirlist = req['dirlist']
        filelist = req['filelist']
        from_path = req['from_drive'] +':' + req['from_dir']
        to_path = req['to_drive'] +':' + req['to_dir']

        if dirlist != ['']:
            for dir in dirlist:
                print(from_path + '/' + dir)
                print(to_path)
                os.mkdir(to_path + '/' + dir)
                flash('Copy ' + from_path + '/' + dir + ' to ' + to_path)
                shutil.copytree(from_path + '/' + dir, to_path + '/' + dir, dirs_exist_ok=True)
        if filelist != ['']:
            for file in filelist:
                flash('Copy ' + from_path + '/' + file + ' to ' + to_path)
                shutil.copy(from_path + '/' + file, to_path)
    
    if req['op'] == 'changeDrive':
        global root
        root = req['drivename'] + ':/'

    if req['op'] == 'changeView':
        global gridview
        gridview = not gridview

    if req['op'] == 'archive':
        path = req['to_drive'] + ':' + req['to_dir'] + '/' + req['dirname']
        flash(path + '.zip created')
        shutil.make_archive(path, 'zip', path)

    if req['op'] == 'unzip':
        path = req['to_drive'] + ':' + req['to_dir'] + '/' + req['zipfile']
        flash(path + 'unzipped to ' + path + '/' + req['zipfile'][:-4])
        print(req['zipfile'])
        shutil.unpack_archive(path, path[:-4])

    if req['op'] == 'zip':
        from zipfile import ZipFile
        myzip = ZipFile(req['to_drive'] + ':' + req['to_dir'] + '/' + 'output.zip', 'w')
        for file in req['filelist']:
            path = req['to_drive'] + ':' + req['to_dir'] + '/' + file
            print(path)
            myzip.write(path, file)
        myzip.close()
        flash('zipped to ' + req['to_drive'] + ':' + req['to_dir'] + '/' + 'output.zip')

    return json.dumps(res)

@app.route('/api/upload', methods=('POST',))
def upload():
    path = request.form['dest']
    file = request.files['file']

    fileup = os.path.join('uploads/', file.filename)
    file.save(fileup)
    filedest = path + '/' + file.filename
    shutil.move(fileup, filedest)
    return 'ok'

@app.route('/api/openfile', methods=('POST',))
def openfile():
    req = request.json
    res = {'status':'ok','msg':'','redirect':'no', 'txt':''}
    if req['op'] == 'open':
        path = req['to_drive'] + ':' + req['to_dir'] + '/' + req['name']
        f = open(path, "r")
        res['txt'] = f.read()
        f.close()
    elif req['op'] == 'save':
        path = req['path']
        print(path)
        res['txt'] = req['txt']
        f = open(path, 'w')
        f.write(req['txt'])
        f.close()

    return json.dumps(res)

@app.route('/api/auth', methods=('POST',))
def user_auth():
    req = request.json
    print(req)
    res = {'status':'ok', 'msg':'','redirect':'page'}
    db = sqlite3.connect('fileup.db')
    db.row_factory = sqlite3.Row

    if req['op'] == 'register' and reg == True:
        username = req['username']
        password = req['password']
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)",
                           (username, generate_password_hash(password)))
            db.commit()
            flash('register successed')
        except:
            flash('username has been registered')

    if req['op'] == 'login':
        username = req['username']
        password = req['password']
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()
        if user is None:
            flash('Incorrect username')
        elif not check_password_hash(user['password'], password):
            flash('Incorrect password.')
        else:
            session.clear()
            session['user_id'] = user['id']

    if req['op'] == 'logout':
        session.clear()

    return json.dumps(res)

@app.route('/cache/<filename>')
def show_thumb(filename):
    path = os.getcwd() + '/uploads/cache/'
    return send_file(path + filename)

def parallel_thumb(lists):
    piclist = []
    picname = []
    for file in lists[1]:
        if file['type'] in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
            file['ispic'] = True
            pic_path = file['path']
            m = hashlib.sha256()
            m.update(pic_path.encode())
            tname = "t-" + file['name'] + "-" + m.hexdigest()[:6] + ".jpg"
            if not os.path.exists(os.getcwd() + "/uploads/cache/" + tname):
                piclist.append(pic_path)
                picname.append(tname)
                file['t'] = "/cache/" + tname
            else:
                file['t'] = "/cache/" + tname
        elif file['type'] == '.gif':
            file['ispic'] = True
        else:
            file['ispic'] = False

    pool = Pool(8)
    pool.map(thumbnail, zip(piclist, picname))
    return

def thumbnail(params):
    pic_path, name = params
    im = Image.open(pic_path)
    im.thumbnail((256, 256))
    try:
        im.save("uploads/cache/%s" % name)
    except:
        rgb_im = im.convert('RGB')
        rgb_im.save("uploads/cache/%s" % name)

def sizedisp(num):
    for unit in ("", "k", "M"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}B"
        num /= 1024.0
    return f"{num:.1f} GB"

def create_db():
    db = sqlite3.connect('fileup.db')
    cursor = db.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS user( \
            id integer primary key autoincrement, \
            username text unique not null, password text)")
    db.commit()
    db.close()

if __name__ == '__main__':
    freeze_support()
    parser = argparse.ArgumentParser(description="down and up files")
    parser.add_argument('-p', "--port", help="change default port")
    parser.add_argument('-r', "--root", help="change start directory like C:/")
    parser.add_argument('-u', "--auth", help="reg/noreg to enable register")
    args =  parser.parse_args()
    if args.root != None:
        root = args.root 
    if args.port is None:
        port = 5000
    else:
        port = args.port
    if args.auth == 'reg':
        use_auth = True
        create_db()
    if args.auth == 'noreg':
        use_auth = True
        reg = False
        create_db()
    
    app.run('0.0.0.0', port=port, debug=True)
