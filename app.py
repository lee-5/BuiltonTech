from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from waitress import serve
import pymysql
import hashlib
import logging
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

UPLOAD_FOLDER = 'assets/images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hash the input password using hashlib and encode it
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Database connection
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",  # Replace with your MySQL root password
        database="builtontech"
    )

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Fetch services with corresponding resources
def fetch_services():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT s.image, s.service_name, s.description, r.no_of_people, r.no_of_days, s.price, r.file_url 
    FROM services s
    JOIN resources r ON s.service_id = r.service_id
    """

    cursor.execute(query)
    services = cursor.fetchall()

    cursor.close()
    conn.close()
    return services

# Fetch portfolio items
def fetch_portfolio():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT title, price, people, location, duration, image_path 
    FROM portfolio
    """

    cursor.execute(query)
    portfolio_items = cursor.fetchall()

    cursor.close()
    conn.close()
    return portfolio_items

# Fetch bookings
def fetch_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT booking_id, name, phone_number, address, visit_date, service_name, service_id, booking_date, price, latitude, longitude, user_id
    FROM bookings
    """

    cursor.execute(query)
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()
    return bookings

# Fetch progress
def fetch_progress():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """  SELECT title, price, people, location, duration, image_path
    FROM portfolio
    """

    cursor.execute(query)
    progress_items = cursor.fetchall()

    cursor.close()
    conn.close()
    return progress_items

# Fetch deals
def fetch_deals():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT s.service_name, s.description, s.price, r.no_of_people, r.no_of_days, s.image
    FROM services s
    JOIN resources r ON s.service_id = r.service_id
    """
    cursor.execute(query)
    deals = cursor.fetchall()
    cursor.close()
    conn.close()
    return deals

