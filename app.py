from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    # We use "Version 1.0" so we can easily test our CI/CD automation later
    return "<h1>Flask App - Version 3.0.1</h1><p>Automated CI/CD Deployment Successful!</p>"

if __name__ == '__main__':
    # Jenkins will map this port later
    app.run(host='0.0.0.0', port=5000)
