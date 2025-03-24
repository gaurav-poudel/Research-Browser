import time
import requests
import os
import re
import math
import json
import threading
import pickle
import subprocess
from collections import Counter
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

app = Flask(__name__)
app.jinja_env.filters['zip'] = zip

# Global variables
research_papers = []
tf_idf_index = {}  # custom TF-IDF index
last_update = None
DATA_FILE = "research_papers.pkl"
INDEX_FILE = "tf_idf_index.pkl"

# Get Chrome version to download matching ChromeDriver
def get_chrome_version():
    try:
        # Try to get Chrome version using subprocess
        result = subprocess.run(['google-chrome', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        version_string = result.stdout.strip()
        
        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_string)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error getting Chrome version: {e}")
    
    
    return "134.0.6998.165"


def download_chromedriver():
    chrome_version = get_chrome_version()
    major_version = chrome_version.split('.')[0]  
    
    print(f"Detected Chrome version: {chrome_version} (Major: {major_version})")
    
    
    base_url = f"https://storage.googleapis.com/chrome-for-testing-public/{chrome_version}"
    
    # Determine platform
    if os.name == 'nt':  # Windows
        platform = "win64"
        driver_name = "chromedriver.exe"
    elif os.name == 'posix':  
        if os.uname().sysname == 'Darwin':  # Mac
            platform = "mac-x64" if 'arm' not in os.uname().machine else "mac-arm64"
        else:  # Linux
            platform = "linux64"
        driver_name = "chromedriver"
    
    download_url = f"{base_url}/{platform}/chromedriver-{platform}.zip"
    
   
    driver_dir = os.path.join(os.getcwd(), "chromedriver")
    os.makedirs(driver_dir, exist_ok=True)
    
    driver_path = os.path.join(driver_dir, driver_name)
    
    
    if os.path.exists(driver_path):
        print(f"ChromeDriver already exists at: {driver_path}")
        return driver_path
    

    try:
        import zipfile
        from io import BytesIO
        
        print(f"Downloading ChromeDriver from: {download_url}")
        response = requests.get(download_url)
        
        if response.status_code != 200:
            print(f"Failed to download ChromeDriver. Status code: {response.status_code}")
            return None
        
        e
        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(driver_dir)
        
        
        extracted_dir = os.path.join(driver_dir, f"chromedriver-{platform}")
        if os.path.exists(extracted_dir):

            os.rename(os.path.join(extracted_dir, driver_name), driver_path)
            
            if os.name == 'posix':
                os.chmod(driver_path, 0o755)
            
            print(f" ChromeDriver downloaded and extracted to: {driver_path}")
            return driver_path
        else:
            print(f"ChromeDriver extraction failed. Directory not found: {extracted_dir}")
            return None
            
    except Exception as e:
        print(f"Error downloading/extracting ChromeDriver: {e}")
        return None

# Setup Selenium WebDriver with manual ChromeDriver
def setup_webdriver_manual():
    try:
        # Get Chrome binary path
        chrome_path = "/usr/bin/google-chrome"
        if not os.path.exists(chrome_path):
            chrome_path = None
            print(" Chrome binary not found at expected location")
        
        # Download ChromeDriver matching the Chrome version
        chromedriver_path = download_chromedriver()
        if not chromedriver_path:
            print("Failed to download ChromeDriver")
            return None
        
        
        options = Options()
        if chrome_path:
            options.binary_location = chrome_path
        
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.165 Safari/537.36"
        )
 
        service = Service(executable_path=chromedriver_path)
        
        # Initialize the WebDriver
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver initialized successfully with manual ChromeDriver!")
        return driver
        
    except Exception as e:
        print(f" Manual WebDriver initialization failed: {e}")
        return None

