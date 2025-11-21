


# TrustAI Flask Application
# Main application with authentication, consent, decisions, explanations, bias detection, and audit endpoints

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from datetime import datetime, timezone
import os
import json
import uuid
from functools import wraps
import logging

# Import models
from backend.models import (
    db,
    User,
    AIDecision,
    Explanation,
    Consent,
    AuditLog,
    BiasAlert,
    ModelPerformance,
    NotificationPreference,
    DecisionOverride,
    create_sample_data
)

# Import AI services
from backend.services.ai_explainer import AIExplainerService
from backend.services.bias_detector import BiasDetectorService
from backend.services.model_manager import ModelManagerService

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///trustai.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _parse_bool(value):
    """Convert various truthy representations to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'on']
    return bool(value)

def _get_notification_preferences(user_id):
    """Fetch or create default notification preferences for a user."""
    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not prefs:
        prefs = NotificationPreference(
            user_id=user_id,
            email_enabled=True,
            weekly_summary_enabled=True
        )
        db.session.add(prefs)
        db.session.commit()
    return prefs

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(user_id)

# Decorators for role-based access control
def role_required(*roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def audit_log(action_type, resource_type=None, resource_id=None, details=None, status='success', risk_level='low'):
    """Create audit log entry"""
    try:
        log_entry = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            risk_level=risk_level,
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            user_agent=request.headers.get('User-Agent', '')
        )
        log_entry.set_action_details(details)
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")

# Authentication Routes
@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Unified role-based dashboard"""
    return render_template('dashboard.html')

@app.route('/customer_dashboard')
@login_required
@role_required('customer', 'customer_service', 'compliance_officer', 'admin', 'compliance_officer')
def customer_dashboard():
    """Legacy customer dashboard route - redirect to unified dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/admin_panel')
@login_required
@role_required('admin', 'compliance_officer')
def admin_panel():
    """Legacy admin panel route - redirect to unified dashboard"""
    return redirect(url_for('dashboard'))

# API Routes
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                return jsonify({'error': 'Account is disabled'}), 403
            
            login_user(user)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            audit_log('login', details={'email': email})
            
            return jsonify({
                'token': 'mock-jwt-token',  # In production, use real JWT
                'user': user.to_dict()
            })
        
        audit_log('login', details={'email': email, 'reason': 'invalid_credentials'}, status='failure', risk_level='medium')
        return jsonify({'error': 'Invalid email or password'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """API registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['firstName', 'lastName', 'email', 'role', 'password', 'confirmPassword']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if passwords match
        if data['password'] != data['confirmPassword']:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create new user
        user = User(
            email=data['email'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            role=data['role'],
            department=data.get('department')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create default consents
        default_consents = [
            Consent(
                user_id=user.id,
                consent_type='credit_scoring',
                purpose_description='AI-based credit assessment and loan approval decisions'
            ),
            Consent(
                user_id=user.id,
                consent_type='fraud_detection',
                purpose_description='Pattern recognition for fraudulent activity detection'
            ),
            Consent(
                user_id=user.id,
                consent_type='personalized_offers',
                purpose_description='Personalized product recommendations'
            ),
            Consent(
                user_id=user.id,
                consent_type='risk_profiling',
                purpose_description='Behavioral analysis for risk assessment'
            )
        ]
        
        db.session.add_all(default_consents)
        db.session.commit()
        
        audit_log('register', details={'email': data['email'], 'role': data['role']})
        
        return jsonify({'message': 'Registration successful'})
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    """API logout endpoint"""
    audit_log('logout')
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

# Dashboard API Routes
@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """Get dashboard statistics with real-time data"""
    try:
        from datetime import datetime, timezone, timedelta
        
        # Get 24-hour timeframe
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        if current_user.role in ['admin', 'compliance_officer']:
            # Admin/Compliance gets system-wide statistics
            total_decisions = AIDecision.query.count()
            decisions_24h = AIDecision.query.filter(AIDecision.created_at >= last_24h).count()
            
            total_users = User.query.filter_by(is_active=True).count()
            active_users_24h = User.query.filter(
                User.last_login >= last_24h,
                User.is_active == True
            ).count()
            
            total_consents = Consent.query.filter_by(is_granted=True).count()
            consents_24h = Consent.query.filter(
                Consent.is_granted == True,
                Consent.created_at >= last_24h
            ).count()
            
            # Bias metrics
            bias_alerts = BiasAlert.query.filter_by(investigation_status='open').count()
            critical_alerts = BiasAlert.query.filter_by(severity='critical', investigation_status='open').count()
            
            # Model performance metrics
            avg_fairness = 0
            if total_decisions > 0:
                decisions_with_explanations = AIDecision.query.join(Explanation).all()
                if decisions_with_explanations:
                    fairness_scores = []
                    for decision in decisions_with_explanations:
                        if decision.explanation and decision.explanation.fairness_metrics:
                            metrics = decision.explanation.get_fairness_metrics()
                            if 'overall_accuracy' in metrics:
                                fairness_scores.append(metrics['overall_accuracy'])
                    avg_fairness = int(sum(fairness_scores) / len(fairness_scores) * 100) if fairness_scores else 0
            
            # Recent activity trends
            hourly_decisions = []
            for i in range(24):
                hour_start = now - timedelta(hours=i+1)
                hour_end = now - timedelta(hours=i)
                count = AIDecision.query.filter(
                    AIDecision.created_at >= hour_start,
                    AIDecision.created_at < hour_end
                ).count()
                hourly_decisions.append(count)
            
            return jsonify({
                'totalDecisions': total_decisions,
                'decisions24h': decisions_24h,
                'totalUsers': total_users,
                'activeUsers24h': active_users_24h,
                'totalConsents': total_consents,
                'consents24h': consents_24h,
                'fairnessScore': avg_fairness,
                'biasAlerts': bias_alerts,
                'criticalAlerts': critical_alerts,
                'hourlyDecisions': hourly_decisions[::-1],  # Reverse to show oldest to newest
                'systemHealth': {
                    'status': 'operational',
                    'uptime': '99.9%',
                    'responseTime': '120ms'
                },
                'lastUpdated': now.isoformat()
            })
        
        else:
            # Customer gets personal statistics
            user_decisions = AIDecision.query.filter_by(user_id=current_user.id).count()
            user_decisions_24h = AIDecision.query.filter(
                AIDecision.user_id == current_user.id,
                AIDecision.created_at >= last_24h
            ).count()
            
            user_consents = Consent.query.filter_by(user_id=current_user.id, is_granted=True).count()
            
            # Get average fairness score from user's decisions
            avg_fairness = 0
            if user_decisions > 0:
                decisions_with_explanations = AIDecision.query.filter_by(user_id=current_user.id).join(Explanation).all()
                if decisions_with_explanations:
                    fairness_scores = []
                    for decision in decisions_with_explanations:
                        if decision.explanation and decision.explanation.fairness_metrics:
                            metrics = decision.explanation.get_fairness_metrics()
                            if 'overall_accuracy' in metrics:
                                fairness_scores.append(metrics['overall_accuracy'])
                    avg_fairness = int(sum(fairness_scores) / len(fairness_scores) * 100) if fairness_scores else 0
            
            # Get bias alerts count
            bias_alerts = BiasAlert.query.filter_by(investigation_status='open').count()
            
            return jsonify({
                'decisions': user_decisions,
                'decisions24h': user_decisions_24h,
                'consents': user_consents,
                'fairnessScore': avg_fairness,
                'biasAlerts': bias_alerts,
                'lastUpdated': now.isoformat()
            })
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'error': 'Failed to get dashboard stats'}), 500

