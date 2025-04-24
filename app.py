import os
import asyncio
import json
import tempfile
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pdfkit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import components
from src.classifiers.enhanced_scenario_classifier import EnhancedScenarioClassifier
from src.policy_analyzer import PolicyAnalyzer
from src.risk_assessor import RiskAssessor
from src.explanation_generator import ExplanationGenerator
from src.recommendation_engine import RecommendationEngine

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")

# Configure file upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'jpg', 'jpeg', 'png'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Initialize components
classifier = EnhancedScenarioClassifier()
policy_analyzer = PolicyAnalyzer()
risk_assessor = RiskAssessor()
explanation_generator = ExplanationGenerator()
recommendation_engine = RecommendationEngine()

# Sample user profiles
SAMPLE_USERS = {
    "user1": {
        "id": "user1",
        "name": "John Doe",
        "email": "john@example.com",
        "password": "password",  # In a real app, this would be hashed
        "years_as_customer": 4,
        "other_policies": ["home_insurance"],
        "driving_record": {
            "accidents": 0,
            "violations": 1
        },
        "vehicle": {
            "make": "Toyota",
            "model": "Camry",
            "year": 2019,
            "value": 22000
        }
    },
    "user2": {
        "id": "user2",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "password": "password",  # In a real app, this would be hashed
        "years_as_customer": 2,
        "other_policies": [],
        "driving_record": {
            "accidents": 1,
            "violations": 0
        },
        "vehicle": {
            "make": "Honda",
            "model": "Civic",
            "year": 2020,
            "value": 24000
        }
    }
}

# Sample history for dashboard
SAMPLE_HISTORY = [
    {
        "id": "case-001",
        "date": "2025-02-10",
        "scenario_type": "collision",
        "risk_level": "high",
        "status": "resolved",
        "description": "Rear-end collision at traffic light"
    },
    {
        "id": "case-002",
        "date": "2025-02-15",
        "scenario_type": "parking_damage",
        "risk_level": "moderate",
        "status": "pending",
        "description": "Door scratch in parking lot"
    },
    {
        "id": "case-003",
        "date": "2025-02-20",
        "scenario_type": "weather_damage",
        "risk_level": "moderate",
        "status": "resolved",
        "description": "Hail damage to roof and hood"
    },
    {
        "id": "case-004",
        "date": "2025-02-25",
        "scenario_type": "theft",
        "risk_level": "high",
        "status": "investigating",
        "description": "Vehicle stolen from apartment complex"
    }
]

