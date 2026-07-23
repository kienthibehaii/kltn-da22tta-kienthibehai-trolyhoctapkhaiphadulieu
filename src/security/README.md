# 🔒 RAG Security System

## ✅ Status: COMPLETE

## 📋 Overview

Hệ thống bảo mật production-ready cho RAG application với authentication, encryption, rate limiting, và security logging.

---

## 🎨 Features

### 1. Authentication & Authorization
- **User Registration** - Password strength validation
- **Login/Logout** - JWT token authentication
- **Session Management** - Secure session handling
- **Role-Based Access Control (RBAC)** - Admin, User, Guest roles
- **Account Lockout** - Protection against brute force
- **Password Hashing** - bcrypt with salt

### 2. Data Encryption
- **AES-256 Encryption** - Data at rest
- **Fernet Symmetric Encryption** - Conversation history
- **Field-Level Encryption** - Sensitive database fields
- **Secure Key Management** - Environment-based keys

### 3. API Security
- **Rate Limiting** - Per minute/hour/day limits
- **Request Validation** - SQL injection & XSS protection
- **Input Sanitization** - HTML escaping
- **CSRF Protection** - Token-based
- **Security Headers** - XSS, clickjacking protection

### 4. Security Logging
- **Audit Trail** - All security events logged
- **Suspicious Activity Detection** - Automatic alerts
- **Log Rotation** - Daily log files
- **Event Types** - Login, logout, unauthorized access, etc.

---

## 📦 Structure

```
security/
├── __init__.py              # Package initialization
├── auth.py                  # Authentication & authorization
├── encryption.py            # Data encryption utilities
├── rate_limiter.py          # API rate limiting
├── security_logger.py       # Security event logging
├── middleware.py            # Security middleware
└── README.md                # This file
```

---

## 🚀 Usage

### 1. Authentication

#### Register User
```python
from security import AuthManager

auth = AuthManager()

success, message = auth.register_user(
    username="john_doe",
    email="john@example.com",
    password="SecurePass@123",
    role=AuthManager.ROLE_USER
)

if success:
    print("User registered successfully")
```

#### Login
```python
success, message, token = auth.login("john_doe", "SecurePass@123")

if success:
    print(f"Login successful. Token: {token}")
    # Store token in session
```

#### Verify Token
```python
is_valid, payload = auth.verify_token(token)

if is_valid:
    print(f"User: {payload['username']}, Role: {payload['role']}")
```

#### Check Permissions
```python
has_permission = auth.has_permission(token, AuthManager.ROLE_ADMIN)

if has_permission:
    print("User has admin access")
```

### 2. Encryption

#### Encrypt Data
```python
from security import EncryptionManager

encryption = EncryptionManager()

# Encrypt string
encrypted = encryption.encrypt("sensitive data")

# Decrypt
decrypted = encryption.decrypt(encrypted)
```

#### Encrypt Conversation
```python
conversation = [
    {'role': 'user', 'content': 'What is data mining?'},
    {'role': 'assistant', 'content': 'Data mining is...'}
]

encrypted_conv = encryption.encrypt_conversation(conversation)
decrypted_conv = encryption.decrypt_conversation(encrypted_conv)
```

#### Encrypt Database Fields
```python
document = {
    'username': 'john_doe',
    'email': 'john@example.com',
    'api_key': 'secret_key_12345'
}

# Encrypt sensitive fields
encrypted_doc = encryption.encrypt_dict(document, ['api_key'])

# Decrypt
decrypted_doc = encryption.decrypt_dict(encrypted_doc, ['api_key'])
```

### 3. Rate Limiting

#### Basic Usage
```python
from security import RateLimiter

limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000,
    requests_per_day=10000
)

# Check if request is allowed
is_allowed, reason = limiter.is_allowed(client_id="user123")

if not is_allowed:
    print(f"Rate limit exceeded: {reason}")
```

#### With Streamlit
```python
from security import RateLimiter, check_rate_limit

limiter = RateLimiter()

# In Streamlit app
if check_rate_limit(limiter):
    # Process request
    pass
```

### 4. Security Logging

#### Log Events
```python
from security import SecurityLogger

logger = SecurityLogger()

# Log login success
logger.log_login_success("john_doe", "user123", "192.168.1.1")

# Log failed login
logger.log_login_failed("attacker", "192.168.1.100", "Invalid password")

# Log unauthorized access
logger.log_unauthorized_access("john_doe", "/admin", "192.168.1.1")
```

#### Get Statistics
```python
stats = logger.get_stats()

print(f"Total events: {stats['total_events']}")
print(f"By type: {stats['by_type']}")
print(f"By severity: {stats['by_severity']}")
```

### 5. Security Middleware

#### Validate Input
```python
from security.middleware import SecurityMiddleware

middleware = SecurityMiddleware()

# Validate input
is_valid, error_msg = middleware.validate_input(user_input)

if not is_valid:
    print(f"Invalid input: {error_msg}")
```

#### Sanitize Input
```python
# Sanitize user input
sanitized = middleware.sanitize_input(user_input)
```

#### Validate Email
```python
is_valid = middleware.validate_email("user@example.com")
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

### Required Variables

```env
# API Keys
GOOGLE_API_KEY=your_gemini_api_key

# Security
JWT_SECRET_KEY=your_jwt_secret_32_chars_minimum
ENCRYPTION_KEY=your_encryption_key_fernet_format
SESSION_SECRET=your_session_secret

# Database
MONGODB_URI=mongodb://localhost:27017/
```

### Generate Secrets

```bash
# JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Session Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🛡️ Security Best Practices

### 1. Password Security
- ✅ Minimum 8 characters
- ✅ Require uppercase, lowercase, digit, special character
- ✅ bcrypt hashing with salt
- ✅ Account lockout after 5 failed attempts
- ✅ Password change invalidates all sessions