@app.route('/api/decisions')
@login_required
def get_decisions():
    """Get AI decisions, scoped by role"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        query = AIDecision.query
        if current_user.role not in ['admin', 'compliance_officer']:
            query = query.filter_by(user_id=current_user.id)

        decisions = query.order_by(AIDecision.created_at.desc()).paginate(page=page, per_page=per_page)

        return jsonify({
            'decisions': [decision.to_dict() for decision in decisions.items],
            'total': decisions.total,
            'pages': decisions.pages,
            'current_page': page
        })

    except Exception as e:
        logger.error(f"Get decisions error: {str(e)}")
        return jsonify({'error': 'Failed to get decisions'}), 500

@app.route('/api/decisions/<decision_id>/explain')
@login_required
def explain_decision(decision_id):
    """Get explanation for a specific decision"""
    try:
        decision = AIDecision.query.filter_by(id=decision_id, user_id=current_user.id).first()
        if not decision:
            return jsonify({'error': 'Decision not found'}), 404
        
        if decision.explanation:
            return jsonify(decision.explanation.to_dict())
        else:
            # Generate explanation on-demand
            explainer = AIExplainerService()
            explanation = explainer.explain_decision(decision)
            return jsonify(explanation)
        
    except Exception as e:
        logger.error(f"Explain decision error: {str(e)}")
        return jsonify({'error': 'Failed to generate explanation'}), 500

# Consent Management API
@app.route('/api/consent/update', methods=['PUT'])
@login_required
def update_consent():
    """Update user consent"""
    try:
        data = request.get_json()
        consent_id = data.get('consentId')
        granted = data.get('granted')
        
        if not consent_id:
            return jsonify({'error': 'Consent ID is required'}), 400
        
        consent = Consent.query.filter_by(id=consent_id, user_id=current_user.id).first()
        if not consent:
            return jsonify({'error': 'Consent not found'}), 404
        
        if granted:
            consent.grant()
        else:
            consent.revoke()
        
        db.session.commit()
        
        audit_log('consent_update', resource_type='consent', resource_id=consent_id, 
                 details={'granted': granted})
        
        return jsonify({'message': 'Consent updated successfully'})
        
    except Exception as e:
        logger.error(f"Update consent error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update consent'}), 500

@app.route('/api/consents')
@login_required
def get_consents():
    """Get user's consents"""
    try:
        consents = Consent.query.filter_by(user_id=current_user.id).all()
        return jsonify([consent.to_dict() for consent in consents])
        
    except Exception as e:
        logger.error(f"Get consents error: {str(e)}")
        return jsonify({'error': 'Failed to get consents'}), 500