# Add global template context
@app.context_processor
def inject_globals():
    return {
        'SAMPLE_USERS': SAMPLE_USERS
    }

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form['username']
        password = request.form['password']

        # Simple authentication for demo
        if user_id in SAMPLE_USERS and SAMPLE_USERS[user_id]["password"] == password:
            session['user_id'] = user_id
            flash(f'Welcome back, {SAMPLE_USERS[user_id]["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['username']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Simple validation
        if user_id in SAMPLE_USERS:
            flash('Username already exists', 'danger')
            return render_template('register.html')

        # Create new user
        SAMPLE_USERS[user_id] = {
            "id": user_id,
            "name": name,
            "email": email,
            "password": password,
            "years_as_customer": 0,
            "other_policies": [],
            "driving_record": {
                "accidents": 0,
                "violations": 0
            },
            "vehicle": {
                "make": "",
                "model": "",
                "year": datetime.now().year,
                "value": 0
            }
        }

        # Log the user in
        session['user_id'] = user_id
        flash('Account created successfully!', 'success')
        return redirect(url_for('profile_setup'))

    return render_template('register.html')

@app.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def profile_setup():
    user_id = session['user_id']
    user = SAMPLE_USERS.get(user_id)

    if request.method == 'POST':
        # Update vehicle info
        user['vehicle']['make'] = request.form['vehicle_make']
        user['vehicle']['model'] = request.form['vehicle_model']
        user['vehicle']['year'] = int(request.form['vehicle_year'])
        user['vehicle']['value'] = int(request.form['vehicle_value'])

        # Update other info
        user['years_as_customer'] = int(request.form['years_as_customer'])

        # Handle other policies
        other_policies = []
        if 'home_insurance' in request.form:
            other_policies.append('home_insurance')
        if 'life_insurance' in request.form:
            other_policies.append('life_insurance')
        if 'health_insurance' in request.form:
            other_policies.append('health_insurance')
        user['other_policies'] = other_policies

        # Handle driving record
        user['driving_record']['accidents'] = int(request.form['accidents'])
        user['driving_record']['violations'] = int(request.form['violations'])

        flash('Profile information updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('profile_setup.html', user=user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    user_id = session['user_id']
    user = SAMPLE_USERS.get(user_id)

    if request.method == 'POST':
        # Update personal info
        user['name'] = request.form['name']
        user['email'] = request.form['email']

        # Check if password is being updated
        if request.form.get('password'):
            user['password'] = request.form['password']

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('profile_edit.html', user=user)

@app.route('/dashboard')
@login_required
def dashboard():
    user = SAMPLE_USERS.get(session['user_id'])
    history = SAMPLE_HISTORY
    return render_template('dashboard.html', user=user, history=history)

@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    if request.method == 'POST':
        scenario_text = request.form.get('scenario_text', '')

        # Handle file upload
        uploaded_file = request.files.get('scenario_file')
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)

            # If it's a text file, append its content to the scenario
            if filename.endswith('.txt'):
                with open(file_path, 'r') as f:
                    additional_text = f.read()
                    scenario_text += "\n\nAdditional information from uploaded file:\n" + additional_text
            else:
                # For non-text files, just note the upload
                scenario_text += f"\n\nAdditional evidence provided: {filename}"

        if not scenario_text.strip():
            flash('Please provide a scenario description', 'warning')
            return redirect(url_for('analyze'))

        try:
            # Process scenario
            results = analyze_scenario(scenario_text)

            # Save to session for PDF generation
            session['latest_results'] = results

            return render_template('results.html', results=results)
        except Exception as e:
            flash(f'Error processing scenario: {str(e)}', 'danger')
            return redirect(url_for('analyze'))

    return render_template('analyze.html')

@run_async
async def analyze_scenario(scenario_text):
    """Analyze a scenario using our components."""
    user_id = session.get('user_id')
    user_profile = SAMPLE_USERS.get(user_id) if user_id else None

    # Process scenario
    classification = await classifier.classify_scenario(scenario_text)
    policy_analysis = policy_analyzer.analyze_policies(classification)
    risk_assessment = await risk_assessor.assess_risk(classification, scenario_text)
    explanation = await explanation_generator.generate_explanation(
        classification, policy_analysis, risk_assessment
    )
    recommendations = await recommendation_engine.generate_recommendations(
        classification, policy_analysis, risk_assessment, user_profile
    )

    # Generate a unique case ID
    case_id = f"case-{uuid.uuid4().hex[:8]}"

    # Add current date
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Combine results
    results = {
        "case_id": case_id,
        "date": current_date,
        "scenario_text": scenario_text,
        "classification": classification,
        "policy_analysis": policy_analysis,
        "risk_assessment": risk_assessment,
        "explanation": explanation,
        "recommendations": recommendations,
        "user_profile": user_profile
    }

    return results

@app.route('/generate_pdf')
@login_required
def generate_pdf():
    """Generate a PDF report of the latest analysis."""
    if 'latest_results' not in session:
        flash('No recent analysis found', 'warning')
        return redirect(url_for('dashboard'))

    results = session['latest_results']

    # Create a temporary HTML file for the PDF
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        html_path = f.name
        html_content = render_template('pdf_template.html', results=results)
        f.write(html_content.encode('utf-8'))

    # Generate PDF from HTML
    pdf_path = html_path.replace('.html', '.pdf')
    try:
        pdfkit.from_file(html_path, pdf_path)
        return send_file(pdf_path, as_attachment=True, download_name=f"analysis_{results['case_id']}.pdf")
    except Exception as e:
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        # Clean up temporary files
        if os.path.exists(html_path):
            os.remove(html_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

@app.route('/sample_scenarios')
@login_required
def sample_scenarios():
    scenarios = [
        {
            "title": "Rear-End Collision",
            "text": """I was stopped at a red light when another driver rear-ended my car.
            There was visible damage to my rear bumper, and I'm experiencing some neck pain.
            The incident occurred on a clear day with good visibility. The other driver
            admitted fault and we exchanged insurance information."""
        },
        {
            "title": "Parking Lot Damage",
            "text": """While my car was parked at the grocery store, someone scratched
            the driver's side door. The scratch is deep and goes across both doors.
            I was only in the store for about 30 minutes. There were no witnesses
            and no note was left."""
        },
        {
            "title": "Weather Damage",
            "text": """My car was damaged during a severe hailstorm last night. There are
            multiple dents on the hood and roof of the vehicle. I had parked on the street
            because my garage was full. The weather service had issued a severe weather
            warning for our area."""
        },
        {
            "title": "Vehicle Theft",
            "text": """My car was stolen from outside my apartment building last night.
            I parked it at around 9 PM and discovered it was missing at 7 AM when I was
            leaving for work. I've filed a police report, and they said there have been
            several similar thefts in the area recently."""
        }
    ]
    return render_template('sample_scenarios.html', scenarios=scenarios)

@app.route('/analyze_sample/<int:scenario_id>')
@login_required
def analyze_sample(scenario_id):
    scenarios = [
        {
            "title": "Rear-End Collision",
            "text": """I was stopped at a red light when another driver rear-ended my car.
            There was visible damage to my rear bumper, and I'm experiencing some neck pain.
            The incident occurred on a clear day with good visibility. The other driver
            admitted fault and we exchanged insurance information."""
        },
        {
            "title": "Parking Lot Damage",
            "text": """While my car was parked at the grocery store, someone scratched
            the driver's side door. The scratch is deep and goes across both doors.
            I was only in the store for about 30 minutes. There were no witnesses
            and no note was left."""
        },
        {
            "title": "Weather Damage",
            "text": """My car was damaged during a severe hailstorm last night. There are
            multiple dents on the hood and roof of the vehicle. I had parked on the street
            because my garage was full. The weather service had issued a severe weather
            warning for our area."""
        },
        {
            "title": "Vehicle Theft",
            "text": """My car was stolen from outside my apartment building last night.
            I parked it at around 9 PM and discovered it was missing at 7 AM when I was
            leaving for work. I've filed a police report, and they said there have been
            several similar thefts in the area recently."""
        }
    ]

    if scenario_id < 0 or scenario_id >= len(scenarios):
        flash('Invalid scenario selected', 'danger')
        return redirect(url_for('sample_scenarios'))

    try:
        # Process scenario
        results = analyze_scenario(scenarios[scenario_id]["text"])

        # Save to session for PDF generation
        session['latest_results'] = results

        return render_template('results.html', results=results)
    except Exception as e:
        flash(f'Error processing scenario: {str(e)}', 'danger')
        return redirect(url_for('sample_scenarios'))

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API endpoint for scenario analysis."""
    # Check for API key (simple implementation)
    api_key = request.headers.get('X-API-Key')
    if api_key != os.getenv("API_KEY", "demo_key"):
        return jsonify({"error": "Unauthorized"}), 401

    # Get request data
    data = request.get_json()
    if not data or 'scenario_text' not in data:
        return jsonify({"error": "Missing scenario_text"}), 400

    scenario_text = data['scenario_text']
    user_profile = data.get('user_profile')

    try:
        # Process scenario asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Process scenario
        classification = loop.run_until_complete(classifier.classify_scenario(scenario_text))
        policy_analysis = policy_analyzer.analyze_policies(classification)
        risk_assessment = loop.run_until_complete(risk_assessor.assess_risk(classification, scenario_text))

        include_explanation = data.get('include_explanation', True)
        include_recommendations = data.get('include_recommendations', True)

        explanation = None
        if include_explanation:
            explanation = loop.run_until_complete(explanation_generator.generate_explanation(
                classification, policy_analysis, risk_assessment
            ))

        recommendations = None
        if include_recommendations:
            recommendations = loop.run_until_complete(recommendation_engine.generate_recommendations(
                classification, policy_analysis, risk_assessment, user_profile
            ))

        # Combine results
        results = {
            "classification": classification,
            "policy_analysis": policy_analysis,
            "risk_assessment": risk_assessment
        }

        if explanation:
            results["explanation"] = explanation

        if recommendations:
            results["recommendations"] = recommendations

        loop.close()

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/docs')
def api_docs():
    """API documentation page."""
    return render_template('api_docs.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
