# Color Contrast Verification Guide

**Standard:** WCAG 2.1 Level AA - Success Criterion 1.4.3
**Required Ratios:**
- Normal text: 4.5:1 minimum
- Large text (18pt+ or 14pt+ bold): 3:1 minimum
- UI components: 3:1 minimum

---

## Current Color Palette

The Model Registry frontend uses CSS custom properties (variables) for consistent theming. These need to be verified for WCAG compliance.

### Verification Needed

The following CSS variables are defined in `front-end/model-registry-frontend/src/index.css`:

```css
:root {
  --bg-primary: /* Background color */
  --bg-secondary: /* Secondary background */
  --bg-tertiary: /* Tertiary background */
  --text-primary: /* Primary text color */
  --text-secondary: /* Secondary text color */
  --accent-primary: /* Primary accent (links, buttons) */
  --border-color: /* Border color */
  --error: /* Error messages */
  --success: /* Success messages */
  --warning: /* Warning messages */
  --info: /* Info messages */
}
```

**Action Required:** Document actual hex values for verification

---

## Verification Tools

### Online Tools (Recommended)

1. **WebAIM Contrast Checker**
   - URL: https://webaim.org/resources/contrastchecker/
   - Features: Simple, accurate, WCAG 2.1 compliance
   - Best for: Quick spot checks

2. **Colour Contrast Analyser (CCA)**
   - URL: https://www.tpgi.com/color-contrast-checker/
   - Features: Desktop app, simulates color blindness
   - Best for: Comprehensive audits

3. **Accessible Colors**
   - URL: https://accessible-colors.com/
   - Features: Suggests compliant alternatives
   - Best for: Finding replacement colors

4. **Contrast Ratio Calculator**
   - URL: https://contrast-ratio.com/
   - Features: Real-time calculations
   - Best for: Interactive testing

### Browser DevTools

**Chrome DevTools:**
1. Inspect element (F12)
2. Click color square in Styles panel
3. View "Contrast ratio" section
4. ✓ Green checkmark = passes WCAG AA
5. ✗ Red X = fails WCAG AA

**Firefox DevTools:**
1. Inspect element (F12)
2. Click "Accessibility" tab
3. View "Contrast" section
4. Shows ratio and WCAG compliance

---

## Areas Requiring Verification

### 1. Score Badges (CRITICAL)

**Component:** `ScoreBadge.tsx`
**CSS Classes:** `.score-high`, `.score-medium`, `.score-low`

**Current Implementation:**
```css
.score-badge.score-high {
  background: green; /* Replace with actual color */
  color: white;
}

.score-badge.score-medium {
  background: yellow; /* Replace with actual color */
  color: black;
}

.score-badge.score-low {
  background: red; /* Replace with actual color */
  color: white;
}
```

**Action:**
1. Extract actual hex colors from CSS
2. Test each combination:
   - High score: green bg + white text
   - Medium score: yellow bg + black text
   - Low score: red bg + white text
3. Document ratios
4. Replace with compliant colors if needed

**Suggested Compliant Colors:**
```css
.score-high {
  background: #0d7d2d; /* Dark green - 4.8:1 with white */
  color: #ffffff;
}

.score-medium {
  background: #856404; /* Dark yellow/ochre - 5.7:1 with white */
  color: #ffffff;
}

.score-low {
  background: #c9302c; /* Dark red - 4.5:1 with white */
  color: #ffffff;
}
```

### 2. Buttons (HIGH PRIORITY)

**Primary buttons:**
```css
button.btn-primary {
  background: var(--accent-primary);
  color: white;
}
```

**Secondary buttons:**
```css
button.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}
```

**Disabled buttons:**
```css
button:disabled {
  opacity: 0.6;  /* May reduce contrast below 4.5:1 */
}
```

**Action:**
- Verify primary button contrast
- Verify secondary button contrast
- Check disabled button text is still readable
- Consider using a different disabled color instead of opacity

### 3. Navigation Links

**Normal state:**
```css
.nav-links a {
  color: var(--text-secondary);
  background: transparent;
}
```

**Hover/focus state:**
```css
.nav-links a:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}
```

**Active state:**
```css
.nav-links a.active {
  color: var(--accent-primary);
  background: var(--bg-tertiary);
}
```

**Action:**
- Test link color against background
- Test hover state contrast
- Test active state contrast

### 4. Form Elements

**Input fields:**
```css
input, select, textarea {
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}
```

**Placeholder text:**
```css
input::placeholder {
  color: var(--text-secondary);
}
```

**Action:**
- Verify input text contrast
- Placeholder text often fails (may need darker color)
- Border color should have 3:1 ratio with background

### 5. Error/Success Messages

**Error:**
```css
.error-message {
  background: /* error background */;
  color: var(--error);
}
```

**Success:**
```css
.success-message {
  background: /* success background */;
  color: var(--success);
}
```

**Action:**
- Verify error message contrast
- Verify success message contrast
- Check icon colors if present

### 6. Footer Text

```css
.footer p {
  color: var(--text-secondary);
  background: var(--bg-secondary);
}
```

**Action:**
- Verify footer text is readable
- May need darker text color

---

## Verification Process

### Step 1: Extract Color Values

```bash
# From the CSS files, document:
cd front-end/model-registry-frontend/src
grep -r "color:" *.css components/*.tsx | grep -v "//\|/\*"
```

### Step 2: Test Each Combination

Create a table:

