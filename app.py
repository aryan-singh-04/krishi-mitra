import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from openai import OpenAI

import requests
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key')

SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')

# Your old .env may contain .../rest/v1/. Convert it to the Supabase project URL.
if SUPABASE_URL.endswith('/rest/v1'):
    SUPABASE_PROJECT_URL = SUPABASE_URL[:-8]
else:
    SUPABASE_PROJECT_URL = SUPABASE_URL


def auth_headers(access_token=None):
    headers = {
        'apikey': SUPABASE_ANON_KEY,
        'Content-Type': 'application/json',
    }
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    return headers


def supabase_ready():
    return bool(SUPABASE_PROJECT_URL and SUPABASE_ANON_KEY)


@app.route('/')
def home():
    return render_template('home.html', logged_in='access_token' in session)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not supabase_ready():
            flash('Supabase configuration missing. Add SUPABASE_ANON_KEY to .env.', 'error')
            return render_template('login.html')

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        response = requests.post(
            f'{SUPABASE_PROJECT_URL}/auth/v1/token?grant_type=password',
            headers=auth_headers(),
            json={'email': email, 'password': password},
            timeout=15,
        )

        if response.ok:
            data = response.json()
            session['access_token'] = data.get('access_token')
            session['refresh_token'] = data.get('refresh_token')
            session['user'] = data.get('user', {})
            return redirect(url_for('dashboard'))

        message = response.json().get('error_description', 'Login failed.')
        flash(message, 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if not supabase_ready():
            flash('Supabase configuration missing. Add SUPABASE_ANON_KEY to .env.', 'error')
            return render_template('signup.html')

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        response = requests.post(
            f'{SUPABASE_PROJECT_URL}/auth/v1/signup',
            headers=auth_headers(),
            json={'email': email, 'password': password},
            timeout=15,
        )

        if response.ok:
            data = response.json()
            if data.get('access_token'):
                session['access_token'] = data['access_token']
                session['refresh_token'] = data.get('refresh_token')
                session['user'] = data.get('user', {})
                return redirect(url_for('dashboard'))
            flash('Account created. Email verification may be required before login.', 'success')
            return redirect(url_for('login'))

        message = response.json().get('msg') or response.json().get('error_description') or 'Signup failed.'
        flash(message, 'error')

    return render_template('signup.html')
@app.route('/hisaab')
def hisaab():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    try:
        expense = float(request.args.get('expense', 0) or 0)
        income = float(request.args.get('income', 0) or 0)
    except ValueError:
        expense = 0
        income = 0

    profit = income - expense

    return render_template(
        'hisaab.html',
        expense=expense,
        income=income,
        profit=profit
    )
@app.route('/crop')
def crop():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    crops = {
        'wheat': {
            'name': 'गेहूँ',
            'season': 'रबी',
            'water': 'मध्यम',
            'soil': 'दोमट मिट्टी'
        },
        'rice': {
            'name': 'धान',
            'season': 'खरीफ',
            'water': 'अधिक',
            'soil': 'चिकनी मिट्टी'
        },
        'potato': {
            'name': 'आलू',
            'season': 'रबी',
            'water': 'मध्यम',
            'soil': 'दोमट मिट्टी'
        },
        'mustard': {
            'name': 'सरसों',
            'season': 'रबी',
            'water': 'कम',
            'soil': 'दोमट मिट्टी'
        }
    }

    selected_crop = request.args.get('crop', 'wheat')
    crop_info = crops.get(selected_crop, crops['wheat'])

    return render_template(
        'crop.html',
        crops=crops,
        selected_crop=selected_crop,
        crop_info=crop_info
    )
@app.route('/dashboard')
def dashboard():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    user = session.get('user', {})
    return render_template('dashboard.html', user=user)
@app.route('/weather')
def weather():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    city = request.args.get('city', 'Lucknow')

    response = requests.get(
        'https://api.openweathermap.org/data/2.5/weather',
        params={
            'q': city,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'hi'
        },
        timeout=10
    )

    if response.ok:
        data = response.json()
        return render_template('weather.html', weather=data, city=city)

    flash('Weather information नहीं मिल पाई।', 'error')
    return redirect(url_for('dashboard'))
@app.route('/crop-scan', methods=['GET', 'POST'])
def crop_scan():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    result = None

    if request.method == 'POST':
        image = request.files.get('crop_image')

        if not image:
            flash('कृपया फसल की फोटो चुनें।', 'error')
            return render_template('crop_scan.html', result=None)

        # AI detection अगला step में जोड़ेंगे
        result = 'Photo successfully received.'

    return render_template('crop_scan.html', result=result)
@app.route('/red-zone')
def red_zone():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    warnings = [
        {
            'title': '🌧️ ज्यादा बारिश',
            'message': 'बारिश ज्यादा होने पर खेत में पानी जमा होने से बचाएँ।'
        },
        {
            'title': '🌡️ ज्यादा तापमान',
            'message': 'गर्मी ज्यादा होने पर फसल की सिंचाई का ध्यान रखें।'
        },
        {
            'title': '🐛 कीट का खतरा',
            'message': 'फसल में कीट दिखाई देने पर समय पर निरीक्षण करें।'
        }
    ]

    return render_template('red_zone.html', warnings=warnings)
    return render_template('red_zone.html', warnings=warnings)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
    





if __name__ == '__main__':
    app.run(debug=True)
app