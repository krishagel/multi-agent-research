# Security Policy

## Overview

This document outlines the security measures implemented in the Multi-Agent Research System to protect sensitive data and ensure safe operation.

## Security Features

### 1. Credential Management
- **Environment Variables**: All sensitive credentials (API keys, AWS secrets) are stored in `.env` files
- **No Hardcoded Secrets**: Source code contains no hardcoded credentials
- **AWS Credential Chain**: Supports IAM roles, environment variables, and config files
- **Secure Configuration**: Uses `pydantic-settings` for type-safe configuration

### 2. Input Validation
- **Path Traversal Protection**: All file paths are validated to prevent directory traversal attacks
- **Input Sanitization**: User queries are sanitized to prevent injection attacks
- **Filename Sanitization**: Generated filenames are cleaned of dangerous characters
- **URL Validation**: External URLs are validated before use

### 3. API Security
- **Rate Limiting**: Prevents API abuse with configurable rate limits
- **Error Handling**: Sensitive error details are not exposed to users
- **Debug Mode Protection**: API keys are fully masked even in debug output

### 4. Data Protection
- **Database Parameterization**: All SQL queries use parameterized statements
- **Session IDs**: Cryptographically secure random session IDs
- **Log Redaction**: Sensitive data is redacted from logs
- **Thread Safety**: Concurrent operations are properly synchronized

### 5. File System Security
- **Path Validation**: All file operations validate paths against base directories
- **Extension Filtering**: Only allowed file extensions can be read/written
- **Directory Isolation**: Operations restricted to application directories

## Security Best Practices

### For Developers

1. **Never commit `.env` files** - Use `.env.example` as a template
2. **Validate all user input** - Use the `security.sanitize_user_input()` function
3. **Use path validation** - Call `security.validate_path()` for all file operations
4. **Handle errors properly** - Use specific exception types from `src.exceptions`
5. **Review dependencies** - Keep all packages up to date

### For Users

1. **Protect your credentials**:
   - Store API keys securely
   - Use IAM roles when possible for AWS
   - Rotate credentials regularly

2. **Monitor usage**:
   - Check the Usage Statistics tab regularly
   - Set appropriate budget alerts
   - Review API call logs

3. **Secure deployment**:
   - Run on trusted networks only
   - Use HTTPS if exposing the web interface
   - Implement additional authentication if needed

## Vulnerability Reporting

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. Email security concerns to the maintainers
3. Include detailed steps to reproduce
4. Allow time for a fix before public disclosure

## Security Checklist

Before deploying to production:

- [ ] All API keys are in environment variables
- [ ] `.env` file has restricted permissions (chmod 600)
- [ ] AWS IAM roles are configured with minimal permissions
- [ ] Rate limiting is configured appropriately
- [ ] Debug mode is disabled
- [ ] All dependencies are up to date
- [ ] Network access is properly restricted
- [ ] Logs are stored securely

## Dependencies

Key security-related dependencies:
- `boto3`: AWS SDK with built-in security features
- `pydantic`: Type validation and settings management
- `python-dotenv`: Secure environment variable loading
- `sqlite3`: Built-in parameterized queries

## Updates

This security policy was last updated: 2025-06-22

Regular security reviews are recommended every 3 months.