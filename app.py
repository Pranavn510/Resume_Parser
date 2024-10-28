#using python version 3.11
from extract_txt import read_files
from txt_preprocessing import preprocess
from txt_to_features import txt_features , feats_reduce
from model import simil
from extract_entities import get_number , get_email , rm_email , rm_number , get_skills , get_name
import pandas as pd
import os
import json
import uuid
from pdfminer3.layout import LAParams
from flask import Flask, flash , render_template, request, redirect, url_for , send_file, abort

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),'files/resumes/')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/outputs/')
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),'Data/')

#make directory if uploaded folder does not exist
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

# Make directory if DOWNLOAD_FOLDER does not exist
if not os.path.isdir(DOWNLOAD_FOLDER):
    os.mkdir(DOWNLOAD_FOLDER)


#flask app config
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['SECRET_KEY'] ='nani?!' #The SECRET_KEY is a special key used by Flask for various security-related operations, such as session management and preventing certain attacks (like CSRF).



ALLOWED_EXTENSIONS = set(['txt','pdf','doc','docx'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/',methods = ["GET"])
def main_page():
    return _show_page()

@app.route('/',methods = ["POST"])
def upload_file():
    # "<p>Please upload the file</p>"
    if 'file' not in request.files:
        return redirect(request.url)
    app.logger.info(request.files)   #logs the uploaded file details i.e, Flask will capture and store specific information about each file that was uploaded in the current request.
    upload_files = request.files.getlist('file')
    app.logger.info(upload_files)

    #If user does not select a file, the browser submits an empty file without a filename
    if not upload_files:
        flash('No Selected file')
        return redirect(request.url)
    
    for file in upload_files:
        original_filename = file.filename
        if allowed_file(original_filename):
            extension = original_filename.rsplit('.',1)[1].lower()
            filename = str(uuid.uuid1()) + '.' + extension #uuid.uuid1() generates a unique identifier based on the current timestamp and the machine's network address, ensuring that each call produces a unique value.
            #these uuid is used because it will generate unique identifier which will be used for giving unique name to file
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            file_list = os.path.join(UPLOAD_FOLDER , 'files.json')
            files = _get_files()
            files[filename] = original_filename
            with open(file_list, 'w') as fh:
                json.dump(files,fh)

    flash('Upload succeeded')
    return redirect(url_for('upload_file'))


@app.route('/download/<code>',methods = ['GET'])
def download(code): #users to download a file based on a unique identifier (code).
    files = _get_files()
    if code in files:
        path = os.path.join(UPLOAD_FOLDER, code)
        if os.path.exists(path):
            return send_file(path)
    abort(404)

@app.route('/process',methods=["POST"])
def process():
    if request.method == 'POST':

        rawtext = request.form['rawtext']
        jdtxt = [rawtext]
        resumetxt = read_files(UPLOAD_FOLDER)  
        p_resumetxt = preprocess(resumetxt)
        p_jdtxt = preprocess(jdtxt)

        feats = txt_features(p_resumetxt , p_jdtxt)
        feat_reduce = feats_reduce(feats)

        df = simil(feat_reduce , p_resumetxt , p_jdtxt)

        t = pd.DataFrame({'Original Resume': resumetxt})
        dt = pd.concat([df,t],axis=1)

        dt['Phone No.'] = dt['Original Resume'].apply(lambda x:get_number(x))
        dt['E-Mail Id'] = dt['Original Resume'].apply(lambda x: get_email(x))
        dt['Original'] = dt['Original Resume'].apply(lambda x: rm_number(x))
        dt['Original']=dt['Original'].apply(lambda x: rm_email(x))
        dt['Candidate\'s Name'] = dt['Original'].apply(lambda x: get_name(x)) 

        skills = pd.read_csv(DATA_FOLDER + 'skill_red.csv')
        skills = skills.values.flatten().tolist()
        skill = []
        for z in skills:
            r = z.lower()
            skill.append(r)

        dt['Skills'] = dt['Original'].apply(lambda x: get_skills(x,skill))
        dt = dt.drop(columns = ['Original', 'Original Resume'])
        if 'JD1' in dt.columns:
            sorted_dt = dt.sort_values(by=['JD1'], ascending=False)
        else:
            print("Column 'JD1' not found in DataFrame. Skipping sort.")
            sorted_dt = dt  # Proceed without sorting if JD 1 is missing

        out_path = DOWNLOAD_FOLDER + "candidates.csv"
        sorted_dt.to_csv(out_path,index = False)

        return send_file(out_path , as_attachment=False)        


def _show_page():
    files = _get_files()
    return render_template('index.html' , files = files)
    # return render_template('index.html')

def _get_files():
    file_list = os.path.join(UPLOAD_FOLDER , 'files.json')
    if os.path.exists(file_list): #This block opens files.json in read mode.
        with open(file_list) as fh:
            return json.load(fh)
    return {}


if __name__ == "__main__":
    app.run(debug=False)
