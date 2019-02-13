import os
import sys
import imghdr
from argparse import ArgumentParser
from flask import Blueprint, Flask, request, redirect, url_for, flash, \
    send_from_directory, abort
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix

from classify_image import run

UPLOAD_FOLDER = '/tmp/tensorflow_images'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)
app.secret_key = "super secret key"
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.update(UPLOAD_FOLDER=UPLOAD_FOLDER,
                  PREFERRED_URL_SCHEME='https',
                  project_hosts=[])

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def limit_remote_addr():
    local_hosts = ['localhost', '127.0.0.1']
    port = ':' + str(app.config.get('project_port', '8086'))
    local_hosts_ports = [host + port for host in local_hosts]

    project_hosts = app.config.get('project_hosts', [])
    if not project_hosts:
        project_hosts = local_hosts_ports

    if request.host not in project_hosts:
        print("{} not allowed in aborting...".format(request.host))
        print("Allowed hosts: {}".format(project_hosts))
        abort(403)  # Forbidden

@bp.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        print("POSTED OBJECT!!!")
        print(app.config)
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if file is given a valid extension name (e.g. dog.jpg) but has
        # a 'true' extension that is not supported, browser redirects
        true_file_ext = imghdr.what(file)
        if true_file_ext not in ALLOWED_EXTENSIONS:
            flash('Not a valid file extension')
            return redirect(request.url)
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('main.uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <style>
    h1, body {
        font-family: "Arial", Times, serif;
    }
    .button {
        background-color: #4CAF50; /* Green */
        border: none;
        color: white;
        padding: 15px 32px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
    }
    #wrap {
       width:600px;
       margin:0 auto;
    }
    #left_col {
       float:left;
       width:300px;
    }
    #right_col {
       float:right;
       width:300px;
    }
    </style>
    <title>Upload an image for classification</title>
    <h1>Upload an image for classification</h1>
    <form method=post enctype=multipart/form-data>
      <div id="weather_app">
        <div id="left_col">
          <center>
            <label class="my-button-class" style="background-color: white;" for="my-file-selector">
              <input id="my-file-selector" type="file" name=file style="display:none;"> Select a File
            </label>
          </center>
        </div>
        <div style="right_col">
        <input type=submit value=Upload class="button">
        </div>
      </div>
    </form>
    <p>
    Image classification application powered by TensorFlow and Anaconda
    </p>
    '''

@bp.route('/tmp/tensorflow_images/<filename>')
def show_images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                           filename)


@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    output = run(image_file=filepath)
    print(output)

    fileurl = url_for('main.show_images', filename=filename)

    results = '<br/>'.join(output)
    return '''
    <!doctype html>
        <title>Classified File</title>
        <img src="{fileurl}"></img>
        <h2>Classification Results</h2>
        <p>{results}</p>
        <button type="button"><a href={url}>Classify New Image</a></button>
    '''.format(fileurl=fileurl, results=results, url = url_for("main.upload_file"))


if __name__ == '__main__':
    # arg parser for the standard anaconda-project options
    parser = ArgumentParser(prog="imagenet-flask",
                            description="Classification Webapp with Tensorflow")
    parser.add_argument('--anaconda-project-host', action='append', default=[],
                        help='Hostname to allow in requests')
    parser.add_argument('--anaconda-project-port', action='store', default=8086, type=int,
                        help='Port to listen on')
    parser.add_argument('--anaconda-project-iframe-hosts',
                        action='append',
                        help='Space-separated hosts which can embed us in an iframe per our Content-Security-Policy')
    parser.add_argument('--anaconda-project-no-browser', action='store_true',
                        default=False,
                        help='Disable opening in a browser')
    parser.add_argument('--anaconda-project-use-xheaders',
                        action='store_true',
                        default=False,
                        help='Trust X-headers from reverse proxy')
    parser.add_argument('--anaconda-project-url-prefix', action='store', default='',
                        help='Prefix in front of urls')
    parser.add_argument('--anaconda-project-address',
                        action='store',
                        default='0.0.0.0',
                        help='IP address the application should listen on.')


    args = parser.parse_args(sys.argv[1:])
    project_hosts = args.anaconda_project_host
    app.config['project_hosts'] = project_hosts
    app.config['project_port'] = args.anaconda_project_port
    app.register_blueprint(bp, url_prefix=args.anaconda_project_url_prefix)
    app.run(debug=True,
            port=args.anaconda_project_port, host=args.anaconda_project_address)
