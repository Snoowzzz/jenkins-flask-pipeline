
# AWS Jenkins CI/CD Automation Playbook

**Region:** ap-south-1 (Mumbai)
**Infrastructure OS:** Ubuntu 24.04 LTS / 26.04 LTS (`c7i-flex.large`)

---

## Phase 1: Local Development & GitHub Setup

### 1. App Configuration Files

* **`app.py`**

  ```python
  from flask import Flask
  app = Flask(__name__)

  @app.route('/')
  def home():
      return "<h1>Flask App - Version 1.0</h1><p>Automated CI/CD Deployment Successful!</p>"

  if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5000)
  ```
* **`requirements.txt`**

  ```text
  flask==3.0.3
  ```
* **`Dockerfile`**

  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 5000
  CMD ["python", "app.py"]
  ```

### 2. Native WSL Git Sequence

```bash
# Initialize local repo
git init
git add .
git commit -m "Initial commit: Flask app and Dockerfile"

# Link and push to GitHub remote
git branch -M main
git remote add origin https://github.com<YOUR_GITHUB_USERNAME>/jenkins-flask-pipeline.git
git push -u origin main
```

---

## Phase 2: Host Provisioning & Engine Installation

### 1. Key Verification via WSL Terminal

To bypass file system mapping issues on mounted Windows drives (`/mnt/`), pull the `.pem` key file directly into the internal Linux root filesystem to allow proper permission enforcement:

```bash
# Copy key out of Windows mount to local WSL home directory
cp "/mnt/s/main folder alternate/jenkins-server.pem" .

# Set strict read-only permissions required by AWS SSH daemon
chmod 400 jenkins-server.pem

# Establish SSH Connection
ssh -i jenkins-server.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
```

### 2. Correct Repository & Engine Deployment (Executed inside EC2)

* **Crucial Fix:** Explicitly download the authenticated verification armor key directly from the package mirror domain (`pkg.jenkins.io`) instead of the main website index.
* **Java Fix:** Modern Jenkins instances running on Ubuntu 24/26 require **Java 21** (`openjdk-21-jre`) to initialize the runner context properly. Java 17 will induce an instant crash loop.

```bash
# 1. Update general system indexes
sudo apt update

# 2. Download correct GPG key to trusted keyring path
sudo wget -O /usr/share/keyrings/jenkins-keyring.asc https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key

# 3. Write precise package archive path directly to source index list
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

# 4. Synchronize index map and install Docker, Jenkins, and Java 21 concurrently
sudo apt update && sudo apt install -y openjdk-21-jre jenkins docker.io

# 5. Authorize the 'jenkins' runner process to talk to the local Docker daemon socket
sudo usermod -aG docker jenkins

# 6. Reset service state history counters (prevents lingering systemd failure blocks)
sudo systemctl reset-failed jenkins

# 7. Reload configurations and restart process managers
sudo systemctl daemon-reload
sudo systemctl enable jenkins
sudo systemctl restart docker
sudo systemctl restart jenkins

# 8. Sanity check tool state verification
sudo systemctl status jenkins
```

### 3. Retrieve Web UI Admin Token

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

---

## Phase 3: Declarative Jenkins Pipeline Configuration

### 1. Job Creation Spec

* **Type:** Pipeline Project
* **Build Trigger:** Poll SCM (`* * * * *` checked for minute-by-minute repo status checks)

### 2. Core Jenkins Pipeline Script Script

```groovy
pipeline {
    agent any

    stages {
        stage('Clone Code') {
            steps {
                cleanWs()
                git branch: 'main', url: 'https://github.com<YOUR_GITHUB_USERNAME>/jenkins-flask-pipeline.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t flask-pipeline-app:latest .'
            }
        }

        stage('Deploy Container') {
            steps {
                script {
                    try {
                        sh 'docker stop flask-app-container'
                        sh 'docker rm flask-app-container'
                    } catch (Exception e) {
                        echo "No active application containers found to terminate. Launching clean instance..."
                    }
                    sh 'docker run -d -p 5000:5000 --name flask-app-container flask-pipeline-app:latest'
                }
            }
        }
    }
}
```
