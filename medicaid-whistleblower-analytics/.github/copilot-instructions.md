# Copilot Instructions for Medicaid Whistleblower Analytics

## Technology Stack
- **Backend**: Python 3.11+ with FastAPI
- **Frontend**: TypeScript/React
- **Database**: PostgreSQL 14+

## Coding Standards
- Follow **PEP 8** for all Python code
- Use **ESLint** and **Prettier** for JavaScript/TypeScript
- Include comprehensive error handling and logging in all modules
- Write unit tests for all core functions
- Use environment variables for all configuration — **never hard-code credentials or API keys**
- Document all functions with docstrings (Google style for Python, JSDoc for TypeScript)

## Data Privacy & Security
- This application handles sensitive Medicaid claims data
- All PII must be handled according to HIPAA guidelines
- Encrypt sensitive data at rest and in transit
- Implement role-based access control for whistleblower case data
- Log all data access for audit trails
- Never expose raw patient identifiers in API responses or UI

## Project Conventions
- Use `async/await` for all I/O-bound operations
- Prefer chunked processing for large datasets (10GB+)
- Include type hints in all Python function signatures
- Use SQLAlchemy ORM for database interactions
- API responses should follow consistent JSON envelope format