# Fetch deals based on search query
def search_deals(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    search_query = """
    SELECT s.service_name, s.description, s.price, r.no_of_people, r.no_of_days, s.image
    FROM services s
    JOIN resources r ON s.service_id = r.service_id
    WHERE s.service_name LIKE %s
    """
    cursor.execute(search_query, ('%' + query + '%',))
    deals = cursor.fetchall()
    cursor.close()
    conn.close()
    return deals

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # Check if the user is the admin
        if email == 'admin@123' and password == '1234':
            session['loggedin'] = True
            session['username'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM login WHERE email = %s AND password = %s', (email, hashed_password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if user[4]:  # Assuming the 5th column indicates if the user is disabled
                return render_template('index.html', error='Your account has been disabled.')
            session['loggedin'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('home'))
        else:
            return render_template('index.html', error='Invalid email or password')

    return render_template('index.html')

@app.route('/home')
def home():
    services = fetch_services()
    return render_template('home.html', services=services, username=session.get('username'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO login (username, email, password) VALUES (%s, %s, %s)', (username, email, hashed_password))
        conn.commit()

        # Fetch the user id of the newly registered user
        cursor.execute('SELECT id FROM login WHERE email = %s', (email,))
        user_id = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Set session variables
        session['loggedin'] = True
        session['id'] = user_id
        session['username'] = username

        return redirect(url_for('home'))

    return render_template('register.html', username=session.get('username'))

@app.route('/about')
def about():
    portfolio_items = fetch_portfolio()
    return render_template('about.html', portfolio_items=portfolio_items, username=session.get('username'))

@app.route('/deals', methods=['GET', 'POST'])
def deals():
    search_query = request.form.get('search_query', '')
    conn = get_db_connection()
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT s.service_name, s.description, s.price, r.no_of_days, r.no_of_people, s.image, r.file_url
            FROM services s
            JOIN resources r ON s.service_id = r.service_id
            WHERE s.service_name LIKE %s
        """, ('%' + search_query + '%',))
        deals = cursor.fetchall()
    else:
        deals = fetch_deals()

    cursor.close()
    conn.close()

    return render_template('deals.html', deals=deals, username=session.get('username'))

@app.route('/reservation')
def reservation():
    if 'loggedin' in session:
        service_id = request.args.get('service_id', 1)  # Default to service_id 1 if not provided
        return render_template('reservation.html', service_id=service_id, username=session['username'])
    return redirect(url_for('login'))

@app.route('/progress') 
def progress():
    if 'loggedin' in session:
        user_id = session['id']
        print(f"User ID: {user_id}")  # Debugging: Print user_id to console
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT p.progress_image, s.service_name, p.description, p.estimated_completion_date
        FROM progress p
        JOIN bookings b ON p.booking_id = b.booking_id
        JOIN services s ON b.service_id = s.service_id
        WHERE b.user_id = %s
        """
        cursor.execute(query, (user_id,))
        progress_data = cursor.fetchall()

        cursor.close()
        conn.close()

        # Debugging: Print progress_data to console
        print(progress_data)

        return render_template('progress.html', progress_data=progress_data, username=session['username'])
    return redirect(url_for('login'))

@app.route('/book_site_visit', methods=['POST'])
def book_site_visit():
    if 'loggedin' in session:
        try:
            user_id = session['id']
            name = request.form['Name']
            phone_number = request.form['Number']
            address = request.form['Guests']
            visit_date = request.form['date']
            service_name = request.form['Destination']
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            current_date = datetime.now().strftime('%Y-%m-%d')
            price = 1000  # Example price, you can fetch the actual price from the service table

            conn = get_db_connection()
            cursor = conn.cursor()

            # Fetch service_id from services table based on service_name
            cursor.execute('SELECT service_id FROM services WHERE service_name = %s', (service_name,))
            service_id = cursor.fetchone()
            if service_id:
                service_id = service_id[0]
            else:
                raise Exception("Service not found")

            query = """
            INSERT INTO bookings (name, phone_number, address, visit_date, service_name, service_id, booking_date, price, latitude, longitude, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (name, phone_number, address, visit_date, service_name, service_id, current_date, price, latitude, longitude, user_id))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for('reservation'))
        except Exception as e:
            logging.error(f"Error during booking site visit: {e}")
            return render_template('reservation.html', error="An error occurred during booking.", service_id=None, username=session.get('username'))
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'loggedin' in session and session['username'] == 'admin':
        return render_template('admin.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/get_data/<table>', methods=['GET'])
def get_data(table):
    if 'loggedin' in session and session['username'] == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(f"SELECT * FROM {table}")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
    return redirect(url_for('login'))

@app.route('/update_data/<table>', methods=['POST'])
def update_data(table):
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        id_column = 'id'
        if table == 'bookings':
            id_column = 'booking_id'
        elif table == 'services':
            id_column = 'service_id'
        elif table == 'portfolio':
            id_column = 'id'
        elif table == 'progress':
            id_column = 'progress_id'
        elif table == 'resources':
            id_column = 'resource_id'
        
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != id_column])
        query = f"UPDATE {table} SET {set_clause} WHERE {id_column} = {data[id_column]}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/upload_image/<table>/<id>/<index>', methods=['POST'])
def upload_image(table, id, index):
    if 'loggedin' in session and session['username'] == 'admin':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            id_column = 'id'
            column = 'progress_image'
            if table == 'services':
                id_column = 'service_id'
                column = 'image'
            elif table == 'portfolio':
                id_column = 'id'
                column = 'image_path'
            elif table == 'progress':
                id_column = 'progress_id'
                column = 'progress_image'
            elif table == 'resources':
                id_column = 'resource_id'
                column = 'file_url'

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT {column} FROM {table} WHERE {id_column} = %s", (id,))
            existing_urls = cursor.fetchone()[0]
            if existing_urls:
                urls = existing_urls.split(',')
                if index.isdigit() and int(index) < len(urls):
                    urls[int(index)] = file_url
                else:
                    urls.append(file_url)
                updated_urls = ",".join(urls)
            else:
                updated_urls = file_url

            query = f"UPDATE {table} SET {column} = %s WHERE {id_column} = %s"
            cursor.execute(query, (updated_urls, id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"status": "success", "file_url": file_url})
    return redirect(url_for('login'))

@app.route('/upload_progress_images/<progress_id>/<index>', methods=['POST'])
def upload_progress_images(progress_id, index):
    if 'loggedin' in session and session['username'] == 'admin':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT progress_image FROM progress WHERE progress_id = %s", (progress_id,))
            existing_urls = cursor.fetchone()[0]
            if existing_urls:
                urls = existing_urls.split(',')
                if index.isdigit() and int(index) < len(urls):
                    urls[int(index)] = file_url
                else:
                    urls.append(file_url)
                updated_urls = ",".join(urls)
            else:
                updated_urls = file_url

            query = "UPDATE progress SET progress_image = %s WHERE progress_id = %s"
            cursor.execute(query, (updated_urls, progress_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"status": "success", "file_url": file_url})
    return redirect(url_for('login'))

@app.route('/add_data/<table>', methods=['POST'])
def add_data(table):
    if 'loggedin' in session and session['username'] == 'admin':
        try:
            data = request.json
            logging.debug(f"Received data for table {table}: {data}")
            # Validate and convert numeric fields
            for key, value in data.items():
                if key in ['price', 'no_of_days', 'no_of_people', 'duration']:  # Add other numeric fields as needed
                    if value == '':
                        data[key] = 0  # Assign a default value if the field is empty
                    else:
                        data[key] = int(value)
                elif key in ['service_name', 'description', 'image', 'title', 'file_url', 'progress_image']:  # Add other required fields as needed
                    if value == '':
                        raise ValueError(f"Field '{key}' cannot be empty")
            
            # Ensure required fields have default values if not provided
            if table == 'services':
                if 'service_name' not in data or data['service_name'] == '':
                    data['service_name'] = 'Default Service Name'
                if 'price' not in data or data['price'] == '':
                    data['price'] = 0.00
                if 'image' not in data or data['image'] == '':
                    data['image'] = 'default_image.png'  # Assign a default image if not provided
                if 'description' not in data or data['description'] == '':
                    data['description'] = 'Default Service Description'

            elif table == 'resources':
                if 'title' not in data or data['title'] == '':
                    data['title'] = 'Default Title'
                if 'description' not in data or data['description'] == '':
                    data['description'] = 'Default Resource Description'
                if 'file_url' not in data or data['file_url'] == '':
                    data['file_url'] = 'default_file_url.png'  # Assign a default file URL if not provided

            elif table == 'portfolio':
                if 'title' not in data or data['title'] == '':
                    data['title'] = 'Default Title'
                if 'price' not in data or data['price'] == '':
                    data['price'] = 0.00
                if 'image_path' not in data or data['image_path'] == '':
                    data['image_path'] = 'default_image_path.png'  # Assign a default image path if not provided
                if 'duration' not in data or data['duration'] == '':
                    data['duration'] = 0  # Assign a default duration if not provided
                if 'description' not in data or data['description'] == '':
                    data['description'] = 'Default Portfolio Description'

            elif table == 'progress':
                if 'description' not in data or data['description'] == '':
                    data['description'] = 'Default Progress Description'
                if 'progress_image' not in data or data['progress_image'] == '':
                    data['progress_image'] = 'default_progress_image.png'

            columns = ", ".join(data.keys())
            values = ", ".join([f"'{value}'" if value is not None else 'NULL' for value in data.values()])
            query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"status": "success"})
        except Exception as e:
            logging.error(f"Error adding data to {table}: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return redirect(url_for('login'))

@app.route('/add_progress', methods=['POST'])
def add_progress():
    data = request.json
    logging.debug(f"Received data: {data}")
    
    description = data.get("description", "").strip()
    
    if not description:
        logging.warning("Description is empty, assigning default value.")
        data["description"] = "Default Progress Description"

    # Proceed with adding to DB...
    try:
        columns = ", ".join(data.keys())
        values = ", ".join([f"'{value}'" if value is not None else 'NULL' for value in data.values()])
        query = f"INSERT INTO progress ({columns}) VALUES ({values})"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        progress_id = cursor.lastrowid  # Get the ID of the newly inserted row
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "progress_id": progress_id})
    except Exception as e:
        logging.error(f"Error adding data to progress: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/add_resources', methods=['POST'])
def add_resources():
    data = request.json
    logging.debug(f"Received data: {data}")
    
    # Ensure required fields have default values if not provided
    if 'service_id' not in data or data['service_id'] == '':
        data['service_id'] = 0  # Assign a default service_id if not provided
    if 'title' not in data or data['title'] == '':
        data['title'] = 'Default Title'
    if 'description' not in data or data['description'] == '':
        data['description'] = 'Default Resource Description'
    if 'file_url' not in data or data['file_url'] == '':
        data['file_url'] = 'default_file_url.png'  # Assign a default file URL if not provided
    if 'no_of_days' not in data or data['no_of_days'] == '':
        data['no_of_days'] = 0
    if 'no_of_people' not in data or data['no_of_people'] == '':
        data['no_of_people'] = 0
    if 'price' not in data or data['price'] == '':
        data['price'] = 0.00
    if 'uploaded_at' not in data or data['uploaded_at'] == '':
        data['uploaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Assign current timestamp if not provided
    else:
        # Convert the uploaded_at field to the correct format
        try:
            data['uploaded_at'] = datetime.strptime(data['uploaded_at'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            data['uploaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Assign current timestamp if conversion fails

    # Proceed with adding to DB...
    try:
        columns = ", ".join(data.keys())
        values = ", ".join([f"'{value}'" if isinstance(value, str) else str(value) for value in data.values()])
        query = f"INSERT INTO resources ({columns}) VALUES ({values})"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        resource_id = cursor.lastrowid  # Get the ID of the newly inserted row
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "resource_id": resource_id})
    except Exception as e:
        logging.error(f"Error adding data to resources: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/toggle_user', methods=['POST'])
def toggle_user():
    if 'loggedin' in session and session['username'] == 'admin':
        user_id = request.json['id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE login SET disabled = NOT disabled WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_booking', methods=['POST'])
def update_booking():
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != 'booking_id'])
        query = f"UPDATE bookings SET {set_clause} WHERE booking_id = {data['booking_id']}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_portfolio', methods=['POST'])
def update_portfolio():
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != 'id'])
        query = f"UPDATE portfolio SET {set_clause} WHERE id = {data['id']}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_service', methods=['POST'])
def update_service():
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != 'service_id'])
        query = f"UPDATE services SET {set_clause} WHERE service_id = {data['service_id']}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != 'progress_id'])
        query = f"UPDATE progress SET {set_clause} WHERE progress_id = {data['progress_id']}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_resource', methods=['POST'])
def update_resource():
    if 'loggedin' in session and session['username'] == 'admin':
        data = request.json
        set_clause = ", ".join([f"{key} = '{value}'" for key, value in data.items() if key != 'resource_id'])
        query = f"UPDATE resources SET {set_clause} WHERE resource_id = {data['resource_id']}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    return redirect(url_for('login'))

@app.route('/update_service_image/<service_id>', methods=['POST'])
def update_service_image(service_id):
    if 'loggedin' in session and session['username'] == 'admin':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            conn = get_db_connection()
            cursor = conn.cursor()
            query = "UPDATE services SET image = %s WHERE service_id = %s"
            cursor.execute(query, (file_url, service_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"status": "success", "file_url": file_url})
    return redirect(url_for('login'))

@app.route('/update_resource_file_url/<resource_id>', methods=['POST'])
def update_resource_file_url(resource_id):
    if 'loggedin' in session and session['username'] == 'admin':
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "No file part"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            conn = get_db_connection()
            cursor = conn.cursor()
            query = "UPDATE resources SET file_url = %s WHERE resource_id = %s"
            cursor.execute(query, (file_url, resource_id))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"status": "success", "file_url": file_url})
    return redirect(url_for('login'))

@app.route('/fetch_bookings', methods=['GET'])
def fetch_bookings():
    if 'loggedin' in session:
        user_id = session['id']  # Assuming you store the user ID in the session
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, phone_number, address, service_name, visit_date
            FROM bookings
            WHERE user_id = %s
        """, (user_id,))
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()

        booking_list = []
        for booking in bookings:
            booking_list.append({
                'name': booking[0],
                'phone_number': booking[1],
                'address': booking[2],
                'service_name': booking[3],
                'visit_date': booking[4]
            })

        return jsonify({'status': 'success', 'bookings': booking_list})
    else:
        return jsonify({'status': 'error', 'message': 'User not logged in'})
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=50100, threads=10)