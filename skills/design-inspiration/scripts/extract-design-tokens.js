// Paste into a browser JavaScript tool (built-in browser `javascript_tool`,
// Chrome `javascript_tool`, or Playwright `browser_evaluate` wrapped as
// `() => { return <this expression> }`) while a LIVE reference site is open.
// Returns the site's real design tokens as JSON: loaded fonts, type scale,
// palette (as hex), radii, shadows, container width, buttons and CSS variables.
// Read-only: it inspects computed styles and changes nothing on the page.
// Comment lines can be dropped when pasting.
(() => {
  // Normalise any CSS color (rgb, oklch, lab, color(), named...) to hex via a 1x1 canvas.
  const ctx = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
  const hexCache = {};
  const hex = (c) => {
    if (!c || c === 'transparent' || c === 'rgba(0, 0, 0, 0)') return null;
    if (c in hexCache) return hexCache[c];
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = '#000';
    ctx.fillStyle = c; // ignored if unparseable, leaving black
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    const h = '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('') + (a < 255 ? a.toString(16).padStart(2, '0') : '');
    return (hexCache[c] = a === 0 ? null : h);
  };
  // Font family without fallbacks, quotes or bundler hash suffixes ("Inter-f2556f4e9bb2" -> "Inter").
  const fam = (f) => f.split(',')[0].replace(/["']/g, '').trim().replace(/[-_][0-9a-f]{8,}$/i, '');
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
  };
  const type = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return {
      sample: (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 70),
      family: fam(s.fontFamily),
      size: s.fontSize,
      weight: s.fontWeight,
      lineHeight: s.lineHeight,
      letterSpacing: s.letterSpacing,
      transform: s.textTransform !== 'none' ? s.textTransform : undefined,
      color: hex(s.color),
    };
  };
  const first = (sel) => [...document.querySelectorAll(sel)].find((e) => visible(e) && e.innerText.trim()) || null;
  const tally = (map, key) => { if (key) map[key] = (map[key] || 0) + 1; };
  const top = (map, n) => Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, n).map(([v, c]) => `${v} ×${c}`);

  const text = {}, bg = {}, border = {}, radii = {}, shadows = {}, sizes = {};
  [...document.querySelectorAll('body *')].slice(0, 4000).forEach((el) => {
    if (!visible(el)) return;
    const s = getComputedStyle(el);
    if (el.childNodes.length && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) {
      tally(text, hex(s.color));
      tally(sizes, s.fontSize);
    }
    tally(bg, hex(s.backgroundColor));
    if (s.borderTopWidth !== '0px' && s.borderTopStyle !== 'none') tally(border, hex(s.borderTopColor));
    if (s.borderRadius !== '0px') tally(radii, s.borderRadius);
    if (s.boxShadow !== 'none') tally(shadows, s.boxShadow);
  });

  // Filled buttons in the first ~900px, largest first. Excluded: skip-links,
  // off-screen helpers and full-width bars (announcement banners). Judge from
  // the labels which one is the primary CTA.
  const fold = Math.max(window.innerHeight, 900);
  const buttons = [...document.querySelectorAll('a, button')]
    .filter((e) => visible(e) && hex(getComputedStyle(e).backgroundColor))
    .filter((e) => !/skip to/i.test(e.innerText) && e.offsetHeight >= 28 && e.offsetWidth >= 60)
    .filter((e) => e.offsetWidth < window.innerWidth * 0.6)
    .filter((e) => { const r = e.getBoundingClientRect(); return r.top + scrollY >= 0 && r.left >= 0 && r.top + scrollY < fold; })
    .sort((a, b) => b.offsetWidth * b.offsetHeight - a.offsetWidth * a.offsetHeight)
    .slice(0, 3)
    .map((e) => {
      const s = getComputedStyle(e);
      return { label: e.innerText.trim().replace(/\s+/g, ' ').slice(0, 40), bg: hex(s.backgroundColor), color: hex(s.color),
        border: s.borderTopWidth !== '0px' ? `${s.borderTopWidth} ${hex(s.borderTopColor)}` : 'none',
        radius: s.borderRadius, padding: s.padding, font: `${s.fontWeight} ${s.fontSize} ${fam(s.fontFamily)}` };
    });

  // Widest centered content container ≈ the site's max content width.
  const container = [...document.querySelectorAll('main *, section *, header *, div')]
    .filter(visible)
    .map((e) => ({ e, s: getComputedStyle(e) }))
    .filter(({ s }) => s.maxWidth.endsWith('px') && parseFloat(s.maxWidth) >= 600 && s.marginLeft === s.marginRight)
    .map(({ s }) => s.maxWidth);

  // CSS custom properties on the root element (design-system tokens, if the site uses them).
  // Chromium enumerates custom properties in computed style; stylesheet scan is the fallback.
  // Design-relevant names (color, font, radius, spacing, shadow…) are kept first.
  const allVars = {};
  const addVar = (p, v) => {
    if (!p.startsWith('--') || !v || !v.trim()) return;
    v = v.trim().slice(0, 120);
    if (/^(oklch|oklab|lab|lch|hsla?|hwb|color)\(/i.test(v)) v += ` → ${hex(v)}`; // add hex for modern color syntaxes
    allVars[p] = v;
  };
  const rootStyle = getComputedStyle(document.documentElement);
  for (const p of rootStyle) addVar(p, rootStyle.getPropertyValue(p));
  if (!Object.keys(allVars).length) {
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules; } catch { continue; } // cross-origin sheets
      for (const r of rules) {
        if (r.selectorText && /(^|,\s*)(:root|html)\b/.test(r.selectorText)) {
          for (const p of r.style) addVar(p, r.style.getPropertyValue(p));
        }
      }
    }
  }
  const RELEVANT = /brand|primary|accent|color|bg|background|text|font|radius|space|spacing|shadow|gap|container/i;
  // Third-party widgets (cookie banners, consent tools, chat, carousels) often
  // declare dozens of root variables that would crowd out the brand's own.
  // UI-framework prefixes (--chakra-*, --mantine-*, --radix-*) are kept: they
  // hold the site's actual theme tokens.
  const NOISE = /^--(cc-|cky-|c15t-|ot-|onetrust|osano|didomi|klaro|iub|cookie|consent|intercom|hs-|drift|swiper|splide|glide|plyr|toastify|rsbs)|tw-|webkit|moz-|transition|animate|duration|z-index|ease/i;
  const cssVars = Object.fromEntries(Object.entries(allVars)
    .filter(([k]) => !NOISE.test(k))
    .sort(([a], [b]) => RELEVANT.test(b) - RELEVANT.test(a) || a.localeCompare(b))
    .slice(0, 60));

  const viewport = `${window.innerWidth}×${window.innerHeight}`;
  return {
    url: location.href,
    title: document.title,
    viewport,
    warning: window.innerWidth < 1200
      ? `Viewport is only ${viewport}: the site may be showing its tablet/mobile layout. Treat layout values with care, and get a true desktop view with scripts/screenshot.py <url> --height 900 --no-mobile.`
      : undefined,
    fontsLoaded: [...new Set([...document.fonts].filter((f) => f.status === 'loaded').map((f) => `${fam(f.family)} ${f.weight}`))].slice(0, 15),
    typography: {
      body: type(document.body),
      h1: type(first('h1')),
      h2: type(first('h2')),
      h3: type(first('h3')),
      paragraph: type(first('main p, section p, p')),
      navLink: type(first('nav a, header a')),
    },
    fontSizesInUse: top(sizes, 10),
    palette: { text: top(text, 6), backgrounds: top(bg, 8), borders: top(border, 4) },
    radii: top(radii, 5),
    shadows: top(shadows, 3),
    buttons,
    maxContentWidth: top(container.reduce((m, w) => (tally(m, w), m), {}), 3),
    cssVarCount: Object.keys(allVars).length,
    cssVars,
  };
})();
