# Sources

This file records, for each candidate source, whether automated collection and redistribution are permitted. No source may be collected from automatically until its "Automated collection allowed" field reads "yes" and the supporting terms of use and robots.txt rules are recorded here.

Allowed values for the two permission fields: yes, no, unclear. If permission is unclear, stop and decide with the project owner.

## Shwapno

- Date checked: 2026-11-04
- URL: https://www.shwapno.com
- Platform still operating: yes
- Terms of use summary (with link): https://www.shwapno.com/tac?lang=en. Section 11.5 prohibits using "any automated system or program in connection with our website". Section 11.6 prohibits scraping. Section 14.1 states that all content, including text, is Shwapno's property and that unauthorised use is strictly prohibited. The terms carry no version date.
- robots.txt rules for product pages: not checked; the terms already prohibit all automated access.
- Automated collection allowed (yes / no / unclear): no
- Redistribution of listing text allowed (yes / no / unclear): no
- Scripts and languages used in listings:
- Fields available:
- Notes: Excluded unless written permission is obtained from Shwapno (ACI Logistics Ltd). Manual copying for private research is not explicitly addressed, but section 14.1 is broad. foodpanda has delivered groceries from Shwapno, so foodpanda listings may duplicate Shwapno products.

## Daraz (grocery section)

- Date checked: 2026-11-04
- URL: https://www.daraz.com.bd
- Platform still operating: yes
- Terms of use summary (with link): https://www.daraz.com.bd/wow/i/bd/help-pages/terms-and-conditions/. Section 2.E grants a licence only for shopping for personal items, and states that it does not include "any collection and use of any product listings, descriptions, or prices", "any derivative use of this Site or its contents", or "any use of data mining, robots, or similar data gathering and extraction tools". Section 2.J states that all content, including text and its selection and arrangement, is Daraz's property and protected by copyright. The terms carry no version date.
- robots.txt rules for product pages: not checked; the terms already prohibit collection.
- Automated collection allowed (yes / no / unclear): no
- Redistribution of listing text allowed (yes / no / unclear): no
- Scripts and languages used in listings:
- Fields available:
- Notes: Excluded. Manual collection of listings is also excluded by section 2.E. Usable only with express written consent from Daraz Bangladesh Limited (legal contact given in the terms: legal@daraz.com.bd).

## foodpanda (grocery)

- Date checked: 2026-11-04
- URL: https://www.foodpanda.com.bd (pandamart only)
- Platform still operating: yes
- Terms of use summary (with link): https://www.foodpanda.com.bd/contents/terms-and-conditions.htm. foodpanda Bangladesh Terms of Use, read on the foodpanda website on 2026-11-04. No clause prohibits scraping or the collection of product listings. Section 3.1 prohibits harvesting information about other people (3.1.10) and any conduct that exposes foodpanda to "liability or detriment of any type", at its sole discretion (3.1.13). Section 4 protects trademarks, logos, images and service marks, but does not mention listing text, and states that use of materials on the Platform may infringe third-party rights. Section 2.1 states that an account is needed to use the Platform. Section 1.2 states that vendors may be third parties or foodpanda itself. The terms carry no version date.
- robots.txt rules for product pages: checked 2026-11-04. For User-agent: *, the disallowed paths cover login, referral, checkout, order tracking, payments, campaign and landing pages, an internal API path and */view-all/* pages; product and shop pages are not disallowed. No crawl delay for general agents. GPTBot (OpenAI's AI training crawler) is disallowed from the whole site, while OpenAI's search and user agents are allowed with a 5-second crawl delay. Sitemap: https://www.foodpanda.com.bd/sitemap.xml
- Automated collection allowed (yes / no / unclear): unclear
- Redistribution of listing text allowed (yes / no / unclear): unclear
- Scripts and languages used in listings: Latin script; English, with Bangla variety names written in Latin letters (for example "Miniket"), which do not make a title romanised under the script rules. Bangla-script titles not seen yet.
- Fields available: title, selling price, original price when discounted, country of origin, description, shop category. No separate brand or size fields.
- Notes: Manual collection appears permissible, subject to two conditions. (1) Listings must be viewable without logging in, as required by the project's collection rules: checked on 2026-11-05 in a private window, and they are viewable. (2) Collect only from pandamart, foodpanda's own shop, because third-party vendors (possibly including Shwapno) may hold rights in their listing text. Collect only from the Gulshan-Banani pandamart store (URL path /darkstore/vbpl/pandamart-gulshan-banani/), with the site language set to EN. Product page URLs have the form /darkstore/<store>/<store-name>/category/<uuid>/product/<id> and do not match any disallowed robots.txt path. Use the numeric product ID as listing_id. Do not use */view-all/* pages. robots.txt blocks GPTBot site-wide, suggesting foodpanda objects to collection for AI training; seek written permission before publishing listing text or using it beyond this research project.

## Chaldal

- Date checked: 2026-11-08
- URL: https://chaldal.com
- Platform still operating: yes
- Terms of use summary (with link): https://chaldal.com/t/TermsOfUse. Section 6.1 states that no material on the site may be "copied, reproduced, republished, installed, posted, transmitted, stored, or distributed without written permission from Chaldal PLC". Section 6.2 prohibits any "page-scrape", "robot", "spider" or other automatic means, "or any similar or equivalent manual process, to access, acquire, copy or monitor any portion of the website or any content". The terms carry no version date.
- robots.txt rules for product pages: not checked; the terms already prohibit collection.
- Automated collection allowed (yes / no / unclear): no
- Redistribution of listing text allowed (yes / no / unclear): no
- Scripts and languages used in listings:
- Fields available:
- Notes: Excluded. Manual collection is explicitly excluded by section 6.2. Usable only with written permission from Chaldal PLC.

## Meena Bazar Online

- Date checked: 2026-11-08
- URL: https://meenabazaronline.com
- Platform still operating: yes
- Terms of use summary (with link): Terms and Conditions page linked from the site footer (exact URL to be added), read on 2026-11-08. The terms contain no clause on copying or reusing site content, intellectual property, scraping, robots or automated access. Registration is required to place orders. The Order Policy states that the site is for personal consumption and discourages reselling or commercial motives. Prices of perishable products, including rice, vary with the selected delivery location. The terms carry no version date.
- robots.txt rules for product pages: no robots.txt exists; https://meenabazaronline.com/robots.txt redirects to /exception/404 (checked 2026-11-08). Under RFC 9309 a missing robots.txt sets no restrictions, but it is not permission.
- Automated collection allowed (yes / no / unclear): unclear
- Redistribution of listing text allowed (yes / no / unclear): unclear
- Scripts and languages used in listings: Latin script, English. The product page heading is shown in title case, while the breadcrumb, URL slug and description show the name in upper case. Bangla-script titles not seen.
- Fields available: title, brand (separate field), unit (for example EACH), seller ("Sold By"), shop category (for example Grocery), selling price, original price when discounted, description. No separate size field.
- Notes: Listings are viewable without logging in (checked 2026-11-08 in a private window). Collect manually only, only items sold by Meena Bazar itself, always with the same delivery location. Copy title_raw from the main product heading. Use the numeric ID at the end of the product URL (/product/<SLUG>/<id>) as listing_id. Fill brand from the Brand field. Seek written permission before publishing listing text.
