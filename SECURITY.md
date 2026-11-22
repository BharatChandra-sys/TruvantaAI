<!-- Copyright 2027 Bodapati Bharat Chandra. All rights reserved. -->
<!-- Licensed under the Apache License, Version 2.0 | SPDX-License-Identifier: Apache-2.0 -->

# Security Policy

## Supported Versions

We actively support the following versions of FactCheckAI:

| Version | Supported          |
| ------- | ------------------ |
| 2.6.x   | ✅ Active support |
| 2.5.x   | ✅ Security fixes  |
| 2.4.x   | ❌ End of life    |
| < 2.4   | ❌ End of life    |

## Reporting Security Vulnerabilities

We take security seriously. If you discover a security vulnerability, please follow these guidelines:

### 🔒 Responsible Disclosure

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please email us directly at: **contact@truvantaai.tech**

### 📧 What to Include

Please include the following information:

- **Vulnerability Type**: (e.g., XSS, SQL Injection, Authentication bypass)
- **Affected Component**: (Backend API, Chrome Extension, Database)
- **Steps to Reproduce**: Detailed reproduction steps
- **Impact Assessment**: Potential security impact
- **Suggested Fix**: If you have ideas for remediation
- **Contact Information**: So we can follow up with questions

### ⏱️ Response Timeline

We commit to the following response times:

| Severity | Initial Response | Status Update | Fix Timeline |
|----------|------------------|---------------|--------------|
| **Critical** | 24 hours | Every 48 hours | 7 days |
| **High** | 48 hours | Weekly | 14 days |
| **Medium** | 5 days | Bi-weekly | 30 days |
| **Low** | 10 days | Monthly | 90 days |

### 🛡️ Security Measures

#### Data Protection
- **Encryption**: All data in transit uses TLS 1.3+
- **Authentication**: JWT tokens with automatic rotation
- **Authorization**: Role-based access control (RBAC)
- **Data Anonymization**: Personal data is automatically anonymized

#### Infrastructure Security
- **Multi-Cloud**: Distributed across multiple cloud providers
- **Rate Limiting**: API endpoints protected against abuse
- **DDoS Protection**: Cloudflare enterprise protection
- **Monitoring**: 24/7 security monitoring with automated alerts

#### Code Security
- **Static Analysis**: Automated security scanning with Bandit
- **Dependency Scanning**: Continuous vulnerability monitoring
- **Secret Scanning**: No secrets in source code
- **Code Review**: All changes reviewed by security-trained developers

### 🔍 Security Testing

We perform regular security assessments:

#### Automated Testing
- **SAST**: Static Application Security Testing on every commit
- **DAST**: Dynamic testing against running applications
- **Dependency Scanning**: Third-party library vulnerability checks
- **Container Scanning**: Docker image security analysis

#### Manual Testing
- **Penetration Testing**: Quarterly external security audits
- **Code Review**: Security-focused code reviews
- **Red Team Exercises**: Internal attack simulations
- **Bug Bounty**: Community-driven vulnerability discovery

### 🏆 Security Bug Bounty

We run a responsible disclosure program with the following rewards:

| Severity | Reward Range | Examples |
|----------|--------------|----------|
| **Critical** | $1,000 - $5,000 | Remote code execution, full system compromise |
| **High** | $500 - $1,000 | Authentication bypass, privilege escalation |
| **Medium** | $100 - $500 | XSS, CSRF, information disclosure |
| **Low** | $50 - $100 | Minor security improvements |

#### Eligibility Requirements
- Vulnerability affects a supported version
- Previously unreported security issue
- Follows responsible disclosure guidelines
- No malicious testing or data extraction
- Testing limited to your own accounts

### 📋 Security Best Practices

#### For Users
- **Keep Updated**: Always use the latest version
- **Strong Passwords**: Use unique, complex passwords
- **Two-Factor Authentication**: Enable 2FA when available
- **Suspicious Activity**: Report unusual behavior immediately

#### For Developers
- **Environment Variables**: Never commit secrets to version control
- **Input Validation**: Sanitize and validate all user inputs
- **Least Privilege**: Use minimal necessary permissions
- **Security Headers**: Implement appropriate HTTP security headers

#### For Enterprises
- **API Keys**: Rotate API keys regularly
- **Network Security**: Use VPNs and network segmentation
- **Access Reviews**: Regularly audit user access and permissions
- **Incident Response**: Have a security incident response plan

### 🔐 Compliance & Certifications

We maintain compliance with industry standards:

#### Current Certifications
- **SOC 2 Type II** (in progress)
- **GDPR Compliance** (EU data protection)
- **CCPA Compliance** (California privacy rights)

#### Planned Certifications
- **ISO 27001** (Information security management)
- **HIPAA** (Healthcare data protection)
- **FedRAMP** (US government cloud security)

### 📊 Security Metrics

We track and publicly report security metrics:

#### Vulnerability Response
- **Mean Time to Detection (MTTD)**: < 4 hours
- **Mean Time to Response (MTTR)**: < 24 hours  
- **Mean Time to Resolution (MTTR)**: < 7 days (critical)

#### Security Posture
- **Security Score**: 95/100 (SecurityScorecard)
- **Vulnerability Density**: < 1 per 10K lines of code
- **Patch Coverage**: 100% of critical vulnerabilities

### 📞 Contact Information

#### Security Team
- **Email**: contact@truvantaai.tech
- **PGP Key**: [Download public key](https://factcheckai.com/pgp-key.asc)
- **Response Time**: 24 hours for critical issues

#### General Security Inquiries
- **Documentation**: https://docs.factcheckai.com/security
- **Status Page**: https://status.factcheckai.com
- **Security Blog**: https://blog.factcheckai.com/security

### 📜 Legal Notice

By participating in our security program, you agree to:

1. **Legal Authorization**: Only test on systems you own or have explicit permission to test
2. **No Harmful Actions**: Do not access, modify, or delete user data
3. **Confidentiality**: Keep vulnerability details confidential until publicly disclosed
4. **Good Faith**: Act in good faith to avoid privacy violations and service disruptions

We commit to:

1. **No Legal Action**: Not pursue legal action against security researchers who follow these guidelines
2. **Acknowledgment**: Public recognition for valid security reports (unless requested otherwise)
3. **Safe Harbor**: Protection under our coordinated disclosure policy

---

**Last Updated**: January 2027  
**Next Review**: April 2027