def scrape_papers():
    """Scrape research papers from the portal with improved error handling"""
    global research_papers, tf_idf_index, last_update

    driver = setup_webdriver_manual()
    if driver is None:
        print("Failed to initialize WebDriver. Search functionality will be limited.")

        if not research_papers:
            research_papers = []
        if not tf_idf_index:
            tf_idf_index = {'vectors': [], 'idf': {}}
            
        return "Failed to initialize WebDriver"

    URL = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting/publications/"
    
    try:
        # Load the page
        print(f"🔄 Attempting to load URL: {URL}")
        driver.get(URL)
        print("Page loaded successfully!")
        
        # Wait for the page to load
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "list-results")))
            print(" Found research papers list on page")
        except Exception as e:
            print(f"Timeout while waiting for papers list: {e}")

        print(f"Page title: {driver.title}")
        
        print("Scrolling to load more papers...")
        scroll_pause_time = 2
        for i in range(5):
            print(f"  - Scroll {i+1}/5")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            
        # Extract page content
        print("Extracting page content...")
        page_source = driver.page_source
        print(f" Extracted page source (length: {len(page_source)} characters)")
        
        soup = BeautifulSoup(page_source, "html.parser")
        driver.quit()
        print("BeautifulSoup parsing complete")
        
        # Parse research papers
        print("Parsing research papers...")
        research_papers = []
        results = soup.find_all("li", class_="list-result-item")
        print(f"Found {len(results)} paper entries")
        
        for i, res in enumerate(results):
            if i % 10 == 0:
                print(f"  - Processing paper {i+1}/{len(results)}")
                
            title_tag = res.find("h3", class_="title")
            if title_tag:
                title = title_tag.text.strip()
                link_tag = title_tag.find("a")
                
                link = ""
                if link_tag:
                    link = link_tag["href"]
                    if not link.startswith("http"):
                        link = "https://pureportal.coventry.ac.uk" + link
                
                # Extract all authors
                author_tags = res.find_all("a", class_="link person")
                authors = [author.text.strip() for author in author_tags] if author_tags else ["Unknown"]
                
                # Extract date
                date_tag = res.find("span", class_="date")
                publication_date = date_tag.text.strip() if date_tag else "Unknown"
                abstract_tag = res.find("div", class_="rendering_abstractportal")
                abstract = abstract_tag.text.strip() if abstract_tag else ""
                document = f"{title} {abstract}"
                
                paper = {
                    "title": title,
                    "link": link,
                    "authors": authors,
                    "date": publication_date,
                    "abstract": abstract,
                    "document": document
                }
                research_papers.append(paper)
        
        print(f"Successfully parsed {len(research_papers)} papers")

        try:
            print("Saving research papers data...")
            with open(DATA_FILE, 'wb') as f:
                pickle.dump(research_papers, f)
            print(f"Saved research papers to {DATA_FILE}")
        except Exception as e:
            print(f"Error saving research papers: {e}")

        print("Building TF-IDF index...")
        build_tf_idf_index()
        
        last_update = datetime.now()
        return f"Successfully scraped {len(research_papers)} papers"
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        if driver:
            driver.quit()
        return f"Error scraping papers: {str(e)}"

# Custom TF-IDF implementation
def preprocess_text(text):
    """Preprocess text by converting to lowercase, removing special characters, and tokenizing"""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.split()

def compute_tf(text):
    """Compute term frequency for a document"""
    tokens = preprocess_text(text)
    counter = Counter(tokens)
    return {word: count / len(tokens) for word, count in counter.items()} if tokens else {}

def compute_idf(corpus):
    """Compute inverse document frequency across corpus"""
    num_docs = len(corpus)
    word_count = Counter()
    
    for doc in corpus:
        unique_words = set(preprocess_text(doc))
        for word in unique_words:
            word_count[word] += 1
    
    return {word: math.log(num_docs / (count + 1)) for word, count in word_count.items()}

