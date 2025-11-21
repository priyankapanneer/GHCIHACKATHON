# TrustAI - Ethical AI Governance Platform for Banking

TrustAI is a comprehensive ethical AI governance platform designed specifically for banking institutions. It provides transparency, explainability, and bias monitoring for AI-driven decision-making processes.

## Features

### 🔐 **Authentication & Role-Based Access Control**
- Multi-role user system (Customer, Customer Service, Compliance Officer, Admin)
- Secure authentication with role-based permissions
- Comprehensive audit logging

### 🤖 **AI Decision Management**
- Real-time AI decision tracking and monitoring
- Multiple decision types (loan approval, credit limit, risk assessment, fraud detection)
- Decision confidence scoring and processing metrics

### 📊 **AI Explainability**
- SHAP (SHapley Additive exPlanations) integration
- LIME (Local Interpretable Model-agnostic Explanations) support
- Human-readable explanations for AI decisions
- Feature importance visualization

### ⚖️ **Bias Detection & Monitoring**
- Real-time bias detection across protected attributes
- Fairness metrics calculation (demographic parity, equal opportunity, predictive parity)
- Automated bias alerts and notifications
- Comprehensive bias reporting

### 📋 **Consent Management**
- Granular consent tracking for different AI services
- Consent history and audit trail
- User-controlled data usage permissions

### 📈 **Dashboard & Analytics**
- Customer dashboard with personal AI insights
- Admin panel with system-wide monitoring
- Real-time metrics and visualizations
- Performance tracking and trend analysis

### 🔍 **Audit & Compliance**
- Immutable audit logs for all system activities
- Risk-based activity classification
- Export capabilities for compliance reporting

## Technology Stack

### Frontend
- **HTML5** with semantic markup
- **Bootstrap 5** for responsive design
- **Vanilla JavaScript** for client-side logic
- **Plotly.js** for data visualization
- **FontAwesome** for icons

### Backend
- **Python 3.8+**
- **Flask** web framework
- **Flask-SQLAlchemy** for ORM
- **Flask-Login** for authentication
- **Flask-CORS** for cross-origin requests

### Database
- **SQLite** for development (easily portable to PostgreSQL/MySQL)

### AI/ML Libraries
- **scikit-learn** for machine learning models
- **XGBoost** for gradient boosting
- **SHAP** for explainability
- **LIME** for local explanations
- **NumPy & Pandas** for data processing

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ghcihackathon
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   # Default values are provided for development
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Login with sample credentials:
     - **Admin**: `admin@trustai.com` / `admin123`
     - **Customer**: `customer@trustai.com` / `customer123`
     - **Compliance**: `compliance@trustai.com` / `compliance123`

## Project Structure

```
ghcihackathon/
├── app.py                      # Main Flask application
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── README.md                   # This file
├── static/
│   ├── css/
│   │   └── styles.css         # Custom CSS with banking theme
│   └── js/
│       └── main.js            # Frontend JavaScript logic
├── templates/
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── customer_dashboard.html # Customer dashboard
│   └── admin_panel.html       # Admin control panel
├── backend/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy database models
│   └── services/
│       ├── __init__.py
│       ├── ai_explainer.py    # AI explainability service
│       ├── bias_detector.py   # Bias detection service
│       └── model_manager.py   # ML model management
└── instance/
    └── trustai.db             # SQLite database (created automatically)
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout

### Dashboard
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/decisions` - User AI decisions
- `GET /api/decisions/{id}/explain` - Decision explanation

### Consent Management
- `GET /api/consents` - User consents
- `PUT /api/consent/update` - Update consent

### Bias Monitoring (Admin/Compliance)
- `GET /api/bias/metrics` - Current bias metrics
- `GET /api/bias/alerts` - Bias alerts

### Audit & Compliance (Admin/Compliance)
- `GET /api/audit/logs` - Audit logs
- `GET /api/models/performance` - Model performance metrics