### 2. Session Security
- ✅ JWT tokens with expiration
- ✅ Session timeout (24 hours default)
- ✅ Secure token storage
- ✅ Token invalidation on logout

### 3. Data Security
- ✅ Encrypt sensitive data at rest
- ✅ Encrypt conversation history
- ✅ Secure MongoDB connections
- ✅ Field-level encryption

### 4. API Security
- ✅ Rate limiting (60/min, 1000/hour, 10000/day)
- ✅ Input validation (SQL injection, XSS)
- ✅ Input sanitization
- ✅ CSRF protection
- ✅ Security headers

### 5. Logging & Monitoring
- ✅ Log all security events
- ✅ Detect suspicious activity
- ✅ Automatic alerts
- ✅ Audit trail

---

## 🚨 Vulnerability Protection

### SQL Injection
```python
# Detected patterns:
- UNION SELECT
- DROP TABLE
- INSERT INTO
- DELETE FROM
- OR 1=1
- AND 1=1
```

### XSS (Cross-Site Scripting)
```python
# Detected patterns:
- <script> tags
- javascript: protocol
- Event handlers (onclick, onerror, etc.)
- <iframe>, <object>, <embed> tags
```

### CSRF (Cross-Site Request Forgery)
```python
# Protection:
- CSRF tokens
- Token verification
- Same-origin policy
```

### Brute Force
```python
# Protection:
- Account lockout after 5 failed attempts
- Lockout duration: 30 minutes
- Rate limiting
```

### Path Traversal
```python
# Protection:
- Filename sanitization
- Remove ../ patterns
- Whitelist file extensions
```

---

## 📊 Security Metrics

### Authentication
- **Password Strength**: 8+ chars, mixed case, digits, special chars
- **Account Lockout**: 5 failed attempts → 30 min lockout
- **Session Timeout**: 24 hours
- **Token Expiration**: 24 hours

### Rate Limiting
- **Per Minute**: 60 requests
- **Per Hour**: 1000 requests
- **Per Day**: 10000 requests

### Encryption
- **Algorithm**: AES-256 (Fernet)
- **Key Size**: 256 bits
- **Password Hashing**: bcrypt (cost factor 12)

---

## 🧪 Testing

### Run Security Tests

```bash
# Test authentication
python -m security.auth

# Test encryption
python -m security.encryption

# Test rate limiter
python -m security.rate_limiter

# Test security logger
python -m security.security_logger

# Test middleware
python -m security.middleware
```

### Test Results
- ✅ Authentication: PASSED
- ✅ Encryption: PASSED
- ✅ Rate Limiter: PASSED
- ✅ Security Logger: PASSED
- ✅ Middleware: PASSED

---

## 🔐 Production Deployment

### 1. Environment Setup
```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false

# Use strong secrets
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 2. Database Security
```bash
# Use authenticated MongoDB
export MONGODB_URI="mongodb://username:password@host:27017/database?authSource=admin"

# Enable SSL/TLS
export MONGODB_URI="mongodb://username:password@host:27017/database?ssl=true"
```

### 3. HTTPS
```bash
# Use HTTPS in production
# Configure reverse proxy (nginx, Apache)
# Use Let's Encrypt for SSL certificates
```

### 4. Secrets Management
```bash
# Use secrets manager in production
# AWS Secrets Manager
# Azure Key Vault
# Google Secret Manager
# HashiCorp Vault
```

### 5. Monitoring
```bash
# Enable security logging
export LOG_LEVEL=INFO

# Set up alerts
# Email/SMS/Slack notifications
# Sentry for error tracking
```

---

## 📝 Security Checklist

### Before Deployment
- [ ] Change all default secrets
- [ ] Use strong passwords
- [ ] Enable HTTPS
- [ ] Configure firewall
- [ ] Set up monitoring
- [ ] Enable logging
- [ ] Test authentication
- [ ] Test rate limiting
- [ ] Test encryption
- [ ] Review security headers
- [ ] Scan for vulnerabilities
- [ ] Update dependencies

### Regular Maintenance
- [ ] Rotate secrets (monthly)
- [ ] Review logs (daily)
- [ ] Update dependencies (weekly)
- [ ] Security audit (quarterly)
- [ ] Penetration testing (annually)

---

## 🆘 Incident Response

### If Security Breach Detected

1. **Immediate Actions**
   - Disable affected accounts
   - Invalidate all sessions
   - Change all secrets
   - Enable maintenance mode

2. **Investigation**
   - Review security logs
   - Identify attack vector
   - Assess damage
   - Document findings

3. **Recovery**
   - Patch vulnerabilities
   - Restore from backup
   - Notify affected users
   - Update security measures

4. **Prevention**
   - Implement additional controls
   - Update security policies
   - Train team members
   - Monitor for similar attacks

---

## 📚 References

### Standards
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework
- **CWE Top 25**: https://cwe.mitre.org/top25/

### Libraries
- **bcrypt**: https://github.com/pyca/bcrypt
- **PyJWT**: https://pyjwt.readthedocs.io/
- **cryptography**: https://cryptography.io/

---

## ✅ Completion Checklist

- [x] Implement authentication (JWT, sessions, RBAC)
- [x] Implement encryption (AES-256, Fernet)
- [x] Implement rate limiting
- [x] Implement security logging
- [x] Implement security middleware
- [x] Add input validation
- [x] Add input sanitization
- [x] Add CSRF protection
- [x] Add security headers
- [x] Create .env.example
- [x] Test all modules (5/5 PASSED)
- [x] Create documentation
- [x] Production-ready code

---

**Status**: ✅ Production-ready  
**Date**: 2026-05-09  
**Version**: 1.0.0