def compute_tf_idf(corpus):
    """Compute TF-IDF for all documents in corpus"""
    documents = [doc for doc in corpus]
    idf = compute_idf(documents)
    
    result = []
    for doc in documents:
        tf = compute_tf(doc)
        tf_idf = {word: tf[word] * idf.get(word, 0) for word in tf}
        result.append(tf_idf)
    
    return result, idf

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors"""
    # Find common words
    common_words = set(vec1.keys()) & set(vec2.keys())
    
    # Calculate dot product
    dot_product = sum(vec1[word] * vec2[word] for word in common_words)
    
    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(val**2 for val in vec1.values()))
    magnitude2 = math.sqrt(sum(val**2 for val in vec2.values()))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)

def build_tf_idf_index():
    """Build TF-IDF index from research papers"""
    global research_papers, tf_idf_index
    
    if not research_papers:
        print("No research papers available to build TF-IDF index")
        return
    
    print(f"Building TF-IDF index for {len(research_papers)} papers...")
    
    # Extract documents for vectorization
    documents = [paper.get('document', '') for paper in research_papers]
    
    # Compute TF-IDF vectors for all documents
    try:
        tf_idf_vectors, idf = compute_tf_idf(documents)
        tf_idf_index = {
            'vectors': tf_idf_vectors,
            'idf': idf
        }
        
        with open(INDEX_FILE, 'wb') as f:
            pickle.dump(tf_idf_index, f)
        
        print(f"Built and saved TF-IDF index with {len(idf)} unique terms")
    except Exception as e:
        print(f"Error building TF-IDF index: {e}")
        tf_idf_index = {'vectors': [], 'idf': {}}

def load_saved_data():
    """Load saved research papers and TF-IDF index from files"""
    global research_papers, tf_idf_index
    
    data_loaded = False
    
    try:
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            with open(DATA_FILE, 'rb') as f:
                research_papers = pickle.load(f)
            print(f"Loaded {len(research_papers)} papers from file")
            data_loaded = True
        else:
            print(f" Data file not found or empty: {DATA_FILE}")
            research_papers = []
    except Exception as e:
        print(f"Error loading research papers: {e}")
        research_papers = []
    
    try:
        if os.path.exists(INDEX_FILE) and os.path.getsize(INDEX_FILE) > 0:
            with open(INDEX_FILE, 'rb') as f:
                tf_idf_index = pickle.load(f)
            print(f" Loaded TF-IDF index")
            data_loaded = True
        else:
            print(f" Index file not found or empty: {INDEX_FILE}")
            tf_idf_index = {'vectors': [], 'idf': {}}
    except Exception as e:
        print(f" Error loading TF-IDF index: {e}")
        tf_idf_index = {'vectors': [], 'idf': {}}
    
    return data_loaded

def search_papers(query, top_n=10):
    """Search papers using cosine similarity with fallback for empty index"""
    global research_papers, tf_idf_index
    
    if not research_papers:
        print(" No research papers available for search")
        return []
    
    if not tf_idf_index or 'vectors' not in tf_idf_index or 'idf' not in tf_idf_index:
        print(" TF-IDF index not properly initialized")
        query_terms = set(preprocess_text(query))
        results = []
        for idx, paper in enumerate(research_papers):
            title_terms = set(preprocess_text(paper['title']))
            if query_terms & title_terms: 
                paper_copy = paper.copy()
                paper_copy['score'] = len(query_terms & title_terms) / len(query_terms)
                results.append(paper_copy)
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]
    
    try:
        doc_vectors = tf_idf_index['vectors']
        idf = tf_idf_index['idf']
        
        if len(doc_vectors) != len(research_papers):
            print("⚠️ TF-IDF vectors count doesn't match papers count")
            build_tf_idf_index()
            doc_vectors = tf_idf_index['vectors']
            idf = tf_idf_index['idf']
        
        query_tf = compute_tf(query)
        query_vector = {word: query_tf[word] * idf.get(word, 0) for word in query_tf}
        
        similarities = []
        for idx, doc_vector in enumerate(doc_vectors):
            sim = cosine_similarity(query_vector, doc_vector)
            similarities.append((idx, sim))
        
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        
        results = []
        for idx, score in similarities[:top_n]:
            if score > 0:  
                paper = research_papers[idx].copy()
                paper['score'] = float(score)
                results.append(paper)
        
        return results
    except Exception as e:
        print(f" Search error: {e}")
        return []

def schedule_weekly_update():
    def run_update():
        print(f" Running scheduled update at {datetime.now()}")
        scrape_papers()
    
    def update_thread():
        while True:
            time.sleep(7 * 24 * 60 * 60)
            run_update()
    
    
    thread = threading.Thread(target=update_thread, daemon=True)
    thread.start()
    print("Weekly update scheduler started")

def initialize():
    """Initialize the application with fallback mechanisms"""
    global research_papers, tf_idf_index, last_update
    
    print(" Initializing application...")
    data_loaded = False

    try:
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            print(f"Found existing data file: {DATA_FILE}")
            with open(DATA_FILE, 'rb') as f:
                research_papers = pickle.load(f)
            print(f"Loaded {len(research_papers)} papers from file")
            data_loaded = True
        else:
            print(f" Data file not found or empty: {DATA_FILE}")
    except Exception as e:
        print(f" Error loading research papers: {e}")
        research_papers = []

    try:
        if os.path.exists(INDEX_FILE) and os.path.getsize(INDEX_FILE) > 0:
            print(f" Found existing index file: {INDEX_FILE}")
            with open(INDEX_FILE, 'rb') as f:
                tf_idf_index = pickle.load(f)
            print(f"Loaded TF-IDF index")
            data_loaded = True
        else:
            print(f" Index file not found or empty: {INDEX_FILE}")
    except Exception as e:
        print(f" Error loading TF-IDF index: {e}")
        
        tf_idf_index = {'vectors': [], 'idf': {}}

    if not data_loaded or len(research_papers) == 0:
        print(" No valid saved data found. Running initial scrape...")
        result = scrape_papers()
        print(f" Initial scrape result: {result}")
    else:
        
        try:
            last_update = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
            print(f"Last update: {last_update}")
        except:
            last_update = datetime.now()
    
    
    print(" Setting up update scheduler...")
    schedule_weekly_update()
    print(" Application initialization complete")

    # Print startup summary
    print("Startup Summary")
    print(f" Papers in database: {len(research_papers)}")
    print(f"Last database update: {last_update}")
    print("Ready to serve requests\n")

# Flask routes
@app.route('/')
def home():
    global last_update
    return render_template('index.html', last_update=last_update)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('index.html', error="Please enter a search query")
    
    results = search_papers(query, top_n=20)
    return render_template('results.html', query=query, results=results)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    results = search_papers(query, top_n=20)
    return jsonify({"results": results})

@app.route('/update')
def update():
    
    result = scrape_papers()
    return jsonify({"message": result})

@app.route('/status')
def status():
    return jsonify({
        "papers_count": len(research_papers) if research_papers else 0,
        "last_update": last_update.strftime("%Y-%m-%d %H:%M:%S") if last_update else None
    })

if __name__ == '__main__':
    initialize()
    app.run(debug=True)