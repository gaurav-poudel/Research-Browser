# Deployment Guide for Research Browser


## Required Files


1. **Dockerfile** - Instructions for building a Docker container for your application
2. **requirements.txt** - List of Python dependencies 
3. **docker-compose.yml** - Configuration for running the application with Docker Compose

## Local Testing with Docker


1. **Install Docker and Docker Compose**:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
   - On Linux: `sudo apt-get install docker.io docker-compose`

2. **Prepare your project**:
   
   - The Dockerfile, requirements.txt, and docker-compose.yml should be in your project root

3. **Build and run the container**:
   ```bash
   docker-compose up --build
   ```

4. **Access your application**:
   - Open http://localhost:5000 in your browser

5. **Upload your files**:
   - Go to the Files tab and upload your project files
   - Alternatively, use Git: `git clone your-repository-url`

6. **Set up a virtual environment**:
   ```bash
   mkvirtualenv --python=python3.10 research-browser
   pip install -r requirements.txt
   ```

7. **Configure web app**:
   - Go to the Web tab and add a new web app
   - Choose "Flask" and Python 3.10
   - Set the path to your app.py file
   - Modify the WSGI configuration file to point to your Flask app



8. **Create a Droplet/Instance** with Ubuntu 

9. **SSH into your server**:
   ```bash
   ssh user@your-server-ip
   ```

10. **Install Docker and Docker Compose**:
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose
   ```

11. **Clone your repository**:
   ```bash
   git clone your-repository-url
   cd your-project
   ```

13. **Deploy with Docker Compose**:
   ```bash
   sudo docker-compose up -d
   ```

