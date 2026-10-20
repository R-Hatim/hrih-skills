# Gallery field guide

Per-site notes for navigating each gallery efficiently. Read only the entries for the galleries you picked. Notes were verified in October 2026. Sites change, so if a slug 404s, fall back to the site's own navigation instead of guessing more slugs.

"Server-rendered" means names, links and image URLs come back from WebFetch/`get_page_text` without running JavaScript. "JS-rendered" means you need a real browser.

## Contents
- [land-book.com](#land-bookcom) — whole landing pages
- [supahero.io](#supaheroio) — hero sections
- [pricingpages.design](#pricingpagesdesign) — pricing pages
- [socialproofexamples.com](#socialproofexamplescom) — testimonials, logos, reviews
- [navbar.gallery](#navbargallery) — navigation
- [ogimage.gallery](#ogimagegallery) — OG / social share images
- [reallygoodemails.com](#reallygoodemailscom) — emails
- [deck.gallery](#deckgallery) — pitch decks
- [posts.design](#postsdesign) — social media posts
- [adfolio.design](#adfoliodesign) — B2B paid-social ads
- [Font substitutes](#font-substitutes)

---

## land-book.com

**What:** The biggest curated gallery of whole websites (more than 100,000 entries), updated daily. Beyond full pages it has section crops (hero, pricing, testimonials, and so on), and it can be filtered by industry, type, style, typography and platform. It's the best starting point for full-site direction.
**Canonical:** `https://land-book.com/`. **Cloudflare blocks WebFetch and curl (403), so use a real browser**, where it loads normally and the listings are server-rendered. Don't try to get around the block with spoofed user agents. `/llms.txt` is open and describes the site. Decline the cookie banner.

**URL patterns**
- Page types: `/design/{slug}`. Slugs: `landing-page`, `portfolio`, `ecommerce`, `blog`, `pricing-page`, `about-us-page`, `career-page`, `sign-up-page`, `case-study`, `blog-post`, `product-page`, `product-listing-page`, `other`.
- Section crops: `/sections/{slug}`. Slugs: `hero`, `value-proposition`, `features`, `how-it-works`, `testimonial`, `brands`, `stats`, `pricing`, `resources`, `faq`, `call-to-action`, `footer`, `about-us`, `case-study`.
- **Stackable filters** work on any list page, e.g. `/design/landing-page?industry[]=finance&type[]=saas` or `/sections/pricing?industry[]=ai`:
  - `industry[]`: advertising, ai, architecture, art, automotive, beauty, charity, design, ecommerce, education, event, fashion, finance, food-and-drinks, furniture-and-interiors, gaming, health-and-fitness, hr, kids, local-business, magazine, marketing, medical, music, nature, news, nft-crypto-web3, photography, pr, productivity, real-estate, sport, tech, travel, writing.
  - `type[]`: agency, beta, community, ebook, mobile-app, os-app, personal, physical-product, resource, saas, service, single-page, software.
  - `style[]`: 3d, animation, apple-style, background-image, background-video, big-footer, big-type, black-and-white, bright-colors, brutalism, cards, dark-colors, flat-design, fun, gradient, illustration, light-colors, parallax, pastel-colors, pattern, people, stripe-style, visible-borders.
  - `typography[]`: serif, sans-serif, display. `platform[]`: framer, webflow, shopify, wordpress, figma.
  - `color={hex}` (no `#`) filters by dominant color and stacks with `industry[]`/`type[]`. It's the best way to **widen the palette range** of a shortlist. Run two or three contrasting hues (e.g. `ff5a1f` orange, `1636d9` cobalt, `111111` near-black, `f5d90a` yellow) for the same industry. Results skew toward older entries, so use them for palette ideas, and check a candidate's live site or a newer entry before adopting its layout.
- Sort: the default, `sort=featured`, is labelled **"Most Recent"** on the site. Everything on land-book is curated, so recent is a good default. The others are `sort=recommended&from=year`, `sort=like&from=month` and `sort=view&from=month`. They're time-windowed, so with narrow filters they often return **nothing**; use them only on broad queries.
- Search: `/?search={term}`. Guests get limited search results, so prefer filters.
- Detail: `/websites/{id}-{slug}`. It has Preview (a tall full-page screenshot), Sections, Headlines and History tabs, an extracted **color palette**, tags with "Show similar" links, and a **Visit** button to the live site (`?ref=land-book.com`).

**Quirks:**
- **Copy detail links exactly from the listing.** Slugs are the full page title (`/websites/68919-kick-self-driving-bookkeeping`), so a guessed slug 404s.
- Detail-page preview images are in `srcset`, not `src`. In a browser, read `img.currentSrc`; from fetched HTML, parse `srcset`.
- **`style[]` tags mostly exist on older entries** (IDs below about 40,000, roughly 2021–22). Combining a style filter with an industry filter tends to surface dated work. Prefer `industry[]` + `type[]`, and judge style from the thumbnails. Entry IDs run in order, so a higher ID means newer.
- Grid and preview images lazy-load. Scroll or wait before screenshotting, or skip screenshots altogether: collect the grid's thumbnail URLs with JS (`[...document.querySelectorAll('img')].map(i => i.currentSrc).filter(s => s.includes('cdn.land-book.com/image'))`, paired with each card's link text) and feed them to `scripts/contact_sheet.py`. The thumbnail URLs are signed, so use them exactly as found.
- Decline the cookie banner ("Reject all").

**Paywall:** Pro unlocks full search results, downloads and older versions. Free list pages still show 20 or more entries each, which is plenty.

**Fast path (e.g. a fintech SaaS landing page):**
1. Open `/design/landing-page?industry[]=finance&type[]=saas`, collect the thumbnails into a contact sheet (or screenshot the grid), and shortlist.
2. Try a keyword search for the product category (e.g. `/?search=bookkeeping`) for closer matches.
3. Open 3–5 detail pages, note the palettes, then hit Visit for the top 2–3 and run the token extractor.
4. For a key section, also check `/sections/{section}?industry[]=finance`.

---

## supahero.io

**What:** About 570 curated **hero sections** (above-the-fold only). Now part of screensdesign.com.
**Canonical:** `https://supahero.io/`. Server-rendered, with all entries on the homepage, no pagination and no protection.

**No categories or filters.** The search box filters a client-side JSON index, and that index is the fastest way in: **`https://supahero.io/search-index.json`** is an array of `{name, slug, description, image}`. Fetch it and match descriptions against the brief's keywords (e.g. payment, bank, wallet or card for fintech; "AI agent" for an AI product). Use word boundaries (`/\b(git|cli|api)\b/i`), since a bare "git" also matches "digital".

**URL patterns**
- Detail: `/hero/{slug}`, e.g. `/hero/wise`. It has the name, tagline and a "Visit Website →" link to the live site.
- Image: `https://pub-26e6aa63ed7942ecb7e9dbc72f09f164.r2.dev/heroes/{slug}.webp`, an above-the-fold crop of about 2363×1908. Fine to view directly.

**Fast path:**
1. Fetch `search-index.json` and pick 8–12 entries whose descriptions match the brief.
2. Render their `image` URLs into one contact sheet (`scripts/contact_sheet.py`, about `--thumb 300 --max-height 240`) and compare them side by side.
3. Visit the live sites of the top 2–3 for motion and real type rendering.

**Tips:** The hero carries most of a landing page's first impression. Compare the headline length and size, where the CTA sits, the product visual (screenshot, illustration, 3D or none), and how much fits above the fold.

---

## pricingpages.design

**What:** About 135 curated SaaS pricing pages, each tagged by component.
**Canonical:** `https://pricingpages.design/`. The user may type it as "pircingpages"; that domain doesn't exist. Server-rendered (Webflow), 24 per page, about 6 pages, with no paywall or protection.

**Filters are client-side only (Finsweet). There are no filter URLs and no search.** Read all the listing pages and filter on each card's tags.
- Pagination is a **"Show me more"** link to `/?23ac8823_page=N`, for N up to about 6.
- The tags are **hidden elements**, so `get_page_text`/`innerText` miss them. Read cards with `textContent`.
- Fastest: from the first page, use the browser's JS tool to `fetch('/?23ac8823_page=N')` for each page, parse the HTML with `DOMParser`, and filter the cards' `textContent`. That's one navigation instead of six.
- WebFetch works too.

The tags:
- Components: Color Coded Tiers, Comparison Table, Contact Sales option, Custom Pricing, Enterprise pricing, FAQs, Feature Checkmarks, Feature Sections, Monthly/Annual switch, Table, Testimonials, Tier Cards, Tier feature table, Usage-Based Calculator, Usage-Based pricing.
- Patterns: Contact Sales, Enterprise pricing, Long & content heavy, Short & content light, One-off payment, Subscription option, Usage-Based Calculator.

**URL patterns**
- Detail: `/sites/{slug}`, e.g. `/sites/ramp`. Some slugs carry a suffix, like `/sites/chroma-tsc8m`. Detail pages add an **Industry** label (not filterable), a "View Website" link to the live pricing page, and "Other pricing pages".
- Screenshots: full-page desktop (1440 wide) and mobile (412 wide) WebP on `cdn.prod.website-files.com`. They're tall, so on the live page look at the top 1–2 screens for tier cards and use the comparison table below for detail.

**Fast path:**
1. Decide the pricing model first: tiers, usage-based, or contact-sales.
2. Collect the cards tagged with the matching components (e.g. "Usage-Based Calculator" plus "Monthly/Annual switch").
3. Open the live pricing pages of the top 2–3.

**Tips:** Judge pricing pages on how clear the choice is: is a recommended tier highlighted, can you compare tiers without scrolling, is it clear who each tier is for, and are objections answered (FAQ, guarantee)?

---

## socialproofexamples.com

**What:** One long, static page by Digital Psychology with about 190 cropped examples in 39 social-proof categories. Each comes with a short caption explaining **why it works**, and that reasoning is as useful as the visuals.
**Canonical:** `https://socialproofexamples.com/`. Static (Astro), with no sub-pages, search or filters. The whole page is about 880KB of HTML.

**Navigation by anchor:** `/#{category}`. IDs include: `wall-of-impact`, `wall-of-love`, `testimonial-mashup`, `famous-logos`, `impact-metrics`, `authority-metrics`, `awards-and-certifications`, `reviews`, `written-testimonial`, `testimonial-carousel`, `impact-carousel`, `micro-case-study`, `written-case-study`, `customer-story-hub`, `social-proof-microcopy`, `menu-social-proof`, `media-mention`, `investor-backing`, `displaying-faces`, `before-and-after`, `user-generated-content`, `referral`, plus video types such as `on-site-video-testimonial`.

**Images:** Cropped screenshots (about 1280×794) at `/_astro/{category}-{brand}.{hash}.webp`, with alt text like "Brand example from {Brand}…". Carousel images lazy-load and look blurred until scrolled into view. Reading the `img` URLs and putting them in a contact sheet avoids that. There are **no links to live sites**, so search for the brand's site yourself if you want to see the pattern in context. Video examples link to YouTube.

**Fast path:**
1. Choose 2–3 proof types that suit the business: logos and metrics for B2B, reviews and user-generated content for consumer, faces and written testimonials for services.
2. Jump to those anchors and screenshot the examples.
3. Read the captions for the persuasion principle behind each one.

**Tips:** Proof placement matters as much as styling. Logos usually sit right under the hero, metrics near claims, testimonials next to pricing or the final CTA. Never invent fake testimonials or logos for the user's product; use clearly marked placeholders.

---

## navbar.gallery

**What:** About 500 curated website navigation designs: static bars, dropdowns, mega-menus, mobile menus. Mostly SaaS, AI, agency and DTC sites.
**Canonical:** `https://www.navbar.gallery/`. Server-rendered (Webflow). No login or paywall.

**URL patterns**
- By navbar type: `/type/{slug}`. Slugs: `static`, `dropdowns`, `mega-menu`, `side-bar`, `search-bar`, `announcement`, `full-screen`, `breadcrumbs`, `tabs`, `progress-bar`.
- By style or industry: `/style/{slug}`, with about 118 slugs. Useful ones: `saas`, `ai`, `technology`, `web-app`, `startup`, `fintech`, `finance`, `crypto`, `e-commerce`, `d2c-direct-to-consumer`, `agency`, `portfolio`, `editorial`, `dark`, `minimal`, `gradient`, `brutalist`, `animated`. `development` is mostly agencies, not dev tools. The full list is at `/browse`.
- Special collections: `/mobile-navigation`, `/framer-navbars`, `/webflow-navbars`.
- Detail: `/navbar/{brand}`, e.g. `/navbar/cloudflare`. The title states the type ("Cloudflare Mega Menu Navigation Design").
- Pagination uses Webflow query params such as `?9edfe7e5_page=2`. Follow the "Next" link rather than constructing them.
- There is no search.

**Media:** Static AVIF screenshots (about 1800px wide), often a closed and an open state, from `cdn.navbar.gallery`. A few are MP4 recordings. Every card links to the live site, which is where to check hover, open and mobile behavior. On listing pages the card's `<img>` sits **outside** its `<a>`, so pair images with names and links through their shared card container (walk up to the common parent), not by looking inside the link. Cards also contain Webflow icons and a 1×1 placeholder: keep only images whose URL contains `cdn.navbar.gallery`. The AVIFs render fine in contact sheets.

**Fast path (e.g. a dev-tools navbar):**
1. Open `/style/technology`, `/style/ai` and `/style/saas`. `/style/web-app` has only a handful of entries.
2. Cross-check against `/type/mega-menu` or `/type/static`, depending on how much the product needs to expose.
3. Open the live sites of the top 2–3 and test the menu interaction and mobile breakpoint.

---

## ogimage.gallery

**What:** About 850 hand-picked Open Graph / social share images (1200×630), some of them animated.
**Canonical:** `https://www.ogimage.gallery/`. Server-rendered (Webflow). No login or paywall.

**URL patterns**
- Categories: `/category/{slug}`. Slugs: `saas`, `app`, `finance`, `health`, `food`, `stores`, `portfolios`, `creative`, `arts-culture`, `resources`, `animated`, `dynamic`. Each shows up to about 100 items.
- Brand pages: `/sites`, then `/site/{brand}`.
- Search: `/search?query={term}`. It matches brand names well and style words poorly.
- Detail: `/og-images/{slug}`, e.g. `/og-images/linear`. Repeat brands get numbered slugs like `linear-2`. Each detail page has a "Visit website ↗" link plus "More by" and "You might also like" sections.

**Media:** Images are WebP on `cdn.prod.website-files.com` (resized variants `-p-500`, `-p-800`, `-p-1080`). Animated ones are GIF.

**Fast path (e.g. an OG image for a SaaS landing page):**
1. Open `/category/saas` and screenshot the grid at reduced scale.
2. Search for direct competitors with `/search?query={brand}`.
3. Check `/category/dynamic` if each page should get its own generated image (blog posts, docs).

**Tips:** Share images are judged at thumbnail size in a feed, so evaluate them small. Reuse the site's own tokens (font, accent, background) so the card matches the landing page.

---

## reallygoodemails.com

**What:** More than 19,000 real marketing and lifecycle emails. Owned by Beefree.
**Canonical:** `https://reallygoodemails.com/`. Server-rendered (Next.js), with 50 cards per listing. More results load from a client-side "load more" button, and `?page=2` is ignored. Browsing and the HTML source are free; only saving and commenting need an account.

**URL patterns**
- Categories: `/categories/{slug}`. One pattern covers both email type and industry; `/industries/`, `/tags/` and `/companies/` return 404.
  - Type: `welcome`, `onboarding`, `activation-sign-up`, `trial-free-trial`, `abandoned-cart`, `newsletter`, `product-launch`, `product-update-new-feature`, `promotion`, `webinar`, `retention-reactivation`, `winback`, `receipt-payment`, `password-reset`, `black-friday`, `dark-mode`, `interactive`, `gif`.
  - Industry: `saas`, `b2b`, `app`, `technology-software`, `ecommerce`, `fashion`, `financial`, `beauty-and-personal-care`, `food`, `travel-and-leisure`, `non-profit-charity`, `education-school`, `health-and-wellness-medical`.
  - About 200 slugs in total (the full taxonomy is in each page's data under `childCategories`).
- Search: `/search?type=emails&query=saas%20welcome` for phrases, and `/search/emails/{Brand}` for brand names. A single category word in search comes back empty, so use `/categories/{slug}` instead. `/popular` lists 20 standouts.
- Detail: `/emails/{slug}`, with tabs `/mobile`, `/code` and `/text`.

**Getting the HTML source:** run `python scripts/rge_email_html.py {slug} out.html`. It also prints the desktop and mobile screenshot URLs. In a browser, the `/code` tab shows the same markup. Screenshots are public PNGs at `https://pro-really-good-emails.s3.eu-west-1.amazonaws.com/emails/{slug}.png`, with mobile versions under `/emails/mobile/{slug}.png`.

**Links to brand:** none to the brand's own site. The brand name links to `/search/emails/{Brand}`, which shows all of that brand's emails. Listing and search cards show only the subject line; the brand is usually the first word or words of the slug (`cleo-bank-connection-onboarding` → Cleo).

**Missing images:** Older emails often have no mobile screenshot (the `/emails/mobile/{slug}.png` URL fails). Use the desktop PNG, or render the HTML yourself at phone width (`screenshot.py ref.html --widths 390`).

**Fast path:**
1. **Find candidates by topic as well as category.** `/categories/welcome` is dominated by e-commerce discount emails.
   - Consumer app: search the product's topic (`?query=habit`, `?query=fitness%20app`, `?query=app%20welcome`) and check `/categories/onboarding`.
   - B2B or SaaS: `/categories/saas` or `/categories/b2b` combined with the email type.
2. Collect 10–15 slugs and turn their public screenshot PNGs (`.../emails/{slug}.png`) into contact sheets with `scripts/contact_sheet.py` (about `--cols 5 --thumb 270 --max-height 700`). That's far faster than opening each detail page.
3. Pull the HTML of the top 2–3 with `scripts/rge_email_html.py`. For email, **reading the source replaces the "visit the live site and run the token extractor" step**: take fonts, sizes, colors, widths, breakpoints and dark-mode handling from the markup.

**Tips:** Email HTML is a different craft from web HTML:
- Tables, inline styles, a 600px max width, no flexbox or grid, and bulletproof (VML) buttons. Reference HTML from strong emails shows the reliable patterns.
- **The `border-collapse` trap:** a global `table { border-collapse: collapse }` reset silently kills `border-radius` and `cellspacing` on every table. Set `border-collapse: separate` inline on any table that needs rounded corners or gaps.
- Check the mobile screenshot (most email is read on phones) and the dark render (`screenshot.py --dark`). Many clients force dark mode, and dark ink on dark cards disappears.
- Web fonts don't load in Gmail or Outlook, so make sure the fallback stack still looks right.

---

## deck.gallery

**What:** About 240 curated decks (about 14,000 slides): pitch decks, brand guidelines, reports, portfolios, sales and strategy decks.
**Canonical:** `https://www.deck.gallery/`. Server-rendered (Astro). Agent-friendly: there is `/llms.txt`, and a **free JSON catalog of every deck** at `https://www.deck.gallery/api/catalog/decks.json` with slug, title, description, url, categories, slide_count and cover.

**URL patterns**
- Categories: `/category/{slug}/`. Slugs: `pitch` (about 17), `guideline` (about 71), `report` (about 111), `portfolio`, `marketing`, `sales`, `talks`, `strategy`, `proposal`, `other`.
- Industry filter: `/?f_industry={slug}`, e.g. `saas`, `fintech`, `crypto`, `ai`, `agency`, `climate`. The JSON has no industry field; the homepage tiles carry it as `data-industry`.
- Detail: `/{slug}/`, e.g. `/arkive-pitch-deck-2022/`. Single slides are at `/{slug}/slide/{n}-{text}/`.
- Slides by role: `/slides/?f_deckcats=pitch`, filterable by cover, problem, solution, traction, market-size, team and the-ask. Mostly Pro.

**Paywall:** Only the **first 6 slides** of each deck are free; the rest, and the filterable slide library, need Pro. Work with the free slides; the cover, problem, solution and opening slides set the visual system anyway.

**Links to brand:** Detail pages link to the brand's site (`?ref=deck.gallery`).

**Images:** Signed URLs on `images.deck.gallery`; an unsigned request returns 403. View them in the browser, or copy the full signed URL from the page.

**Fast path (e.g. a seed-round pitch deck):**
1. Fetch `decks.json` and filter for `pitch`.
2. Open the 3–5 most relevant decks and screenshot their 6 free slides.
3. For a more polished visual system, also browse `guideline` and `report` decks from well-designed brands.

---

## posts.design

**What:** About 2,000 hand-picked social media graphics, with sections for OG images, X profile headers, carousels and a top-by-views ranking. **Nearly all from X/Twitter.** The visuals still transfer well to LinkedIn and Instagram, but adjust the aspect ratio: 1:1 or 4:5 for Instagram, 1.91:1 or 1:1 for LinkedIn.
**Canonical:** `https://posts.design/`. HTML pages server-render only about 12 posts, so **use the agent endpoints** listed in `/llms.txt`:
- `/index.md`: about 48 recent posts as Markdown.
- `/{slug}.md`: one post with its X status link, brand, categories, subjects, views and image URL.
- `/api/post-search?q={term}&sort=relevance|recent`: JSON search.
- `/api/gallery/v2?path=/categories/{slug}`: JSON list. It also works with `/subjects/{slug}`, `/top` and `/carousels`.

**Limits:** Without an account you get the first page only (24 search results, or 30–60 gallery items); paging returns 403 "Sign in to continue". That's plenty for inspiration, so don't sign up.

**URL patterns**
- Categories: `/categories/{slug}`. Slugs: `announcement` (launches), `feature-update`, `teaser`, `event`, `partner`, `milestone`, `custom-raise` (funding), `custom-integration`, `content`, `rebrand`, `hiring`, `custom-data` (charts), `custom-poster`, `custom-deal`, `custom-contest`, `custom-reward`, `custom-award`, `ad`, `meme`.
- Subjects: `/subjects/{slug}`, e.g. `ai`, `crypto`, `finance`, `developer-tools`, `design`, `productivity`, `payments`, `hardware`.
- Brands: `/brands/{brand}`, e.g. `/brands/linear`. Sections: `/opengraph`, `/headers`, `/carousels`, `/top`.

**Media:** `https://posts.design/images/posts/{id}.webp`, with videos at `/media/posts/{id}-detail.mp4`. Every post links to the original `x.com/.../status/...`.

**Fast path (e.g. launch-announcement posts):**
1. Fetch `/api/post-search?q=launch` and `/api/gallery/v2?path=/categories/announcement`.
2. Shortlist 5–10 and open their `.webp` images or `{slug}.md` pages.
3. For a funding announcement, use `custom-raise`; for a metrics post, use `custom-data`.

---

## adfolio.design

**What:** Hand-picked B2B SaaS paid-social ads (LinkedIn and Meta), static and motion, with written breakdowns on some. Curated by Diligent Studios.
**Canonical:** `https://www.adfolio.design/`. **JS-rendered and behind a Vercel bot checkpoint.** curl and WebFetch get HTTP 429, so use a real browser, where it loads normally. There is a cookie banner; decline it.

**Sections (top nav):** `/` (static ads), `/motion` (GIFs), `/videos`, `/landing-pages` (the pages the ads point to).

**Filters (client-side; the URL does not change, so click the chips):**
- **Industry:** Admin, Analytics, Business Services, Collaboration & Design, Content Creation, Development & Hosting, Finance, Food & Health, HR, Hardware, Legal & Compliance, Logistics & Transportation, Marketing & Automation, Research, Sales & Support, Scheduling, Security, Translation, Travel, Workflow & Project Management.
- **Platform:** LinkedIn, Meta.
- **Offer:** Demo, Free Trial, Sign Up, Learn More, Resource, Calculator.
- **Angle:** Pain Point First, Benefit First, Feature First, Capability First, Before/After, Comparison, Case Study, Testimonial, Question, Teaser, Meme.

**Detail:** `/breakdowns/{id}` (opaque id). It shows the ad as it appears in the feed: brand, primary text, creative, headline and CTA. Many have an "Ad breakdown" explaining why it works, plus "Ads from this brand". Grid cards have no text, so judge them from screenshots.

**Fast path (e.g. LinkedIn ads for a fintech SaaS):**
1. In a browser, click Industry → Finance, then Platform → LinkedIn.
2. Screenshot the grid and open 3–5 breakdowns.
3. Try the Angle filter to pick a messaging angle deliberately (e.g. Pain Point First versus Testimonial).

**Tips:** Ads are copy and creative together. Borrow the angle and structure (hook → proof → CTA) as well as the visual style. For consumer, DTC or non-B2B ads, rely more on posts.design.

---

## Font substitutes

Reference sites often use licensed fonts. These free alternatives (Google Fonts or Fontsource) are close in feel. Always say in the direction which substitute you used.

| Licensed font (seen on) | Free substitutes |
|---|---|
| Söhne (Stripe, OpenAI) | Inter, Geist, Hanken Grotesk |
| Circular (Spotify, Airbnb's old site) | DM Sans, Plus Jakarta Sans, Figtree |
| Graphik, Neue Haas Grotesk, Helvetica Now | Inter, Inter Tight, Instrument Sans |
| GT Walsheim, Gilroy | Outfit, Manrope, Urbanist |
| GT America, Suisse Int'l | Geist, Inter, Public Sans |
| Aeonik, Satoshi-style geometric grotesks | General Sans (Fontshare), Satoshi (Fontshare), Manrope |
| Berkeley Mono, SF Mono, Söhne Mono | JetBrains Mono, Geist Mono, IBM Plex Mono |
| Tiempos, GT Sectra, Lyon | Newsreader, Source Serif 4, Fraunces |
| Canela, Editorial New, PP Editorial | Instrument Serif, Playfair Display, DM Serif Display |
| Founders Grotesk, Druk (condensed display) | Anton, Bebas Neue, Oswald |
| Boathouse Extended, GT America Extended, Druk Wide (extended/wide grotesks) | Archivo Expanded (Archivo's width axis), Unbounded, Anybody |
