# GitHub Copilot Auto-Review Setup Guide

This document explains how to enable and configure GitHub Copilot Auto-Review for pull requests in the Model Registry project.

## Overview

The project now includes automated code review using AI-powered tools. The system provides:
- 🤖 Automated code review on every PR
- 🔒 Security vulnerability scanning
- ♿ Accessibility compliance checks
- 📋 Manual review checklists
- 🎯 Best practice recommendations

## Workflow File

Created: `.github/workflows/copilot-review.yml`

### Jobs

1. **copilot-review** - AI-powered code review
2. **manual-review-checklist** - Posts checklist for human reviewers
3. **security-scan** - Scans for vulnerabilities using Trivy and Bandit

## Setup Instructions

### Option 1: GitHub Copilot (Recommended)

**Prerequisites:**
- GitHub Copilot subscription (available for students, open source, and paid)
- Repository with Copilot enabled

**Steps:**
1. Go to repository Settings → Actions → General
2. Enable "Allow GitHub Actions to create and approve pull requests"
3. Add repository secret for `OPENAI_API_KEY` (if using CodeRabbit AI)
4. Push the workflow file to your repository

### Option 2: Alternative AI Code Reviewers

If GitHub Copilot is not available, you can use these alternatives:

#### CodeRabbit AI (Free for open source)
```yaml
- name: AI Code Review
  uses: coderabbitai/ai-pr-reviewer@latest
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

**Setup:**
1. Sign up at https://coderabbit.ai/
2. Connect your GitHub repository
3. Add `OPENAI_API_KEY` secret in repository settings

#### CodeGuru Reviewer (AWS)
```yaml
- name: Amazon CodeGuru Reviewer
  uses: aws-actions/codeguru-reviewer@v1.1
  with:
    build_path: ./src
```

**Setup:**
1. Enable AWS CodeGuru in your AWS account
2. Add AWS credentials as repository secrets
3. Configure IAM permissions

### Option 3: Manual Review Only

If AI review is not needed, the workflow will still provide:
- Manual review checklist
- Security scanning (Trivy, Bandit, Safety)
- Changed files summary

Simply comment out the `copilot-review` job in the workflow file.

## Configuration

### Review Focus Areas

The AI reviewer is configured to focus on:

```yaml
system_message: |
  You are an expert code reviewer for a Trustworthy Model Registry project.
  Focus on:
  - Security vulnerabilities (SQL injection, XSS, CSRF, authentication issues)
  - OWASP Top 10 compliance
  - Accessibility issues (WCAG 2.1 Level AA)
  - Performance concerns
  - Code quality and best practices
  - Type safety
  - Error handling
  - Test coverage
```

### File Filters

Reviews are triggered for these file types:
- `**/*.py` - Python files
- `**/*.ts` - TypeScript files
- `**/*.tsx` - React TypeScript files
- `**/*.js` - JavaScript files
- `**/*.jsx` - React JavaScript files

### Customization

Edit `.github/workflows/copilot-review.yml` to:

**Change review scope:**
```yaml
with:
  path_filters: |
    src/**/*.py
    front-end/**/*.tsx
```

**Adjust security scan severity:**
```yaml
with:
  severity: 'CRITICAL,HIGH,MEDIUM'  # Add MEDIUM
```

**Disable specific jobs:**
```yaml
jobs:
  copilot-review:
    if: false  # Disable this job
