#!/bin/bash

function print_message() {
    echo -e "\e[1;34m>> $1\e[0m"
}

function print_success() {
    echo -e "\e[1;32m✓ $1\e[0m"
}

function print_error() {
    echo -e "\e[1;31m✗ $1\e[0m"
}

print_message "Setting up Research Browser..."

# Check if Python is installed
if command -v python3 &>/dev/null; then
    python_version=$(python3 --version)
    print_success "Python is installed: $python_version"
else
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
print_message "Creating virtual environment..."
if [ -d "venv" ]; then
    print_message "Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_message "Activating virtual environment..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    print_success "Virtual environment activated"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Install dependencies
print_message "Installing dependencies..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Check for Chrome installation
print_message "Checking for Google Chrome..."
if command -v google-chrome &>/dev/null || command -v google-chrome-stable &>/dev/null; then
    chrome_version=$(google-chrome --version 2>/dev/null || google-chrome-stable --version 2>/dev/null)
    print_success "Chrome is installed: $chrome_version"
else
    print_message "Chrome not found. Attempting to install Chrome..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        print_message "Detected Linux OS"
        if command -v apt-get &>/dev/null; then
            # Debian/Ubuntu
            print_message "Installing Chrome using apt..."
            wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
            sudo apt-get update
            sudo apt-get install -y google-chrome-stable
            if [ $? -eq 0 ]; then
                print_success "Chrome installed successfully"
            else
                print_error "Failed to install Chrome. Please install it manually."
            fi
        elif command -v yum &>/dev/null; then
            # CentOS/RHEL/Fedora
            print_message "Installing Chrome using yum..."
            sudo tee /etc/yum.repos.d/google-chrome.repo <<EOF
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://dl-ssl.google.com/linux/linux_signing_key.pub
EOF
            sudo yum install -y google-chrome-stable
            if [ $? -eq 0 ]; then
                print_success "Chrome installed successfully"
            else
                print_error "Failed to install Chrome. Please install it manually."
            fi
        else
            print_error "Could not determine package manager. Please install Chrome manually."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_message "Detected macOS"
        if command -v brew &>/dev/null; then
            print_message "Installing Chrome using Homebrew..."
            brew install --cask google-chrome
            if [ $? -eq 0 ]; then
                print_success "Chrome installed successfully"
            else
                print_error "Failed to install Chrome. Please install it manually."
            fi
        else
            print_error "Homebrew not found. Please install Chrome manually."
        fi
    else
        print_error "Unsupported OS. Please install Chrome manually."
    fi
fi

# Create necessary directories
print_message "Creating necessary directories..."
mkdir -p templates
mkdir -p chromedriver
print_success "Directories created"

# Check if template files exist
print_message "Checking template files..."
if [ -f "templates/index.html" ] && [ -f "templates/results.html" ]; then
    print_success "Template files found"
else
    print_message "Template files not found. Creating from default templates..."
    
    # Create directory for templates if it doesn't exist
    mkdir -p templates
    
    # Copy templates if they exist in current directory
    if [ -f "index.html" ]; then
        cp index.html templates/
        print_success "Copied index.html to templates directory"
    else
        print_error "index.html not found. Please create it manually."
    fi
    
    if [ -f "results.html" ]; then
        cp results.html templates/
        print_success "Copied results.html to templates directory"
    else
        print_error "results.html not found. Please create it manually."
    fi
fi

# Check for Docker installation (optional)
print_message "Checking for Docker installation (optional)..."
if command -v docker &>/dev/null; then
    docker_version=$(docker --version)
    print_success "Docker is installed: $docker_version"
    
    if command -v docker-compose &>/dev/null; then
        compose_version=$(docker-compose --version)
        print_success "Docker Compose is installed: $compose_version"
    else
        print_message "Docker Compose not found. Installing Docker without Compose is not recommended."
        print_message "Please install Docker Compose for easier deployment."
    fi
else
    print_message "Docker not found. This is optional but recommended for deployment."
    print_message "You can still run the application without Docker."
fi

# Set up initial configuration
print_message "Setting up initial configuration..."
if [ ! -f "config.py" ]; then
    cat > config.py << EOL
# Configuration for Research Browser

# Application settings
DEBUG = True
SECRET_KEY = "$(openssl rand -hex 24)"

# Scraper settings
SCRAPE_INTERVAL_DAYS = 7
MAX_PAPERS = 1000
EOL
    print_success "Created config.py with default settings"
else
    print_message "config.py already exists. Skipping creation."
fi

print_message "Setup complete! You can start the application with:"
print_message "python app.py"
print_message ""
print_message "For Docker deployment:"
print_message "docker-compose up -d"
print_message ""
print_message "Don't forget to deactivate the virtual environment when you're done:"
print_message "deactivate"
