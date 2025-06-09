# Car Rental Platform 🚗

A Django-based web application that allows users to rent and list cars securely.

## Features

- User registration with driver's license verification
- Car listing with photos and location
- Car rental request system with notifications
- Internal messaging/chat after rental confirmation
- Admin approval, email notifications, and more

## Technologies

- Django + PostgreSQL
- HTML, CSS, JavaScript
- Leaflet.js for maps
- Bootstrap or custom styling

## Getting Started

```bash
git clone https://github.com/meowwwll/car-rental-platform.git
cd car-rental-platform
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
