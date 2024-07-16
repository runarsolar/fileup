from flask import Flask, render_template, flash, request, send_file, redirect, url_for, abort
from werkzeug.utils import secure_filename
import os, shutil
from urllib.parse import urlparse

#$env:FLASK_APP="fileup.py";$env:FLASK_ENV="development";flask run -h 0.0.0.0

app = Flask(__name__)
app.secret_key = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'
root = 'd:/'

@app.route('/', methods=['GET', 'POST'])
def index():
    cur_dir = '/'
    global root
    try:
        lists = show_file(root)
    except:
        root = 'd:/'
        lists = show_file(root)
    try:
        filedest = upload()
    except:
        flash('Upload Fail')
        return redirect('/')
    if filedest:
        return redirect(request.url)
    
    return render_template('index.html', lists=lists, cur_dir=cur_dir)

@app.route('/<path:url>', methods=['GET', 'POST'])
def show_list(url):
    if url == 'favicon.ico':
        return redirect(url_for('static', filename='icon.webp'))
    
    try:
        global root
        path = os.path.join(root, url)
        if os.path.isdir(path):
            lists = show_file(path)
            cur_dir = '/' + url + '/'
        else:
            return send_file(path)
    except:
        return redirect('/')
    
    #try:
    filedest = upload()
    #except:
    #    flash('Upload Fail')
    #    return redirect('/')
    if filedest:
        return redirect(request.url)
    
    return render_template('index.html', lists=lists, cur_dir=cur_dir)

def show_file(dir):
    dirs = []
    files = []
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isdir(path):
            info = {}
            info['name'] = filename
            info['size'] = 'Folder'
            dirs.append(info)
        elif os.path.isfile(path):
            info = {}
            info['name'] = filename
            size = os.stat(path).st_size
            info['size'] = sizedisp(size)
            files.append(info)
        else:
            print('Something is Wrong.')
    
    return [dirs, files]
        
def upload():
    if request.method == 'POST':
        global root
        if 'op' in request.form:
            if request.form['op'] == 'delete':
                delpath = request.form['path']
                deldir = request.form['dirname'].split(',')
                delfile = request.form['filename'].split(',')
                if deldir != ['']:
                    for x in deldir:
                        flash(os.path.join(root, delpath, x) + ' deleted.')
                        shutil.rmtree(os.path.join(root, delpath, x))
                if delfile != ['']:
                    for x in delfile:
                        flash(os.path.join(root, delpath, x) + ' deleted.')
                        os.remove(os.path.join(root, delpath, x))
                return 'delete'
            elif request.form['op'] == 'rename':
                newname = request.form['newname']
                if newname == '':
                    flash('No name input.')
                    return redirect(request.url)
                repath = request.form['path']
                redir = request.form['dirname'].split(',')
                refile = request.form['filename'].split(',')
                if (len(redir) > 1) or (len(refile) > 1 ) or ((redir != ['']) and ((refile != ['']))):
                    flash('Select just One')
                    return redirect(request.url)
                if redir != ['']:
                    flash(os.path.join(root, repath, redir[0]) + ' renamed.')
                    os.rename(os.path.join(root, repath, redir[0]), os.path.join(root, repath, newname))
                if refile != ['']:
                    flash(os.path.join(root, repath, refile[0]) + ' renamed.')
                    os.rename(os.path.join(root, repath, refile[0]), os.path.join(root, repath, newname))
                return 'rename'




        if 'disk' in request.form:
            root = request.form['disk'] + ':/'
            return redirect('/')
        
        if 'foldername' in request.form:
            foldername = request.form['foldername']
            url = urlparse(request.url).path + '/'
            folderpath = os.path.join(root, url, foldername)
            os.makedirs(folderpath)
            return redirect(request.url)
        
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        fileup = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        url = urlparse(request.url).path + '/'
        filedest = os.path.join(root, url, filename)
        file.save(fileup)
        shutil.move(fileup, filedest)
        return filedest
    return

def sizedisp(num):
    for unit in ("", "k", "M"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}B"
        num /= 1024.0
    return f"{num:.1f} GB"
    