@app.route('/api/notifications/preferences', methods=['GET', 'PUT'])
@login_required
def notification_preferences():
    """Get or update notification preferences"""
    try:
        if request.method == 'GET':
            target_user_id = request.args.get('user_id')
        else:
            payload = request.get_json() or {}
            target_user_id = payload.get('userId')

        if target_user_id and current_user.role not in ['admin', 'compliance_officer']:
            return jsonify({'error': 'Insufficient permissions to view other users'}), 403

        target_user = User.query.get(target_user_id) if target_user_id else current_user
        if not target_user:
            return jsonify({'error': 'Target user not found'}), 404

        prefs = _get_notification_preferences(target_user.id)

        if request.method == 'GET':
            return jsonify(prefs.to_dict())

        # Update preferences
        updatable_fields = {
            'email_enabled': 'emailEnabled',
            'sms_enabled': 'smsEnabled',
            'push_enabled': 'pushEnabled',
            'weekly_summary_enabled': 'weeklySummaryEnabled',
            'critical_alerts_only': 'criticalAlertsOnly'
        }

        for model_attr, payload_key in updatable_fields.items():
            if payload_key in payload:
                setattr(prefs, model_attr, _parse_bool(payload[payload_key]))

        quiet_hours = payload.get('quietHours')
        if quiet_hours:
            start = quiet_hours.get('start')
            end = quiet_hours.get('end')
            if start:
                prefs.quiet_hours_start = start
            if end:
                prefs.quiet_hours_end = end

        if 'preferredChannels' in payload:
            prefs.set_preferred_channels(payload.get('preferredChannels'))

        db.session.commit()

        audit_log(
            'notification_preferences_update',
            resource_type='notification_preference',
            resource_id=prefs.id,
            details={'updated_fields': list(payload.keys())}
        )

        return jsonify({'message': 'Preferences updated', 'preferences': prefs.to_dict()})

    except Exception as e:
        logger.error(f"Notification preferences error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process notification preferences'}), 500

# Bias Monitoring API
@app.route('/api/bias/metrics')
@login_required
@role_required('admin', 'compliance_officer')
def get_bias_metrics():
    """Get bias monitoring metrics"""
    try:
        bias_detector = BiasDetectorService()
        metrics = bias_detector.get_current_metrics()
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Get bias metrics error: {str(e)}")
        return jsonify({'error': 'Failed to get bias metrics'}), 500

@app.route('/api/bias/alerts')
@login_required
@role_required('admin', 'compliance_officer')
def get_bias_alerts():
    """Get bias alerts"""
    try:
        alerts = BiasAlert.query.order_by(BiasAlert.created_at.desc()).limit(50).all()
        return jsonify([alert.to_dict() for alert in alerts])
        
    except Exception as e:
        logger.error(f"Get bias alerts error: {str(e)}")
        return jsonify({'error': 'Failed to get bias alerts'}), 500

# Audit Log API
@app.route('/api/audit/logs')
@login_required
@role_required('admin', 'compliance_officer')
def get_audit_logs():
    """Get audit logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return jsonify([log.to_dict() for log in logs])
        
    except Exception as e:
        logger.error(f"Get audit logs error: {str(e)}")
        return jsonify({'error': 'Failed to get audit logs'}), 500

# Model Management API
@app.route('/api/models/performance')
@login_required
@role_required('admin', 'compliance_officer')
def get_model_performance():
    """Get model performance metrics"""
    try:
        performances = ModelPerformance.query.order_by(ModelPerformance.evaluation_date.desc()).limit(100).all()
        return jsonify([perf.to_dict() for perf in performances])
        
    except Exception as e:
        logger.error(f"Get model performance error: {str(e)}")
        return jsonify({'error': 'Failed to get model performance'}), 500

# AI Decision Simulation
@app.route('/api/decisions/simulate', methods=['POST'])
@login_required
def simulate_decision():
    """Simulate an AI decision for testing"""
    try:
        data = request.get_json()
        decision_type = data.get('decision_type', 'loan_approval')
        input_data = data.get('input_data', {})
        
        model_manager = ModelManagerService()
        result = model_manager.make_decision(decision_type, input_data, current_user.id)
        
        # Create decision record
        decision = AIDecision(
            user_id=current_user.id,
            decision_type=decision_type,
            model_name=result['model_name'],
            model_version=result['model_version'],
            outcome=result['outcome'],
            confidence_score=result['confidence'],
            processing_time_ms=result['processing_time_ms']
        )
        decision.set_input_data(input_data)
        decision.set_metadata(result.get('metadata', {}))
        
        db.session.add(decision)
        db.session.flush()  # Get the decision ID
        
        # Generate explanation
        explainer = AIExplainerService()
        explanation = explainer.explain_decision(decision)
        
        # Check for bias
        bias_detector = BiasDetectorService()
        bias_alerts = bias_detector.check_decision_bias(decision, explanation)
        
        db.session.commit()
        
        audit_log('ai_decision', resource_type='decision', resource_id=decision.id,
                 details={'decision_type': decision_type, 'outcome': result['outcome']})
        
        return jsonify({
            'decision': decision.to_dict(),
            'explanation': explanation,
            'bias_alerts': [alert.to_dict() for alert in bias_alerts]
        })
        
    except Exception as e:
        logger.error(f"Simulate decision error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to simulate decision'}), 500

@app.route('/api/decisions/override', methods=['POST'])
@login_required
@role_required('admin', 'compliance_officer')
def override_decision_api():
    """Manually override an AI decision outcome"""
    try:
        data = request.get_json() or {}
        decision_id = data.get('decisionId')
        new_outcome = data.get('newOutcome')
        reason = data.get('reason')
        reviewer_notes = data.get('reviewerNotes')
        risk_level = data.get('riskLevel', 'medium')

        if not decision_id or not new_outcome or not reason:
            return jsonify({'error': 'decisionId, newOutcome, and reason are required'}), 400

        decision = AIDecision.query.filter_by(id=decision_id).first()
        if not decision:
            return jsonify({'error': 'Decision not found'}), 404

        old_outcome = decision.outcome
        decision.outcome = new_outcome

        override_record = DecisionOverride(
            decision_id=decision.id,
            requested_by=current_user.id,
            approved_by=current_user.id,
            target_user_id=decision.user_id,
            old_outcome=old_outcome,
            new_outcome=new_outcome,
            reason=reason,
            reviewer_notes=reviewer_notes,
            status='applied',
            risk_level=risk_level
        )

        db.session.add(override_record)
        db.session.commit()

        audit_log(
            'decision_override',
            resource_type='decision',
            resource_id=decision.id,
            details={
                'old_outcome': old_outcome,
                'new_outcome': new_outcome,
                'risk_level': risk_level
            },
            risk_level='high' if risk_level in ['high', 'critical'] else 'medium'
        )

        return jsonify({
            'message': 'Decision override applied',
            'decision': decision.to_dict(),
            'override': override_record.to_dict()
        })

    except Exception as e:
        logger.error(f"Decision override error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to override decision'}), 500

# Export API
@app.route('/api/export')
@login_required
@role_required('admin', 'compliance_officer')
def export_data():
    """Export system data"""
    try:
        format_type = request.args.get('format', 'json')
        
        if format_type not in ['json', 'csv']:
            return jsonify({'error': 'Unsupported format'}), 400
        
        # Collect data
        export_data = {
            'users': [user.to_dict() for user in User.query.all()],
            'decisions': [decision.to_dict() for decision in AIDecision.query.all()],
            'consents': [consent.to_dict() for consent in Consent.query.all()],
            'audit_logs': [log.to_dict() for log in AuditLog.query.limit(1000).all()],
            'bias_alerts': [alert.to_dict() for alert in BiasAlert.query.all()],
            'export_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        audit_log('data_export', details={'format': format_type}, risk_level='medium')
        
        if format_type == 'json':
            response = make_response(jsonify(export_data))
            response.headers['Content-Disposition'] = f'attachment; filename=trustai_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            response.headers['Content-Type'] = 'application/json'
            return response
        
        # CSV export would require additional implementation
        return jsonify({'error': 'CSV export not implemented yet'}), 501
        
    except Exception as e:
        logger.error(f"Export data error: {str(e)}")
        return jsonify({'error': 'Failed to export data'}), 500

# Initialize database and sample data
@app.before_request
def create_tables():
    """Create database tables and sample data"""
    if not hasattr(app, '_tables_created'):
        db.create_all()
        app._tables_created = True
    
    # Check if admin user exists
    if not User.query.filter_by(email='admin@trustai.com').first():
        create_sample_data()
        logger.info("Sample data created")

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0'
    })

# CLI commands for database management
@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    create_sample_data()
    print("Database initialized with sample data!")

@app.cli.command()
def reset_db():
    """Reset the database"""
    db.drop_all()
    db.create_all()
    create_sample_data()
    print("Database reset and initialized!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