| Element | Foreground | Background | Ratio | Pass/Fail | Notes |
|---------|------------|------------|-------|-----------|-------|
| Body text | #333333 | #ffffff | ? | ? | Check with tool |
| Primary button | #ffffff | #0066cc | ? | ? | Check with tool |
| ... | ... | ... | ... | ... | ... |

### Step 3: Fix Failing Combinations

For each failing combination:

1. **Use contrast checker to find passing color**
2. **Update CSS variable or class**
3. **Document change in git commit**
4. **Re-test**

### Step 4: Document Results

Update this file with:
- Tested color combinations
- Contrast ratios achieved
- Any changes made
- Date of verification

---

## Common Issues & Fixes

### Issue 1: Yellow on White (Common Failure)

**Problem:** Yellow (#ffff00) on white (#ffffff) = 1.07:1 (FAIL)
**Fix:** Use dark yellow/ochre (#856404) = 5.7:1 (PASS)

### Issue 2: Light Gray Text (Common Failure)

**Problem:** Light gray (#999999) on white (#ffffff) = 2.85:1 (FAIL)
**Fix:** Darken to #767676 = 4.54:1 (PASS)

### Issue 3: Green Success Messages

**Problem:** Bright green (#00ff00) hard to read
**Fix:** Use dark green (#0d7d2d) or provide background

### Issue 4: Disabled Button Opacity

**Problem:** opacity: 0.6 reduces contrast
**Fix:** Use specific disabled colors instead:

```css
/* Instead of opacity */
button:disabled {
  background: #e0e0e0;
  color: #757575;
  opacity: 1;
}
```

### Issue 5: Focus Indicators

**Problem:** Thin or light-colored focus outlines
**Fix:** Use 3px solid outline with high contrast:

```css
*:focus-visible {
  outline: 3px solid #0066cc;
  outline-offset: 2px;
}
```

---

## Suggested Color Palette (WCAG AA Compliant)

### Light Theme

```css
:root {
  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #e9ecef;

  /* Text */
  --text-primary: #212529;      /* 16.1:1 with white */
  --text-secondary: #495057;    /* 8.6:1 with white */

  /* Accent */
  --accent-primary: #0066cc;    /* 4.6:1 with white */
  --accent-hover: #0052a3;      /* 6.3:1 with white */

  /* Borders */
  --border-color: #dee2e6;      /* 1.4:1 with white - UI component */

  /* Status colors */
  --error: #dc3545;             /* 4.5:1 with white */
  --success: #0d7d2d;           /* 4.8:1 with white */
  --warning: #856404;           /* 5.7:1 with white */
  --info: #0c5460;              /* 7.2:1 with white */

  /* Score badges */
  --score-high: #0d7d2d;        /* Green - 4.8:1 */
  --score-medium: #856404;      /* Ochre - 5.7:1 */
  --score-low: #c9302c;         /* Red - 4.5:1 */
}
```

### Dark Theme (Optional)

```css
:root[data-theme="dark"] {
  /* Backgrounds */
  --bg-primary: #1a1a1a;
  --bg-secondary: #2d2d2d;
  --bg-tertiary: #3d3d3d;

  /* Text */
  --text-primary: #f8f9fa;      /* 15.3:1 with #1a1a1a */
  --text-secondary: #adb5bd;    /* 8.2:1 with #1a1a1a */

  /* Accent */
  --accent-primary: #4da6ff;    /* 6.9:1 with #1a1a1a */
  --accent-hover: #66b3ff;      /* 8.6:1 with #1a1a1a */

  /* Rest adjusted for dark theme... */
}
```

---

## Testing Checklist

- [ ] Extract all color values from CSS
- [ ] Test body text contrast
- [ ] Test heading contrast
- [ ] Test link colors (all states)
- [ ] Test button colors (all variants)
- [ ] Test form element colors
- [ ] Test placeholder text
- [ ] Test border colors
- [ ] Test score badge colors
- [ ] Test error/success/warning messages
- [ ] Test footer text
- [ ] Test disabled element colors
- [ ] Test focus indicators
- [ ] Test with color blindness simulators
- [ ] Document all ratios
- [ ] Update CSS with fixes
- [ ] Re-run automated accessibility tests
- [ ] Update docs/ACCESSIBILITY.md with verification date

---

## Automated Testing

After manual verification, run automated tests:

```bash
# Accessibility tests include color contrast checks
PYTHONPATH=. python -m pytest tests/accessibility/test_accessibility.py::AccessibilityTests::test_color_contrast -v
```

---

## Color Blindness Considerations

Beyond contrast ratios, consider:

1. **Don't rely on color alone**
   - Add text labels to colored indicators
   - Use patterns or icons in addition to color

2. **Test with simulators**
   - Chrome DevTools: Rendering tab → Emulate vision deficiencies
   - Firefox: Inspect → Accessibility → Simulate

3. **Common types:**
   - Protanopia (red-blind)
   - Deuteranopia (green-blind)
   - Tritanopia (blue-blind)
   - Achromatopsia (complete color blindness)

---

## Sign-Off

Once verification is complete:

**Verified By:** _________________
**Date:** _________________
**Tool Used:** _________________
**All combinations pass WCAG AA:** Yes ☐ No ☐
**Changes required:** Yes ☐ No ☐

**If changes made, list:**
1. _________________
2. _________________
3. _________________

---

## References

- [WCAG 2.1 Success Criterion 1.4.3](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Accessible Color Palette Builder](https://toolness.github.io/accessible-color-matrix/)
- [Contrast Ratio](https://contrast-ratio.com/)

---

**Last Updated:** 2025-11-23
**Status:** Pending manual verification
**Next Review:** After CSS color implementation
