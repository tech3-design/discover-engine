"""Generates a formal Site Discovery Report — a professional analysis document.

This is not a scorecard. It is a detailed, structured analysis paper that
documents every aspect of a site's technical configuration, content quality,
authority signals, and AI readiness. Each section describes:
  - What was analyzed (methodology)
  - What was found (observations with actual extracted data)
  - The raw evidence (details dict from each checker)
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.enums import Layer
from app.models.responses import AuditResponse, CheckResult

# ─── Section descriptions: what each analysis area covers ────────────────

_SECTION_DESCRIPTIONS: dict[str, str] = {
    # Site Foundation
    "robots_txt": (
        "Analysis of the robots.txt file, which controls how search engine "
        "and AI crawlers access the site. We examined whether the file exists, "
        "its directives, sitemap references, and AI bot policies."
    ),
    "xml_sitemap": (
        "Examination of the XML sitemap at /sitemap.xml, which helps crawlers "
        "discover and index all pages. We checked for valid XML structure, "
        "URL entries, and specialized sitemap types."
    ),
    "image_sitemap": (
        "Analysis of image sitemap entries within the XML sitemap, which help "
        "search engines discover and index image content."
    ),
    "video_sitemap": (
        "Analysis of video sitemap entries within the XML sitemap, which help "
        "search engines discover and index video content."
    ),
    "news_sitemap": (
        "Examination of news sitemap entries, which are used by Google News "
        "and other news aggregators to discover timely content."
    ),
    "https": (
        "Verification of HTTPS encryption, which is a fundamental security "
        "and trust signal for both users and search engines."
    ),
    "canonical_tags": (
        "Analysis of canonical tags, which tell search engines which version "
        "of a page is the authoritative one, preventing duplicate content issues."
    ),
    "crawl_traps": (
        "Detection of crawl trap patterns — URL structures that can cause "
        "infinite crawling loops, such as session IDs, calendar patterns, "
        "or excessive query parameters."
    ),
    "robots_meta": (
        "Examination of robots meta tags and X-Robots-Tag headers, which "
        "provide page-level instructions to crawlers about indexing and "
        "link-following behavior."
    ),
    # Indexability & Speed
    "core_web_vitals": (
        "Analysis of performance-related indicators discoverable from the "
        "HTML source, including viewport configuration for mobile compatibility "
        "and resource hints (preconnect/preload) for faster loading."
    ),
    "js_rendering": (
        "Assessment of the page's rendering strategy — whether content is "
        "available in the raw HTML (server-side rendered) or requires "
        "JavaScript execution (client-side rendered)."
    ),
    # Graph & Discovery
    "internal_linking": (
        "Analysis of the internal linking structure, including link count, "
        "anchor text diversity, navigation patterns, and contextual links "
        "within content paragraphs."
    ),
    "llm_txt": (
        "Examination of the llms.txt file at /.well-known/llms.txt, a "
        "machine-readable description of the site specifically designed "
        "for Large Language Models."
    ),
    # Node Readability
    "json_ld": (
        "Comprehensive analysis of JSON-LD structured data markup. We extracted "
        "all schema types, evaluated property completeness against the schema.org "
        "specification (19 recognized types with required and recommended "
        "properties), and checked for date metadata freshness."
    ),
    "og_metadata": (
        "Discovery of Open Graph and Twitter Card meta tags, which control "
        "how the page appears when shared on social media platforms, messaging "
        "apps, and other surfaces that generate link previews."
    ),
    "semantic_html": (
        "Analysis of the page's semantic HTML structure, including heading "
        "hierarchy (H1-H6), heading count, and use of semantic elements."
    ),
    # Authority & Trust
    "entity_brand": (
        "Discovery of brand and entity signals, including Organization schema "
        "markup, brand mentions in page titles, contact information, social "
        "profile links, and Wikipedia references."
    ),
    "author_eeat": (
        "Comprehensive E-E-A-T (Experience, Expertise, Authoritativeness, "
        "Trustworthiness) analysis. We examined author attribution, Person "
        "schema markup, professional credentials, links to authoritative "
        "domains (.gov, .edu, major publications), trust pages (about, "
        "contact, privacy, terms), publication dates, external source "
        "diversity, and transparency signals (editorial policies, disclosures)."
    ),
    "expertise_schema": (
        "Analysis of domain-specific expertise signals in structured data, "
        "including specialized schema types (Medical, Legal, Financial), "
        "speakable markup for voice assistants, and credential properties."
    ),
    # LLM Extraction
    "faq_schema": (
        "Examination of FAQ-style content structures that are directly "
        "extractable by AI systems — including FAQPage JSON-LD schema, "
        "details/summary accordion blocks, and question-style headings."
    ),
    "ai_visibility": (
        "Static analysis of how extractable and citable the page's content "
        "is for Large Language Models. We examined answer-first formatting, "
        "citation patterns, paragraph self-containedness, key takeaway blocks, "
        "definition patterns, sentence quotability, and content chunking "
        "via descriptive headings."
    ),
    # Content Quality
    "content_quality": (
        "Deep analysis of content quality signals based on information "
        "retrieval research. We examined citation and source references, "
        "statistical data points, expert quotes, authoritative vs. hedging "
        "language, readability metrics (Flesch-Kincaid), technical terminology, "
        "vocabulary diversity (Type-Token Ratio), paragraph structure, "
        "transition words, answer-first formatting, and keyword repetition."
    ),
}

# ─── Finding code → formal observation text ──────────────────────────────

_FINDING_TEXT: dict[str, str] = {
    # -- robots_txt --
    "robots_txt_exists": "A robots.txt file was found at the root of the site.",
    "robots_txt_missing": "No robots.txt file was found at the expected location.",
    "no_blanket_disallow": "The robots.txt does not contain a blanket Disallow: / directive — crawlers are permitted to access the site.",
    "blanket_disallow_found": "The robots.txt contains a blanket Disallow: / directive that blocks all crawlers from accessing site content.",
    "sitemap_directive_present": "A Sitemap directive was found in robots.txt, pointing crawlers to the XML sitemap.",
    "ai_bots_allowed": "No restrictions on AI-specific crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) were found.",
    # -- xml_sitemap --
    "sitemap_exists": "An XML sitemap was located at /sitemap.xml.",
    "sitemap_missing": "No XML sitemap was found at /sitemap.xml.",
    "valid_sitemap_with_urls": "The sitemap contains valid XML with URL entries.",
    "valid_xml_no_urls": "The sitemap is valid XML but contains no URL entries.",
    "invalid_sitemap_format": "A file exists at /sitemap.xml but does not conform to the sitemap XML specification.",
    # -- image / video / news sitemap --
    "image_tags_in_sitemap": "Image sitemap entries (<image:image>) were found within the sitemap.",
    "no_image_sitemap": "No image sitemap entries were found.",
    "video_tags_in_sitemap": "Video sitemap entries (<video:video>) were found within the sitemap.",
    "no_video_sitemap": "No video sitemap entries were found.",
    "news_sitemap_found": "A news sitemap (<news:news>) was found.",
    "news_site_no_news_sitemap": "The site appears to publish news-style content but no news sitemap was found.",
    # -- https --
    "https_enabled": "The site is served over HTTPS with a valid TLS connection.",
    "not_https": "The site is not served over HTTPS.",
    # -- canonical_tags --
    "canonical_tag_present": "A <link rel=\"canonical\"> tag was found on the page.",
    "no_canonical_tag": "No canonical tag was found on the page.",
    "self_referencing_canonical": "The canonical tag is self-referencing, pointing to the current URL.",
    "canonical_points_elsewhere": "The canonical tag points to a different URL, indicating this page defers to another as the authoritative version.",
    "conflicting_canonicals": "Multiple canonical tags with differing URLs were found, creating conflicting signals.",
    "single_canonical": "A single canonical tag is present with no conflicts.",
    "no_conflicts": "Multiple canonical declarations are present but all reference the same URL.",
    # -- crawl_traps --
    "no_crawl_traps_detected": "No crawl trap patterns were detected in the internal link structure.",
    "session_ids_in_urls": "Session identifiers were found embedded in URLs, which can create crawl traps.",
    "calendar_pattern_detected": "Infinite calendar URL patterns were detected, which can cause unbounded crawling.",
    "excessive_url_params": "Internal links with excessive query parameters were found, suggesting possible faceted navigation traps.",
    # -- robots_meta --
    "no_robots_meta_tag": "No robots meta tag is present — crawlers are free to index and follow links.",
    "noindex_directive": "A noindex robots meta directive was found — search engines are instructed not to index this page.",
    "nofollow_directive": "A nofollow robots meta directive was found — search engines are instructed not to follow links on this page.",
    "conflicting_directives": "Conflicting robots meta directives were found (both index and noindex).",
    "robots_meta_ok": "Robots meta tags are present and permit indexing and link following.",
    # -- core_web_vitals --
    "viewport_meta_present": "A viewport meta tag was found, indicating mobile-responsive configuration.",
    "viewport_meta_missing": "No viewport meta tag was found — the page may not render properly on mobile devices.",
    "resource_hints_present": "Resource hints (preconnect/preload directives) were found, indicating performance optimization.",
    "no_resource_hints": "No resource hints (preconnect/preload) were found.",
    # -- js_rendering --
    "noscript_fallback_present": "A <noscript> fallback is provided for environments without JavaScript support.",
    "no_noscript_fallback": "No <noscript> fallback was found.",
    "main_content_in_html": "Main content is present in the raw HTML source (server-side rendered).",
    "no_main_content_element": "No <main> or <article> element was found in the HTML source.",
    "ssr_content_detected": "Server-side rendered content was detected within the application root element.",
    "empty_root_div_csr_likely": "The application root element is empty, indicating the page likely relies on client-side JavaScript rendering.",
    # -- internal_linking --
    "excellent_link_count": "A substantial internal link network was found (10 or more internal links).",
    "good_link_count": "A moderate internal link network was found (5-9 internal links).",
    "adequate_link_count": "A minimal internal link structure was found (3-4 internal links).",
    "insufficient_links": "Very few internal links were found (fewer than 3).",
    "diverse_anchor_text": "The anchor text across internal links is diverse, using varied descriptive text.",
    "moderate_anchor_diversity": "Moderate anchor text diversity was observed across internal links.",
    "low_anchor_diversity": "Anchor text across internal links is repetitive, with low diversity.",
    "visible_faq_section": "A visible FAQ section was found on the page.",
    # -- llm_txt --
    "llm_txt_exists": "An llms.txt file was found at /.well-known/llms.txt.",
    "llm_txt_missing": "No llms.txt file was found — no machine-readable site description is available for LLMs.",
    "llm_txt_comprehensive": "The llms.txt file is comprehensive, containing descriptive content and URLs.",
    "llm_txt_has_urls": "The llms.txt file contains URLs but limited descriptive content.",
    "llm_txt_descriptive_no_urls": "The llms.txt file has descriptive content but no URLs.",
    "llm_txt_minimal": "The llms.txt file exists but contains minimal content.",
    # -- json_ld --
    "json_ld_present": "JSON-LD structured data was found on the page.",
    "no_json_ld": "No JSON-LD structured data was found on the page.",
    "json_ld_parse_error": "One or more JSON-LD blocks could not be parsed due to malformed JSON.",
    "valid_schema_context": "The JSON-LD blocks reference a valid schema.org context.",
    "date_metadata_present": "Date metadata (datePublished and/or dateModified) was found in structured data.",
    # -- semantic_html --
    "single_h1": "A single <h1> heading was found on the page.",
    "no_h1": "No <h1> heading was found on the page.",
    "valid_heading_hierarchy": "The heading hierarchy follows a valid sequential order (no skipped levels).",
    "heading_hierarchy_gaps": "The heading hierarchy contains gaps (e.g., H2 directly followed by H4).",
    "no_headings": "No heading tags were found on the page.",
    # -- entity_brand --
    "organization_schema_present": "Organization, Corporation, or LocalBusiness schema markup was found.",
    "no_organization_schema": "No Organization schema markup was found.",
    "brand_in_title_or_h1": "The brand name appears in the page title or H1 heading.",
    "contact_info_present": "Contact information (email or phone link) was found on the page.",
    "no_social_links": "No social media profile links were found.",
    "wikipedia_link": "A Wikipedia link associated with the brand was found.",
    # -- author_eeat --
    "author_byline_found": "An author byline or attribution was found on the page.",
    "no_author_byline": "No author byline or attribution was found.",
    "author_about_links": "Links to author, about, or team pages were found.",
    "no_author_about_links": "No links to author or about pages were found.",
    "person_schema_present": "Person schema markup was found in the structured data.",
    "no_person_schema": "No Person schema markup was found.",
    "author_credentials_in_schema": "Author credentials (jobTitle or hasCredential properties) were found in the Person schema.",
    "credentials_mentioned": "Professional credentials or titles were mentioned in the page content.",
    "no_credentials_found": "No professional credentials were found in the content.",
    "no_trust_links": "No links to authoritative or trust domains (.gov, .edu, major publications) were found.",
    "no_trust_pages": "No trust pages (about, contact, privacy, terms) were found among the site's links.",
    "publication_date_found": "A publication date was found on the page.",
    "no_publication_date": "No publication date was found on the page.",
    "modified_date_found": "A last-modified or updated date was found on the page.",
    "no_external_links": "No external links were found on the page.",
    "no_transparency_signals": "No transparency signals (editorial policies, disclosures, fact-checking notices) were found.",
    # -- expertise_schema --
    "no_schema_markup": "No schema markup of any kind was found.",
    "general_schema_only": "Schema markup was found, but no domain-specific expertise types (Medical, Legal, Financial, etc.).",
    "speakable_present": "The speakable property was found in schema, marking content for voice assistant extraction.",
    "no_speakable": "No speakable property was found in the schema.",
    "credentials_in_schema": "Credential or expertise properties (hasCredential, knowsAbout) were found in the schema.",
    "no_credentials_in_schema": "No credential or expertise properties were found in the schema.",
    # -- faq_schema --
    "faq_schema_present": "FAQPage JSON-LD schema was found.",
    "self_contained_answers": "Q&A blocks contain self-contained answers with substantive content.",
    "partial_answer_quality": "Some Q&A blocks contain answers, but coverage is limited.",
    "no_html": "No HTML content was available for analysis.",
    # -- content_quality --
    "no_citations_found": "No citation or source reference patterns were found in the content.",
    "reference_section_found": "A dedicated references or bibliography section was found.",
    "no_statistics_found": "No statistical data points were found in the content.",
    "no_quotes_found": "No attributed quotes or blockquote elements were found.",
    "no_tone_signals": "No authoritative or hedging language patterns were detected.",
    "answer_first_detected": "The content opens with a direct answer-first format.",
    "no_answer_first_detected": "The content does not open with a direct answer.",
    "keyword_stuffing_detected": "Keyword repetition analysis indicates the most frequent bigram exceeds 3% of all bigrams.",
    "no_technical_terms_found": "No technical terms, acronyms, or domain-specific vocabulary were found.",
    # -- og_metadata --
    "og_title_found": "The og:title meta tag was found.",
    "og_title_missing": "The og:title meta tag is absent.",
    "og_description_found": "The og:description meta tag was found.",
    "og_description_missing": "The og:description meta tag is absent.",
    "og_image_found": "The og:image meta tag was found.",
    "og_image_missing": "The og:image meta tag is absent — link previews on social platforms will lack an image.",
    "og_url_found": "The og:url meta tag was found.",
    "og_url_missing": "The og:url meta tag is absent.",
    "og_type_found": "The og:type meta tag was found.",
    "og_type_missing": "The og:type meta tag is absent.",
    "og_site_name_found": "The og:site_name meta tag was found.",
    "og_site_name_missing": "The og:site_name meta tag is absent.",
    "twitter_card_found": "The twitter:card meta tag was found.",
    "twitter_card_missing": "The twitter:card meta tag is absent.",
    "twitter_title_found": "The twitter:title meta tag was found.",
    "twitter_title_missing": "The twitter:title meta tag is absent.",
    "twitter_image_found": "The twitter:image meta tag was found.",
    "twitter_image_missing": "The twitter:image meta tag is absent.",
    "twitter_description_found": "The twitter:description meta tag was found.",
    "twitter_description_missing": "The twitter:description meta tag is absent.",
    "og_image_no_dimensions": "The og:image is specified but image dimensions (og:image:width, og:image:height) are not declared.",
    # -- ai_visibility --
    "ai_answer_first_detected": "The content opens with a direct answer, making it immediately extractable by language models.",
    "ai_no_answer_first": "The content does not open with a direct answer.",
    "ai_no_citations": "No structured citation patterns were found that language models could use for source attribution.",
    "ai_paragraphs_self_contained": "All paragraphs are self-contained — no dependency language ('as mentioned above', 'see below') was detected.",
    "ai_takeaway_blocks_found": "Key takeaway, summary, or TLDR blocks were found on the page.",
    "ai_no_takeaway_blocks": "No key takeaway or summary blocks were found.",
    "ai_no_definitions": "No definition patterns ('X is defined as', 'X refers to') were found.",
    "ai_no_quotable_sentences": "No short, factual declarative sentences suitable for direct quoting were found.",
    "ai_no_headings": "No H2/H3 headings were found — the content is not chunked into navigable sections.",
}

# ─── Layer metadata ──────────────────────────────────────────────────────

LAYER_META: dict[Layer, dict] = {
    Layer.SITE_FOUNDATION: {
        "title": "Site Foundation",
        "description": (
            "This section examines the fundamental technical infrastructure "
            "that determines how crawlers — both traditional search engines "
            "and AI systems — can access, understand, and navigate the site."
        ),
    },
    Layer.INDEXABILITY_SPEED: {
        "title": "Indexability & Performance",
        "description": (
            "This section analyzes how effectively the page can be indexed "
            "by search engines, including rendering strategy, mobile "
            "compatibility, and performance indicators."
        ),
    },
    Layer.GRAPH_DISCOVERY: {
        "title": "Graph & Discovery",
        "description": (
            "This section examines how the page connects to the broader "
            "site structure and how it makes itself discoverable to AI "
            "systems through internal linking and machine-readable descriptions."
        ),
    },
    Layer.NODE_READABILITY: {
        "title": "Node Readability & Structured Data",
        "description": (
            "This section analyzes the page's structured data markup, "
            "semantic HTML, and social sharing metadata — the machine-readable "
            "layer that enables search engines and platforms to understand "
            "and present the content."
        ),
    },
    Layer.AUTHORITY_TRUST: {
        "title": "Authority & Trust Signals",
        "description": (
            "This section examines the signals that establish the page's "
            "credibility — author attribution, organizational identity, "
            "professional credentials, links to authoritative sources, "
            "and transparency indicators."
        ),
    },
    Layer.LLM_EXTRACTION: {
        "title": "LLM Extraction & AI Readiness",
        "description": (
            "This section analyzes how effectively AI systems and Large "
            "Language Models can extract, cite, and use the page's content. "
            "It examines content structures that facilitate machine comprehension."
        ),
    },
    Layer.CONTENT_QUALITY: {
        "title": "Content Quality Analysis",
        "description": (
            "This section provides a deep analysis of content quality "
            "indicators — the signals that determine whether content is "
            "well-researched, authoritative, readable, and substantive."
        ),
    },
}


def _humanize_finding(raw: str) -> str:
    """Convert a raw finding code into a formal observation."""
    if raw in _FINDING_TEXT:
        return _FINDING_TEXT[raw]

    if ":" in raw:
        code, value = raw.split(":", 1)
        value = value.strip()

        match code:
            # -- existing infrastructure --
            case "ai_bots_blocked":
                return f"The following AI crawlers are blocked in robots.txt: {value}."
            case "brand":
                return f"The detected brand name is: {value}."
            case "sameAs_links":
                return f"{value} sameAs links were found in Organization schema, pointing to social and profile URLs."
            case "social_links":
                return f"Social profile links were found for: {value.replace(',', ', ')}."
            case "internal_links_count":
                return f"{value} internal links were found on the page."
            case "nav_links":
                return f"The navigation structure contains {value} links."
            case "contextual_links" | "few_contextual_links":
                return f"{value} contextual links (links embedded within paragraph text) were found."
            case "fast_load_time":
                return f"The page loaded in {value}, indicating fast server response."
            case "moderate_load_time":
                return f"The page loaded in {value}, indicating moderate server response."
            case "slow_load_time":
                return f"The page loaded in {value}, indicating slow server response."
            case "very_slow_load_time":
                return f"The page loaded in {value}, indicating very slow server response."
            case "sufficient_html_text":
                return f"{value} of text content was found in the raw HTML, indicating server-side rendering."
            case "minimal_html_text":
                return f"Only {value} of text was found in the raw HTML, suggesting partial reliance on JavaScript rendering."
            case "very_low_html_text":
                return f"Very little text ({value}) was found in the raw HTML, indicating likely client-side rendering."
            case "semantic_tags":
                return f"The following semantic HTML tags were found: {value.replace(',', ', ')}."
            case "multiple_h1s":
                return f"{value} H1 headings were found on the page (convention recommends exactly one)."
            case "heading_count":
                return f"A total of {value} heading tags were found across the page."
            case "lists_present" | "lists_found":
                return f"{value} list elements (ul/ol) were found on the page."
            case "tables_present" | "tables_found":
                return f"{value} table elements were found on the page."
            case "schema_completeness":
                return f"Average schema property completeness across all types: {value}."
            case "schema_types":
                return f"The following schema types were discovered: {value.replace(',', ', ')}."
            case "schema_incomplete":
                return f"The {value} schema type is missing one or more required properties."
            case "expertise_types":
                return f"Domain-expertise schema types were found: {value.replace(',', ', ')}."
            case "faq_schema_present":
                return f"FAQPage JSON-LD schema was found containing {value} Q&A items."
            case "details_summary_blocks":
                return f"{value} details/summary accordion blocks were found."
            case "question_headings":
                return f"{value} question-style headings (ending with '?') were found."
            # -- content quality --
            case "citations_found":
                return f"{value} citation and source reference patterns were identified in the content (e.g., 'according to', '(Author, 2024)', '[1]')."
            case "statistics_found":
                return f"{value} statistical data points were identified (percentages, monetary values, growth metrics, ratios)."
            case "quotes_found":
                return f"{value} attributed quotes or blockquote elements were found."
            case "blockquotes_found":
                return f"{value} HTML blockquote elements were found."
            case "authority_signals_found":
                return f"{value} authoritative tone markers were detected (e.g., 'evidence shows', 'based on our analysis', 'best practice')."
            case "hedging_signals_found":
                return f"{value} hedging or uncertainty markers were detected (e.g., 'I think', 'maybe', 'possibly')."
            case "readability_grade":
                return f"The Flesch-Kincaid grade level is {value} (optimal range: 6-12 for general audiences)."
            case "readability_ease":
                return f"The Flesch reading ease score is {value} (higher is easier to read; 60+ is considered accessible)."
            case "technical_terms_found":
                return f"{value} technical terms were identified, including acronyms, defined terms, and compound technical phrases."
            case "acronym_definitions_found":
                return f"{value} explicitly defined acronyms were found (e.g., 'Search Engine Optimization (SEO)')."
            case "vocabulary_ttr":
                return f"The vocabulary Type-Token Ratio is {value} (a measure of lexical diversity; higher values indicate more varied word choice)."
            case "word_count":
                return f"The total content word count is {value}."
            case "paragraph_avg_words":
                return f"The average paragraph length is {value} words (optimal range: 20-80 words for readability)."
            case "transition_words_found":
                return f"{value} transition words and phrases were found (e.g., 'however', 'therefore', 'moreover', 'for example')."
            case "top_bigram":
                return f"The most frequently repeated two-word phrase is: \"{value}\"."
            # -- author_eeat --
            case "trust_links_found":
                return f"{value} links to authoritative trust domains were found (.gov, .edu, major publications, academic journals)."
            case "trust_pages_found":
                return f"The following trust pages were found among the site's links: {value.replace(',', ', ')}."
            case "external_domains_found":
                return f"External links point to {value} distinct domains, indicating source diversity."
            case "transparency_signals":
                return f"The following transparency signals were found: {value.replace(',', ', ')}."
            case "org_info_signals":
                return f"The following organizational information signals were found: {value.replace(',', ', ')}."
            # -- og_metadata --
            case "og_image_dimensions":
                return f"Open Graph image dimensions are specified: {value}."
            case "og_description_length":
                return f"The og:description is {value} characters long (optimal range: 50-160 characters)."
            # -- ai_visibility --
            case "ai_citations_found":
                return f"{value} structured citation patterns were found that language models can use for source attribution."
            case "ai_dependency_language_found":
                return f"{value} dependency phrases were found ('as mentioned above', 'see below', etc.), which reduce paragraph extractability."
            case "ai_definitions_found":
                return f"{value} definition patterns were found ('X is defined as', 'X refers to'), which are directly extractable by language models."
            case "ai_quotable_sentences":
                return f"{value} short, factual declarative sentences (10-30 words) were found that are suitable for direct quoting by AI systems."
            case "ai_headings_found":
                return f"{value} H2/H3 headings were found, providing content chunking for navigability."
            case "ai_descriptive_headings":
                return f"Of these, {value} are descriptive (non-generic) headings that convey topical meaning."
            case "ai_generic_headings":
                return f"{value} headings use generic text (e.g., 'Introduction', 'Overview') that does not convey specific topic information."

    return raw.replace("_", " ").capitalize() + "."


def _build_analysis_section(check: CheckResult) -> dict:
    """Build a formal analysis section for a single check."""
    observations = [_humanize_finding(f) for f in check.findings]

    section: dict = {
        "subject": check.name,
        "methodology": _SECTION_DESCRIPTIONS.get(check.check_id, ""),
        "observations": observations,
    }

    # Include extracted data as evidence, but filter out internal-only keys
    if check.details:
        section["evidence"] = check.details

    return section


def build_report(audit: AuditResponse) -> dict:
    """Build a formal Site Discovery Report from a completed audit."""
    if not audit.signal_score:
        return {"url": audit.url, "error": audit.error or "No results available"}

    sections: list[dict] = []
    for layer_result in audit.signal_score.layers:
        analyses = []
        for check in layer_result.checks:
            analysis = _build_analysis_section(check)
            if analysis["observations"]:
                analyses.append(analysis)

        layer_meta = LAYER_META.get(layer_result.layer, {})
        sections.append({
            "title": layer_meta.get("title", layer_result.label),
            "description": layer_meta.get("description", ""),
            "analyses": analyses,
        })

    return {
        "document_type": "Site Discovery Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "url": audit.url,
        "executive_summary": _build_executive_summary(audit),
        "methodology": (
            "This report was generated through automated static analysis of the "
            "target URL. The analysis engine crawled the page and its associated "
            "resources (robots.txt, sitemap.xml, llms.txt), then performed 22 "
            "independent analyses across 7 domains: Site Foundation, Indexability "
            "& Performance, Graph & Discovery, Node Readability, Authority & Trust, "
            "LLM Extraction, and Content Quality. Each analysis examines specific "
            "technical and content signals, extracts relevant data, and reports "
            "observations. No subjective assessments were made — all observations "
            "are based on the presence, absence, or measured value of specific "
            "signals in the HTML source and associated files."
        ),
        "sections": sections,
    }


def _build_executive_summary(audit: AuditResponse) -> str:
    """Build a formal executive summary paragraph."""
    if not audit.signal_score:
        return ""

    checks_by_id: dict[str, CheckResult] = {}
    for layer in audit.signal_score.layers:
        for check in layer.checks:
            checks_by_id[check.check_id] = check

    parts: list[str] = []

    # Infrastructure
    infra: list[str] = []
    c = checks_by_id.get("https")
    if c:
        infra.append("HTTPS" if "https_enabled" in c.findings else "no HTTPS")
    c = checks_by_id.get("robots_txt")
    if c:
        if "robots_txt_exists" in c.findings:
            infra.append("robots.txt present")
        else:
            infra.append("no robots.txt")
    c = checks_by_id.get("xml_sitemap")
    if c:
        if "sitemap_exists" in c.findings:
            infra.append("XML sitemap present")
        else:
            infra.append("no XML sitemap")
    if infra:
        parts.append(f"Site infrastructure: {', '.join(infra)}.")

    # Structured data
    c = checks_by_id.get("json_ld")
    if c:
        types = c.details.get("types", [])
        if types:
            parts.append(f"Structured data includes {len(types)} schema type(s): {', '.join(types)}.")
        else:
            parts.append("No JSON-LD structured data was found.")

    # Social metadata
    c = checks_by_id.get("og_metadata")
    if c:
        og = c.details.get("og_tags_found", 0)
        tw = c.details.get("twitter_tags_found", 0)
        parts.append(f"Social sharing metadata: {og} of 6 Open Graph tags and {tw} of 4 Twitter Card tags present.")

    # Content
    c = checks_by_id.get("content_quality")
    if c:
        wc = c.details.get("word_count", 0)
        cites = c.details.get("citation_count", 0)
        stats = c.details.get("statistic_count", 0)
        quotes = c.details.get("attributed_quotes", 0) + c.details.get("blockquote_elements", 0)
        parts.append(
            f"Content analysis: {wc:,} words, {cites} citation patterns, "
            f"{stats} statistical references, and {quotes} attributed quotes identified."
        )

    # E-E-A-T
    c = checks_by_id.get("author_eeat")
    if c:
        trust_count = c.details.get("trust_link_count", 0)
        trust_pages = c.details.get("trust_pages", [])
        diversity = c.details.get("source_diversity", 0)
        parts.append(
            f"Trust analysis: {trust_count} authoritative domain links, "
            f"{len(trust_pages)} trust page(s), and {diversity} external domain(s) identified."
        )

    # AI readiness
    c = checks_by_id.get("ai_visibility")
    if c:
        quotable = c.details.get("quotable_count", 0)
        defs = c.details.get("definition_count", 0)
        deps = c.details.get("dependency_count", 0)
        parts.append(
            f"AI extractability: {quotable} quotable sentences, {defs} definition patterns, "
            f"and {deps} dependency phrase(s) found."
        )

    # LLM discovery
    c = checks_by_id.get("llm_txt")
    if c:
        if "llm_txt_exists" in c.findings:
            parts.append("An llms.txt file is published for LLM discovery.")
        else:
            parts.append("No llms.txt file was found.")

    return " ".join(parts)
