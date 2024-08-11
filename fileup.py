from flask import Flask, render_template, flash, request, send_file, redirect, url_for, abort
import os, shutil

#flask --app fileup --debug run -h 0.0.0.0

app = Flask(__name__)
app.secret_key = 'dev'
app.config['UPLOAD_FOLDER'] = 'uploads'
root = 'd:\\'

@app.route('/', methods=['GET', 'POST'])
def index():
    
    return redirect('/files')

@app.route('/files/', methods=['GET', 'POST'])
@app.route('/files/<path:url>', methods=['GET', 'POST'])
def show_list(url=None):
    #if url == 'favicon.ico':
    #    return redirect(url_for('static', filename='icon.webp'))
    global root
    drives = [ chr(x) + ":" for x in range(65,91) if os.path.exists(chr(x) + ":") ]
    
    if url == None:
        url = ''
    path = os.path.join(root, url)
    
    if os.path.isdir(path):
        lists = show_file(path)
    else:
        return send_file(path)
    cur_dir = '/files/' + url

    op =  postSend(url)
    if op == 'disk':
        return redirect('/')
    elif op:
        return redirect(request.url)
    
    return render_template('index.html', lists=lists, cur_dir=cur_dir, drives=drives)

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
        
def postSend(url):
    if request.method == 'POST':
        global root

        # File Operate
        if 'op' in request.form:
            if request.form['op'] == 'delete':
                delpath = url
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
                repath = url
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

        # Change drives
        if 'disk' in request.form:
            root = request.form['disk'] + '\\'
            return 'disk'
        
        # Create new folder
        if 'foldername' in request.form:
            foldername = request.form['foldername']
            folderpath = os.path.join(root, url, foldername)
            os.makedirs(folderpath)
            return 'new'
        
        # Upload one or more files
        if 'files' not in request.files:
            flash('No file part')
            return redirect(request.url)

        files = request.files.getlist('files')
        if (files[0].filename == ''):
            flash('No selected file')
            return redirect(request.url)

        for file in files:
            fileup = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(fileup)
            filedest = os.path.join(root, url, file.filename)
            shutil.move(fileup, filedest)
            print(filedest)
        return redirect(request.url)
    return

def sizedisp(num):
    for unit in ("", "k", "M"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}B"
        num /= 1024.0
    return f"{num:.1f} GB"
    
