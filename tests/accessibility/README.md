# Accessibility Testing Suite

This directory contains automated accessibility tests for the Model Registry frontend, ensuring WCAG 2.1 Level AA compliance.

## Overview

The accessibility test suite uses **axe-selenium-python** to automatically detect and report accessibility issues across all pages of the application.

## Test Coverage

### 10 Automated Tests

1. **test_home_page_accessibility** - Runs axe-core against the home/search page
2. **test_ingest_page_accessibility** - Runs axe-core against the ingest page
3. **test_keyboard_navigation** - Verifies keyboard-only navigation works
4. **test_aria_landmarks** - Checks for proper landmark regions (nav, main, footer)
5. **test_form_labels** - Ensures all form inputs have accessible labels
6. **test_heading_hierarchy** - Validates heading structure (no skipped levels)
7. **test_color_contrast** - Checks color contrast ratios
8. **test_skip_link_functionality** - Verifies skip navigation link works
9. **test_button_accessibility** - Ensures buttons have accessible names
10. **test_live_regions** - Checks ARIA live regions for dynamic content

## Running Tests

### Prerequisites

```bash
pip install axe-selenium-python selenium webdriver-manager
```

### Local Execution

**With services running:**

```bash
# Start backend and frontend first
./run_api_new.sh  # Terminal 1
cd front-end/model-registry-frontend && npm run dev  # Terminal 2

# Run accessibility tests (Terminal 3)
PYTHONPATH=. python -m pytest tests/accessibility/ -v
```

**With visible browser (debugging):**

```bash
HEADLESS=false PYTHONPATH=. python -m pytest tests/accessibility/test_accessibility.py -v
```

**Single test:**

```bash
PYTHONPATH=. python -m pytest tests/accessibility/test_accessibility.py::AccessibilityTests::test_home_page_accessibility -v
```

### Docker Execution

```bash
# Start Docker stack
docker-compose up -d

# Run tests
FRONTEND_URL="http://localhost:5173" \
HEADLESS=true \
PYTHONPATH=. python -m pytest tests/accessibility/ -v

# Cleanup
docker-compose down
```

## CI/CD Integration

### GitHub Actions

The accessibility tests are integrated into the CI/CD pipeline. They run automatically on:

- Pull requests affecting frontend code
- Manual workflow dispatch

See `.github/workflows/gui-tests.yml` for the full configuration.

## Test Results

### Passing Criteria

- ✅ **Zero critical violations** - No WCAG Level A failures
- ✅ **Zero serious violations** - No WCAG Level AA failures
- ⚠️  **Minor/moderate violations** - Warnings only (manual review required)

### Interpreting Results

**Impact Levels:**

- **Critical** - Must fix immediately (blocks accessibility)
- **Serious** - Should fix (significant accessibility barrier)
- **Moderate** - Should fix (some users affected)
- **Minor** - Nice to fix (best practice)

**Example Output:**

```
✓ Found 3 navigation landmark(s)
✓ Found 1 main landmark(s)
✓ Found 1 footer landmark(s)
✓ All 8 form inputs have accessible labels
✓ Heading hierarchy is correct (5 headings)
✓ All 12 buttons have accessible names

test_home_page_accessibility PASSED
test_ingest_page_accessibility PASSED
test_keyboard_navigation PASSED
test_aria_landmarks PASSED
test_form_labels PASSED
test_heading_hierarchy PASSED
test_color_contrast PASSED
test_skip_link_functionality PASSED
test_button_accessibility PASSED
test_live_regions PASSED

==================== 10 passed in 15.42s ====================
```

## WCAG 2.1 Compliance

These tests cover the following WCAG 2.1 Level AA success criteria:

### Level A (Required)

- **1.1.1** Non-text Content
- **1.3.1** Info and Relationships
- **2.1.1** Keyboard
- **2.4.1** Bypass Blocks
- **2.4.4** Link Purpose (In Context)
- **3.1.1** Language of Page
- **3.3.1** Error Identification
- **3.3.2** Labels or Instructions
- **4.1.1** Parsing
- **4.1.2** Name, Role, Value

### Level AA (Enhanced)

- **1.4.3** Contrast (Minimum)
- **2.4.7** Focus Visible
- **3.2.4** Consistent Identification
- **4.1.3** Status Messages

## Manual Testing

While automated tests catch ~80% of accessibility issues, some require manual verification:

### Screen Reader Testing

Test with popular screen readers:

- **Windows:** NVDA (free) or JAWS
- **macOS:** VoiceOver (built-in)
- **Linux:** Orca

**Steps:**

1. Enable screen reader
2. Navigate through the application using only keyboard
3. Verify all content is announced properly
4. Check form labels, buttons, and dynamic content

### Keyboard-Only Navigation

1. Unplug your mouse
2. Navigate using Tab, Shift+Tab, Enter, Space, Arrow keys
3. Verify all functionality is accessible
4. Check focus indicators are visible

### Color Contrast

Use browser extensions:

- **WAVE** - Web Accessibility Evaluation Tool
- **axe DevTools** - Browser extension by Deque
- **Lighthouse** - Built into Chrome DevTools

### Zoom Testing

1. Zoom to 200% in browser
2. Verify content is readable
3. Check no content is cut off
4. Ensure functionality still works

## Fixing Violations

### Common Issues and Fixes

**1. Missing form labels:**

```tsx
// Bad
<input type="text" placeholder="Search" />

// Good
<label htmlFor="search">Search:</label>
<input id="search" type="text" placeholder="Search" />
```

**2. Poor color contrast:**

```css
/* Bad - contrast ratio < 4.5:1 */
color: #999;
background: #fff;

/* Good - contrast ratio ≥ 4.5:1 */
color: #666;
background: #fff;
```

**3. Missing ARIA live regions:**

```tsx
// Bad
{loading && <div>Loading...</div>}

// Good
{loading && (
  <div role="status" aria-live="polite">
    Loading...
  </div>
)}
```

**4. Improper heading hierarchy:**

```html
<!-- Bad - skips from h1 to h3 -->
<h1>Title</h1>
<h3>Subtitle</h3>

<!-- Good - proper hierarchy -->
<h1>Title</h1>
<h2>Subtitle</h2>
```

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools Browser Extension](https://www.deque.com/axe/devtools/)

## Accessibility Audit Report

For detailed findings and remediation steps, see:
- `docs/ACCESSIBILITY_AUDIT.md` - Full accessibility audit report
- `docs/ACCESSIBILITY.md` - WCAG compliance documentation (generated after fixes)

## Support

For questions or issues with accessibility testing:
1. Review the audit report in `docs/ACCESSIBILITY_AUDIT.md`
2. Check existing GitHub issues
3. Create a new issue with test output and screenshots