### AI Simulation
- `POST /api/decisions/simulate` - Simulate AI decision

## Configuration

### Environment Variables
- `FLASK_APP=app.py` - Flask application file
- `FLASK_ENV=development` - Flask environment (development/production)
- `SECRET_KEY` - Flask secret key (change in production)
- `DATABASE_URL=sqlite:///trustai.db` - Database connection string

### Model Configuration
Models are automatically initialized with sample data. In production, you would:
1. Train models with your historical data
2. Save trained models using the model manager
3. Update model configurations in `backend/services/model_manager.py`

### Bias Detection Thresholds
Bias detection thresholds can be configured in `backend/services/bias_detector.py`:
- `demographic_parity`: 0.80
- `equal_opportunity`: 0.80
- `predictive_parity`: 0.80
- `disparate_impact`: 0.80

## User Roles & Permissions

| Role | Permissions | Access |
|------|-------------|--------|
| **Customer** | View own decisions, manage consents | Customer Dashboard |
| **Customer Service** | View customer decisions, basic reports | Customer Dashboard |
| **Compliance Officer** | All customer views, bias monitoring, audit logs | Customer Dashboard + Admin Panel |
| **Admin** | Full system access, user management, system configuration | Customer Dashboard + Admin Panel |

## AI Models

The platform includes lightweight models for demonstration:

### Loan Approval Model
- **Type**: Random Forest
- **Features**: Credit score, income, debt-to-income ratio, employment length, age
- **Output**: Approved/Rejected with confidence score

### Credit Limit Model
- **Type**: XGBoost
- **Features**: Credit score, income, current limit, payment history
- **Output**: Limit increase/no change

### Risk Assessment Model
- **Type**: Decision Tree
- **Features**: Credit score, payment history, delinquencies, credit utilization
- **Output**: Low/High risk classification

### Fraud Detection Model
- **Type**: Logistic Regression
- **Features**: Transaction amount, frequency, merchant category, location
- **Output**: Legitimate/Fraudulent

## Fairness Metrics

The platform tracks multiple fairness metrics:

- **Demographic Parity**: Equal approval rates across demographic groups
- **Equal Opportunity**: Equal true positive rates across groups
- **Predictive Parity**: Equal positive predictive values across groups
- **Disparate Impact**: Ratio of favorable outcomes between groups
- **Overall Accuracy**: Model accuracy across all predictions

## Security Features

- **Role-based access control** with granular permissions
- **Secure password hashing** using Werkzeug
- **Audit logging** for all system activities
- **Input validation** and sanitization
- **CORS protection** for API endpoints
- **Session management** with Flask-Login

## Development

### Running Tests
```bash
# Run the application in development mode
python run.py

# The application will automatically create sample data
# and start on http://localhost:5000
```

### Database Management
```bash
# Initialize database with sample data
flask init-db

# Reset database (clear all data)
flask reset-db
```

### Adding New Models
1. Create model in `backend/services/model_manager.py`
2. Add feature definitions to `_initialize_models()`
3. Update bias detection if needed
4. Add API endpoints for new decision types

## Production Deployment

### Database Migration
For production, migrate from SQLite to PostgreSQL:
1. Install PostgreSQL adapter: `pip install psycopg2-binary`
2. Update `DATABASE_URL` in `.env`
3. Run database migrations

### Security Considerations
- Change `SECRET_KEY` in production
- Use HTTPS/WSS for all communications
- Implement proper logging and monitoring
- Set up regular database backups
- Configure firewall rules
- Enable rate limiting on API endpoints

### Scaling
- Deploy with Gunicorn or uWSGI
- Use Redis for session storage
- Implement database connection pooling
- Set up load balancing for multiple instances
- Configure monitoring and alerting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or support:
- Create an issue in the repository
- Contact the development team
- Review the documentation and code comments

## Acknowledgments

- SHAP library for explainability
- LIME library for local explanations
- scikit-learn for machine learning models
- Flask framework for web development
- Bootstrap for responsive UI components
