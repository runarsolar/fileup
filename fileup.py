from flask import Flask, render_template, flash, request, send_file, redirect, url_for, g
import os, shutil, hashlib, argparse
from urllib.parse import quote, unquote
from PIL import Image
from multiprocessing import Pool, freeze_support

#flask --app fileup --debug run -h 0.0.0.0
#pyinstaller -F --add-data templates:templates --add-data static:static fileup.py

app = Flask(__name__)
app.secret_key = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'
root = 'D:/'
gridview = False
if not os.path.exists('uploads'):
    os.mkdir('uploads')
if not os.path.exists('uploads/cache'):
    os.mkdir('uploads/cache')

@app.route('/')
def index():
    return redirect(url_for('files'))

@app.route('/files/', methods=['GET', 'POST'])
@app.route('/files/<path:url>', methods=['GET', 'POST'])
def files(url=''):
    global root
    g.gridview = gridview
    g.drive = root[:2]
    drives = [ chr(x) + ":" for x in range(65,91) if os.path.exists(chr(x) + ":") ]

    path = os.path.join(root, unquote(url))
    if not os.path.exists(path):
        root = 'D:'
        
    if url == '':
        cur_dir = '/files'
    else:
        cur_dir = '/files/' + url
    
    if os.path.isdir(path):
        lists = show_file(path)
    else:
        return send_file(path)
    
    if g.gridview:
        #cache_thumb(lists)
        parallel_thumb(lists)

    op =  postSend(url)
    if op == 'disk':
        return redirect(url_for('files'))
    elif op:
        return redirect(request.url)
    
    return render_template('index.html', lists=lists, cur_dir=cur_dir, drives=drives)

def cache_thumb(lists):
    for file in lists[1]:
        if file['type'] in ['.jpg', '.jpeg', '.png', '.gif']:
            file['ispic'] = True
            pic_path = file['path']
            if not os.path.exists("uploads/cache/t-" + file['name']):
                im = Image.open(pic_path)
                im.thumbnail((256, 256))
                try:
                    im.save("uploads/cache/t-%s" % file['name'])
                except:
                    rgb_im = im.convert('RGB')
                    rgb_im.save("uploads/cache/t-%s" % file['name'])
                file['t'] = "/cache/t-" + file['name']
            else:
                file['t'] = "/cache/t-" + file['name']
        else:
            file['ispic'] = False
    return

def parallel_thumb(lists):
    piclist = []
    picname = []
    for file in lists[1]:
        if file['type'] in ['.jpg', '.jpeg', '.png', '.gif']:
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
        
def postSend(url):
    if request.method == 'POST':
        global root
        global gridview

        # File Operate
        if 'op' in request.form:
            if request.form['op'] == 'delete':
                delpath = url
                deldir = request.form['dirname'].split(',')
                delfile = request.form['filename'].split(',')
                if deldir != ['']:
                    for x in deldir:
                        flash(root + delpath + '/' + x + ' deleted.')
                        shutil.rmtree(os.path.join(root, delpath, x))
                if delfile != ['']:
                    for x in delfile:
                        flash(root + delpath + '/' + x + ' deleted.')
                        os.remove(os.path.join(root, delpath, x))
                return 'delete'
            
            elif request.form['op'] == 'rename':
                newname = request.form['newname']
                if newname == '':
                    flash('No name input.')
                    return redirect(request.url)
                repath = url
                redir = request.form['dirname'].split(',')
                refile = request.form['filename'].split(',')
                if (len(redir) > 1) or (len(refile) > 1 ) or ((redir != ['']) and ((refile != ['']))):
                    flash('Select just One')
                    return redirect(request.url)
                if redir != ['']:
                    flash(root + repath + '/' + redir[0] + ' renamed.')
                    os.rename(os.path.join(root, repath, redir[0]), os.path.join(root, repath, newname))
                if refile != ['']:
                    flash(root + repath + '/' + refile[0] + ' renamed.')
                    os.rename(os.path.join(root, repath, refile[0]), os.path.join(root, repath, newname))
                return 'rename'
        
        # Change view
        if 'view' in request.form:
            gridview = not gridview
            return 'view'

        # Change drives
        if 'disk' in request.form:
            root = request.form['disk'] + '/'
            return 'disk'
        
        # Create new folder
        if 'foldername' in request.form:
            foldername = request.form['foldername']
            folderpath = os.path.join(root, url, foldername)
            os.makedirs(folderpath)
            return 'new'
        
        # Upload one or more files
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if (file.filename == ''):
            flash('No selected file')
            return redirect(request.url)
        fileup = os.path.join('uploads/', file.filename)
        file.save(fileup)
        filedest = os.path.join(root, url, file.filename)
        shutil.move(fileup, filedest)
        return redirect(request.url)
    return

@app.route('/cache/<filename>')
def show_thumb(filename):
    path = os.getcwd() + '/uploads/cache/'
    return send_file(path + filename)

def sizedisp(num):
    for unit in ("", "k", "M"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}B"
        num /= 1024.0
    return f"{num:.1f} GB"

if __name__ == '__main__':
    freeze_support()
    parser = argparse.ArgumentParser(description="down and up files")
    parser.add_argument('-p', "--port", help="change default port")
    args =  parser.parse_args()
    if args.port is None:
        port = 5000
    else:
        port = args.port
    
    app.run('0.0.0.0', port=port, debug=True)