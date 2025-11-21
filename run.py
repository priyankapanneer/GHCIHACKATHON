# TrustAI Application Runner
# Entry point for running the TrustAI application

import os
import sys
from app import app, db
from backend.models import create_sample_data

def main():
    """Main function to run the application"""
    # Set environment variables
    os.environ.setdefault('FLASK_APP', 'app.py')
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Check if we need to create sample data
        from backend.models import User
        if not User.query.first():
            print("Creating sample data...")
            create_sample_data()
            print("Sample data created successfully!")
    
    print("Starting TrustAI application...")
    print("Access the application at: http://localhost:5000")
    print("Login credentials:")
    print("  Admin: admin@trustai.com / admin123")
    print("  Customer: customer@trustai.com / customer123")
    print("  Compliance: compliance@trustai.com / compliance123")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
