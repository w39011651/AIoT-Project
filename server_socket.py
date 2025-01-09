from flask import Flask

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    return 'Upload Success!', 200

@app.route('/download', methods=['GET'])
def download():
    return 'Download Success!', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)