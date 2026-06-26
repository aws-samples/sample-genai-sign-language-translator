# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisory** (preferred): [Open a Security Advisory](../../security/advisories/new)
2. **Email**: Send a report to [aws-security@amazon.com](mailto:aws-security@amazon.com)

Please include the following information in your report:

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact of the vulnerability
- Any suggested fix or mitigation (if available)

## Response Process

After you submit a report:

1. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 72 hours.
2. **Assessment**: The security team will investigate and validate the reported vulnerability.
3. **Resolution**: We will work on a fix and coordinate the release timeline.
4. **Disclosure**: Once a fix is available, we will publish a security advisory with details about the vulnerability and the fix.

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Security Best Practices for Users

When deploying this solution, we recommend the following security practices:

- Keep all dependencies up to date
- Use IAM roles with least-privilege permissions
- Enable encryption at rest and in transit for all AWS services
- Regularly rotate credentials and access keys
- Enable AWS CloudTrail for auditing API calls
- Review and apply security patches promptly
- Follow the [AWS Well-Architected Framework Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

## Disclosure Policy

- We follow a coordinated disclosure process.
- Security issues will be disclosed publicly only after a fix is available and affected users have had reasonable time to update.
- We will credit reporters who follow responsible disclosure practices, unless they prefer to remain anonymous.

## Security Updates

Security updates will be published as:
- GitHub Security Advisories
- Patch releases with clear changelog entries

## Contact

For any security-related questions that do not involve reporting a vulnerability, please open a regular issue or contact the maintainers.