```

## Security Scanning Tools

### 1. Trivy (Container & Filesystem Scanner)
- **What it scans:** Dependencies, OS packages, misconfigurations
- **Severities:** CRITICAL, HIGH, MEDIUM, LOW
- **Output:** Uploaded to GitHub Security tab

### 2. Bandit (Python Security Linter)
- **What it scans:** Python code for security issues
- **Checks:** SQL injection, hardcoded passwords, insecure functions
- **Output:** JSON report + PR comment

### 3. Safety (Python Dependency Checker)
- **What it scans:** Python dependencies against CVE database
- **Output:** JSON report with known vulnerabilities

## Manual Review Checklist

Every PR automatically gets a checklist covering:

### Security
- No hardcoded secrets
- Input validation present
- SQL injection protection
- XSS protection
- Authentication/authorization checks
- OWASP Top 10 compliance

### Testing
- Unit tests added/updated
- Integration tests pass
- Code coverage maintained (>60%)
- GUI tests pass (if frontend)
- Accessibility tests pass (if UI)

### Accessibility (UI changes)
- ARIA labels present
- Keyboard navigation works
- Screen reader compatible
- Color contrast meets WCAG AA
- Focus indicators visible

### Code Quality
- Follows coding standards
- No code duplication
- Error handling implemented
- Logging added
- Documentation updated

### Performance
- No N+1 queries
- Efficient algorithms
- Large data sets handled
- No memory leaks

### Documentation
- README updated
- API documentation updated
- Comments added
- Changelog updated

## Usage

### Automatic Trigger

The workflow runs automatically when:
- A pull request is opened
- New commits are pushed to an open PR
- A closed PR is reopened

### Manual Trigger

To re-run the review:
1. Go to Actions tab
2. Select "Copilot Code Review"
3. Click "Run workflow"
4. Select the branch

### Reviewing Results

**AI Review Comments:**
- Posted as PR review comments
- Inline with specific code lines
- Includes severity and suggestions

**Security Findings:**
- Posted as PR comment
- Detailed results in Actions tab
- Critical issues highlighted

**Manual Checklist:**
- Posted as PR comment
- Check boxes to track progress
- Updated by reviewers

## Best Practices

### For PR Authors

1. **Run tests locally** before pushing
2. **Review AI suggestions** carefully - they're not always correct
3. **Complete the checklist** before requesting review
4. **Respond to security findings** promptly
5. **Keep PRs focused** - smaller PRs get better reviews

### For Reviewers

1. **Don't rely solely on AI** - manual review is still essential
2. **Verify security fixes** are properly implemented
3. **Check test coverage** for changed code
4. **Ensure accessibility** for UI changes
5. **Test functionality** when possible

### For Repository Admins

1. **Monitor workflow usage** - AI reviews use API credits
2. **Adjust sensitivity** if too many false positives
3. **Keep tools updated** - update action versions regularly
4. **Review security findings** in Security tab weekly
5. **Configure branch protection** to require reviews

## Troubleshooting

### Workflow Not Running

**Check:**
1. Workflow file is in `.github/workflows/` directory
2. YAML syntax is valid (use yamllint)
3. GitHub Actions are enabled in repository settings
4. Branch protection rules don't block the workflow

**Fix:**
```bash
# Validate YAML
yamllint .github/workflows/copilot-review.yml

# Check GitHub Actions status
gh workflow list
```

### AI Review Not Posting Comments

**Common issues:**
1. Missing `OPENAI_API_KEY` secret
2. Insufficient permissions in workflow
3. API rate limits reached
4. No changed files matching filters

**Fix:**
```yaml
permissions:
  contents: read
  pull-requests: write  # Required for comments
  issues: write         # Required for issue comments
```

### Security Scan Failures

**Common issues:**
1. Bandit/Safety not installed
2. Invalid file paths
3. Network issues downloading CVE database

**Fix:**
```bash
# Install tools locally to test
pip install bandit safety
bandit -r src/
safety check
```

### Rate Limiting

**Symptoms:**
- AI reviews fail with 429 errors
- Slow or incomplete reviews

**Solutions:**
1. Reduce review frequency (weekly instead of every PR)
2. Use caching for dependencies
3. Filter to only review important files
4. Consider upgrading API plan

## Cost Considerations

### GitHub Copilot
- **Individual:** $10/month
- **Business:** $19/user/month
- **Free:** For students, teachers, open source maintainers

### CodeRabbit AI
- **Open Source:** Free
- **Teams:** Starting at $12/user/month
- **Enterprise:** Custom pricing

### GitHub Actions Minutes
- **Free tier:** 2,000 minutes/month
- **Pro:** 3,000 minutes/month
- **Typical usage:** ~5-10 minutes per PR review

## Alternatives to AI Review

If AI review is not feasible, consider:

1. **Automated Linting:**
   - pylint, flake8, mypy (Python)
   - ESLint, TypeScript compiler (JavaScript/TypeScript)

2. **Static Analysis:**
   - SonarQube
   - CodeClimate
   - Scrutinizer

3. **Security Scanning Only:**
   - Keep Trivy and Bandit
   - Remove AI review job
   - Focus on vulnerability detection

4. **Manual Reviews:**
   - Use the checklist
   - Establish review guidelines
   - Train team on security best practices

## References

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides)
- [CodeRabbit AI](https://coderabbit.ai/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

## Support

For issues with the review workflow:
1. Check workflow logs in Actions tab
2. Review this documentation
3. Check GitHub Actions status page
4. Create an issue in the repository

---

**Last Updated:** 2025-11-23
**Maintained By:** Developer B - Frontend, Testing & Security Lead
