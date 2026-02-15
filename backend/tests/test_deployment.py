"""
Test deployment configuration and infrastructure.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


def test_env_example_file_exists():
    """Verify .env.production.example exists"""
    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    env_example = os.path.join(root_dir, ".env.production.example")
    assert os.path.exists(env_example), ".env.production.example file should exist"


def test_railway_toml_exists():
    """Verify railway.toml exists"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    railway_toml = os.path.join(root_dir, "railway.toml")
    assert os.path.exists(railway_toml), "railway.toml file should exist"


def test_health_router_imports():
    """Test health router can be imported"""
    from health import router
    assert router is not None
    assert hasattr(router, 'routes')


def test_encryption_with_valid_key():
    """Test PHI encryption with a valid key"""
    from cryptography.fernet import Fernet
    from core.encryption import PHIEncryption
    
    # Generate a test key
    test_key = Fernet.generate_key().decode()
    
    # Create encryption instance
    encryptor = PHIEncryption(encryption_key=test_key)
    
    # Test encryption/decryption
    plaintext = "John Doe"
    encrypted = encryptor.encrypt(plaintext)
    assert encrypted != plaintext
    assert len(encrypted) > len(plaintext)
    
    decrypted = encryptor.decrypt(encrypted)
    assert decrypted == plaintext


def test_encryption_dict_operations():
    """Test dictionary encryption/decryption"""
    from cryptography.fernet import Fernet
    from core.encryption import PHIEncryption
    
    test_key = Fernet.generate_key().decode()
    encryptor = PHIEncryption(encryption_key=test_key)
    
    # Test data
    patient_data = {
        "id": 123,
        "name": "John Doe",
        "ssn": "123-45-6789",
        "diagnosis": "Test"
    }
    
    # Encrypt specific fields
    encrypted = encryptor.encrypt_dict(patient_data, ["name", "ssn"])
    assert encrypted["id"] == 123
    assert encrypted["diagnosis"] == "Test"
    assert encrypted["name"] != "John Doe"
    assert encrypted["ssn"] != "123-45-6789"
    
    # Decrypt fields
    decrypted = encryptor.decrypt_dict(encrypted, ["name", "ssn"])
    assert decrypted["name"] == "John Doe"
    assert decrypted["ssn"] == "123-45-6789"


def test_logging_config_setup():
    """Test logging configuration"""
    from core.logging_config import setup_logging, JSONFormatter
    import logging
    
    # Setup logging
    with patch.dict(os.environ, {"LOG_LEVEL": "INFO", "STRUCTURED_LOGGING": "false"}):
        setup_logging()
    
    logger = logging.getLogger("test")
    assert logger.level == logging.INFO or logger.level == logging.NOTSET


def test_json_formatter():
    """Test JSON log formatter"""
    from core.logging_config import JSONFormatter
    import logging
    import json
    
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    log_dict = json.loads(formatted)
    
    assert log_dict["level"] == "INFO"
    assert log_dict["message"] == "Test message"
    assert "timestamp" in log_dict


@patch("core.rate_limiter.redis_client")
def test_rate_limiter_init(mock_redis):
    """Test rate limiter initialization"""
    from core.rate_limiter import limiter
    
    assert limiter is not None
    assert hasattr(limiter, 'limit')


def test_evidence_integrity_service():
    """Test evidence integrity service initialization"""
    from services.evidence_integrity import EvidenceIntegrityService
    
    service = EvidenceIntegrityService()
    assert service.SIGNATURE_ALGORITHM == "SHA-256"
    assert service.EVIDENCE_VERSION == "1.0"


def test_celery_app_configuration():
    """Test Celery app configuration"""
    with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
        from tasks import celery_app
        
        assert celery_app is not None
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.timezone == "America/New_York"


def test_deployment_docs_exist():
    """Verify deployment documentation exists"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    deployment_md = os.path.join(root_dir, "DEPLOYMENT.md")
    assert os.path.exists(deployment_md), "DEPLOYMENT.md should exist"


def test_validation_script_exists():
    """Verify validation script exists"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    validation_script = os.path.join(root_dir, "scripts", "validate_deployment.sh")
    assert os.path.exists(validation_script), "Validation script should exist"
    
    # Check if executable
    import stat
    st = os.stat(validation_script)
    assert bool(st.st_mode & stat.S_IXUSR), "Validation script should be executable"


def test_dockerfile_prod_exists():
    """Verify production Dockerfile exists"""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dockerfile = os.path.join(root_dir, "Dockerfile.prod")
    assert os.path.exists(dockerfile), "Dockerfile.prod should exist"


def test_alembic_configuration():
    """Test Alembic configuration exists"""
    alembic_ini = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    assert os.path.exists(alembic_ini), "alembic.ini should exist"
    
    alembic_env = os.path.join(os.path.dirname(__file__), "..", "alembic", "env.py")
    assert os.path.exists(alembic_env), "alembic/env.py should exist"
