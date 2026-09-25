/**
 * BuzDev Outreach MCP Server — Cloudflare Workers (standalone)
 *
 * Fork of customer-outreach-mcp with all Agentora dependencies removed.
 * Provides 8 business outreach tools:
 *   buzdev_fetch_website, buzdev_search_web, buzdev_research_company,
 *   buzdev_search_for_leads, buzdev_discover_email, buzdev_search_social,
 *   buzdev_export_leads, buzdev_discover_extensions
 *
 * Auth: Optional Bearer token (BUZDEV_API_KEY env var).
 *       If BUZDEV_API_KEY is not set, all tools are open (no auth required).
 *       If set, clients must pass it as: Authorization: Bearer <key>
 *
 * No credit gate — all tools are free.
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const JINA_READER_URL = "https://r.jina.ai/";
const FREESERP_URL = "https://freeserp.ai/api.php";

// ---------------------------------------------------------------------------
// Auth (optional)
// ---------------------------------------------------------------------------

function extractBearerToken(request: Request): string | null {
  const authHeader = request.headers.get("Authorization") || request.headers.get("authorization");
  if (authHeader?.startsWith("Bearer ")) {
    return authHeader.slice(7);
  }
  const altHeader = request.headers.get("X-BuzDev-Key") || request.headers.get("x-buzdev-key");
  if (altHeader) return altHeader;
  return null;
}

function validateToken(token: string, expectedKey: string | undefined): boolean {
  if (!expectedKey) return true; // No key configured = open access
  return token === expectedKey;
}

// ---------------------------------------------------------------------------
// Web helpers
// ---------------------------------------------------------------------------

async function fetchPage(url: string, jinaKey?: string): Promise<{ status: "ok" | "error"; markdown?: string; error?: string; url?: string; via?: string }> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const headers: Record<string, string> = { "Accept": "text/markdown" };
      if (jinaKey) headers["Authorization"] = `Bearer ${jinaKey}`;
      const response = await fetch(`${JINA_READER_URL}${url}`, { headers });
      if (response.ok) {
        const text = await response.text();
        if (text && text.length >= 10) {
          return { status: "ok", markdown: text.substring(0, 15000), url, via: "jina" };
        }
      }
      if (attempt === 0) await new Promise((r) => setTimeout(r, 1500));
    } catch { /* fall through to retry, then direct fetch */ }
  }
  try {
    const response = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; BuzDevBot/1.0)" },
      redirect: "follow",
    });
    if (response.ok) {
      const raw = await response.text();
      const titleM = raw.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
      const text = htmlToText(raw).substring(0, 15000);
      if (text.length >= 10) {
        const title = titleM ? `Title: ${htmlToText(titleM[1])}\n\n` : "";
        return { status: "ok", markdown: `${title}${text}`, url, via: "direct" };
      }
    }
  } catch { /* ignore */ }
  return { status: "error", error: "Jina rate-limited and direct fetch failed", url };
}

function htmlToText(htmlText: string): string {
  return htmlText
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function searchWeb(query: string, numResults: number, jinaKey?: string): Promise<Array<Record<string, unknown>>> {
  try {
    const response = await fetch(`${FREESERP_URL}?q=${encodeURIComponent(query)}&size=${numResults}`);
    if (response.ok) {
      const data = await response.json() as Record<string, unknown>;
      const results = data.results as Array<Record<string, unknown>> | undefined;
      if (results && results.length > 0) {
        return results.slice(0, numResults).map((item) => ({
          url: `https://${item.domain as string}` || "",
          domain: item.domain as string || "",
          title: item.title as string || "",
          description: ((item.ai_summary as string) || (item.title as string) || "").substring(0, 500),
          domain_rating: item.dr,
          tech_stack: item.ai_source,
          went_live: item.went_live,
        }));
      }
    }
  } catch { /* fall through */ }

  const ddg = await searchDDG(query, numResults);
  if (ddg.length > 0) return ddg;

  if (jinaKey) {
    try {
      const response = await fetch(`https://s.jina.ai/${encodeURIComponent(query)}`, {
        headers: { "Accept": "application/json", "Authorization": `Bearer ${jinaKey}` },
      });
      if (response.ok) {
        const data = await response.json() as Record<string, unknown>;
        const items = (data.data || []) as Array<Record<string, unknown>>;
        return items.slice(0, numResults).map((item) => ({
          url: (item.url as string) || "",
          title: (item.title as string) || "",
          description: ((item.description as string) || (item.content as string) || "").substring(0, 500),
        }));
      }
    } catch { /* fall through */ }
  }

  return [];
}

async function searchDDG(query: string, numResults: number): Promise<Array<Record<string, unknown>>> {
  try {
    const response = await fetch(`https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" },
    });
    if (!response.ok) return [];
    const page = await response.text();
    const out: Array<Record<string, unknown>> = [];
    for (const block of page.split('class="result__body"').slice(1)) {
      const linkM = block.match(/class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/);
      if (!linkM) continue;
      let href = linkM[1];
      const uddg = href.match(/[?&]uddg=([^&]+)/);
      if (uddg) href = decodeURIComponent(uddg[1]);
      if (!href.startsWith("http")) continue;
      const title = linkM[2].replace(/<[^>]+>/g, "").trim();
      const snipM = block.match(/class="result__snippet"[^>]*>([\s\S]*?)<\/a>/);
      const desc = snipM ? snipM[1].replace(/<[^>]+>/g, "").trim() : "";
      let domain = "";
      try { domain = new URL(href).hostname.replace(/^www\./, ""); } catch { /* keep empty */ }
      out.push({ url: href, domain, title, description: desc.substring(0, 500) });
      if (out.length >= numResults) break;
    }
    return out;
  } catch {
    return [];
  }
}

function extractEmails(text: string): string[] {
  const found = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g) || [];
  return [...new Set(found)].filter((e) =>
    !/sentry|noreply|donotreply|example\.com|yourdomain|w3\.org|schema/i.test(e)
  );
}

// ---------------------------------------------------------------------------
// Extension registry (static)
// ---------------------------------------------------------------------------

const EXTENSION_REGISTRY: Record<string, { description: string; extensions: Array<Record<string, unknown>> }> = {
  render_pitch_deck: {
    description: "Render pitch deck content into polished PPTX/PDF",
    extensions: [
      { name: "deckpipe", type: "mcp_server", url: "https://deckpipe.dev/mcp", auth: "oauth", cost: "10 credits per slide", setup: "easy", best_for: "Agent-native HTML/CSS slides" },
      { name: "SlidesGPT", type: "mcp_server", url: "https://claude.slidesgpt.com/mcp", auth: "api_key", cost: "Paid per presentation", setup: "easy", best_for: "Polished PPTX with themes and images" },
      { name: "python-pptx (local)", type: "library", url: "pip install python-pptx", auth: "none", cost: "free", setup: "trivial", best_for: "Basic PPTX from JSON" },
    ],
  },
  send_outreach_emails: {
    description: "Send cold outreach emails (use with caution)",
    extensions: [
      { name: "reachout_mcp", type: "mcp_server", url: "https://github.com/TheCodeDaniel/reachout_mcp", auth: "SMTP", cost: "free (self-hosted)", setup: "medium", best_for: "Open-source outreach with human-in-the-loop" },
      { name: "Resend", type: "api", url: "https://resend.com", auth: "api_key", cost: "Free: 3,000 emails/month", setup: "easy", best_for: "Simple reliable transactional email" },
    ],
  },
  verify_emails: {
    description: "Verify email addresses to reduce bounce rates",
    extensions: [
      { name: "Reacher", type: "library", url: "https://github.com/reacherhq/check-if-email-exists", auth: "none", cost: "free", setup: "medium (Docker)", best_for: "Full SMTP verification" },
    ],
  },
  competitive_intelligence: {
    description: "Deep competitive intelligence and market research",
    extensions: [
      { name: "Agent-Reach", type: "skill", url: "https://github.com/Panniantong/Agent-Reach", auth: "varies", cost: "free", setup: "medium", best_for: "Social media search across 14+ platforms" },
      { name: "Scrapling", type: "skill", url: "https://github.com/D4Vinci/Scrapling", auth: "none", cost: "free", setup: "easy", best_for: "Adaptive web scraping with anti-bot" },
    ],
  },
  social_engagement: {
    description: "Engage with prospects on social media (caution — ToS risks)",
    extensions: [
      { name: "BrowserSkill", type: "skill", url: "https://github.com/tencent/browserskill", auth: "browser session", cost: "free", setup: "medium", best_for: "Use user's real browser" },
    ],
  },
};

// ---------------------------------------------------------------------------
// Server factory
// ---------------------------------------------------------------------------

function createServer(): McpServer {
  const server = new McpServer({
    name: "buzdev-outreach",
    version: "1.0.0",
  });

  const jinaKey = ""; // No Jina key by default; free tier works.

  // =========================================================================
  // FREE TOOLS (all tools are free — no credit gate)
  // =========================================================================

  server.tool(
    "buzdev_fetch_website",
    `Fetch a website URL and return its content as clean markdown. Use this to read a business's website for analysis.

Parameters:
- url: Website URL to fetch

Free tool — no auth required.`,
    {
      url: z.string().url(),
    },
    async (args) => {
      const page = await fetchPage(args.url, jinaKey);
      if (page.status !== "ok") {
        return { content: [{ type: "text", text: JSON.stringify({ error: page.error, url: args.url }) }], isError: true };
      }
      const markdown = page.markdown || "";
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            url: args.url,
            title: markdown.split("\n")[0].replace(/^#+\s*/, "").trim(),
            content: markdown,
            word_count: markdown.split(/\s+/).length,
          }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "buzdev_search_web",
    `Search the web and return results (URLs, titles, descriptions). Use this to find companies, people, news, or any information.

Parameters:
- query: Search query
- max_results: Max results (default 10)

Free tool — no auth required.`,
    {
      query: z.string().min(1),
      max_results: z.number().int().min(1).max(50).default(10),
    },
    async (args) => {
      const results = await searchWeb(args.query, args.max_results, jinaKey);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ query: args.query, result_count: results.length, results }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "buzdev_research_company",
    `Research a company: fetches their website content, searches for recent news/products/services, and extracts any emails found. Returns raw data for you to analyze.

Parameters:
- company_name: Company name (optional if URL provided)
- url: Company website URL (optional if name provided)
- depth: "quick", "standard" (default), or "deep" (adds team, financials, reviews)

Free tool — no auth required.`,
    {
      company_name: z.string().optional(),
      url: z.string().url().optional(),
      depth: z.enum(["quick", "standard", "deep"]).default("standard"),
    },
    async (args) => {
      if (!args.company_name && !args.url) {
        return { content: [{ type: "text", text: JSON.stringify({ error: "Either company_name or url is required" }) }], isError: true };
      }

      let websiteContent: string | null = null;
      let url = args.url || "";

      if (args.url) {
        const page = await fetchPage(args.url, jinaKey);
        if (page.status === "ok") websiteContent = page.markdown || null;
      } else if (args.company_name) {
        const searchResults = await searchWeb(`${args.company_name} official website`, 3, jinaKey);
        if (searchResults.length > 0) {
          url = searchResults[0].url as string;
          const page = await fetchPage(url, jinaKey);
          if (page.status === "ok") websiteContent = page.markdown || null;
        }
      }

      const searches: Array<{ query: string; label: string }> = [
        { query: `${args.company_name} news recent`, label: "recent_news" },
        { query: `${args.company_name} products services`, label: "products" },
      ];
      if (args.depth === "deep") {
        searches.push({ query: `${args.company_name} team leadership founders`, label: "team" });
        searches.push({ query: `${args.company_name} funding revenue growth`, label: "financials" });
        searches.push({ query: `${args.company_name} reviews customers`, label: "reviews" });
      }

      const researchData: Record<string, unknown> = {};
      for (const s of searches) {
        const results = await searchWeb(s.query, 3, jinaKey);
        researchData[s.label] = results.map((r) => ({
          title: (r.title as string) || "",
          url: (r.url as string) || "",
          description: ((r.description as string) || "").substring(0, 300),
        }));
      }

      let emails: string[] = [];
      if (websiteContent) emails = extractEmails(websiteContent);

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            company_name: args.company_name || "",
            url,
            website_content: websiteContent ? websiteContent.substring(0, 12000) : null,
            emails_found_on_website: emails,
            research: researchData,
          }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "buzdev_search_for_leads",
    `Search the web for potential customers or partners using keywords. Returns results with URLs, descriptions, and optionally fetched page content and emails. You analyze and score the results.

Parameters:
- keywords: Array of keywords to search for
- queries: Custom search queries (overrides keywords, max 5)
- location: Geographic location filter (optional)
- industry: Industry filter (optional)
- max_results: Max results to return (default 20)
- fetch_content: Fetch page content for results (default true)
- max_fetch: Max pages to fetch content for (default 10)

Free tool — no auth required. Use buzdev_export_leads to export the results as CSV.`,
    {
      keywords: z.array(z.string()).optional(),
      queries: z.array(z.string()).optional(),
      location: z.string().optional(),
      industry: z.string().optional(),
      max_results: z.number().int().min(1).max(50).default(20),
      fetch_content: z.boolean().default(true),
      max_fetch: z.number().int().min(1).max(20).default(10),
    },
    async (args) => {
      if (!args.keywords && !args.queries) {
        return { content: [{ type: "text", text: JSON.stringify({ error: "Provide keywords or queries to search" }) }], isError: true };
      }

      let queries: string[] = [];
      if (args.queries) {
        queries = args.queries.slice(0, 5);
      } else if (args.keywords) {
        for (const kw of args.keywords.slice(0, 3)) {
          queries.push(`companies ${kw}`);
        }
      }

      if (args.location) queries = queries.map((q) => `${q} ${args.location}`);
      if (args.industry) queries = queries.map((q) => `${q} ${args.industry}`);

      let allResults: Array<Record<string, unknown>> = [];
      for (const q of queries) {
        const results = await searchWeb(q, 10, jinaKey);
        allResults.push(...results);
      }

      const seen = new Set<string>();
      const deduped = allResults.filter((r) => {
        const u = r.url as string;
        return u && !seen.has(u) && (seen.add(u), true);
      });

      if (args.fetch_content !== false) {
        const maxFetch = args.max_fetch || 10;
        for (let i = 0; i < Math.min(deduped.length, maxFetch); i++) {
          const page = await fetchPage(deduped[i].url as string, jinaKey);
          if (page.status === "ok") {
            deduped[i].page_content = (page.markdown || "").substring(0, 5000);
            deduped[i].emails = extractEmails(page.markdown || "");
          }
        }
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            queries_used: queries,
            total_results: deduped.length,
            results: deduped.slice(0, args.max_results),
            hint: "Analyze and score these results, then use buzdev_export_leads to export as CSV.",
          }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "buzdev_discover_email",
    `Discover email addresses for a company using multiple methods: website scraping, contact page checking, pattern-based guessing, and web search. Returns ranked results with confidence levels.

Parameters:
- url: Company website URL (required)
- company_name: Company name (optional, improves pattern guessing)
- person_name: Specific person's name (optional, for personal email patterns)

Free tool — no auth required.`,
    {
      url: z.string().url(),
      company_name: z.string().optional(),
      person_name: z.string().optional(),
    },
    async (args) => {
      const { company_name, url, person_name } = args;
      const emails = new Map<string, { email: string; confidence: string; method: string; source: string }>();
      const methods_tried: string[] = [];

      function extractEmailsLocal(text: string): string[] {
        const found: string[] = [];
        const emailRegex = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
        let match;
        while ((match = emailRegex.exec(text)) !== null) {
          const email = match[0].toLowerCase();
          if (email.match(/\.(png|jpg|gif|svg|css|js)$/i)) continue;
          if (email.includes("noreply") || email.includes("no-reply") || email.includes("example.com") || email.includes("wixpress") || email.includes("yourdomain") || email.includes("sentry")) continue;
          if (email.length < 6 || email.length > 80) continue;
          found.push(email);
        }
        return [...new Set(found)];
      }

      methods_tried.push("jina_reader_main");
      try {
        const page = await fetchPage(url, jinaKey);
        if (page.status === "ok") {
          for (const e of extractEmailsLocal(page.markdown || "")) {
            if (!emails.has(e)) emails.set(e, { email: e, confidence: "high", method: "jina_reader_main", source: url });
          }
        }
      } catch { /* ignore */ }

      methods_tried.push("direct_fetch_main");
      try {
        const resp = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0 (compatible; BuzDevBot/1.0)" } });
        if (resp.ok) {
          const html = await resp.text();
          for (const e of extractEmailsLocal(html)) {
            if (!emails.has(e)) emails.set(e, { email: e, confidence: "high", method: "direct_fetch", source: url });
          }
        }
      } catch { /* ignore */ }

      methods_tried.push("contact_page_check");
      const contactPaths = ["/contact", "/contact-us", "/about", "/about-us", "/team", "/imprint"];
      for (const path of contactPaths) {
        const contactUrl = url.replace(/\/$/, "") + path;
        try {
          const page = await fetchPage(contactUrl, jinaKey);
          if (page.status === "ok") {
            const found = extractEmailsLocal(page.markdown || "");
            for (const e of found) {
              if (!emails.has(e)) emails.set(e, { email: e, confidence: "high", method: "contact_page", source: contactUrl });
            }
            if (found.length > 0) break;
            continue;
          }
        } catch { /* ignore */ }
        try {
          const resp = await fetch(contactUrl, { headers: { "User-Agent": "Mozilla/5.0 (compatible; BuzDevBot/1.0)" }, redirect: "follow" });
          if (resp.ok) {
            const html = await resp.text();
            const found = extractEmailsLocal(html);
            for (const e of found) {
              if (!emails.has(e)) emails.set(e, { email: e, confidence: "high", method: "contact_page_direct", source: contactUrl });
            }
            if (found.length > 0) break;
          }
        } catch { /* ignore */ }
      }

      if (company_name && emails.size === 0) {
        methods_tried.push("pattern_guess");
        let domain: string | null = null;
        try { domain = new URL(url).hostname.replace(/^www\./, ""); } catch { domain = null; }
        if (domain) {
          const patterns = [
            `info@${domain}`, `contact@${domain}`, `hello@${domain}`,
            `sales@${domain}`, `support@${domain}`, `team@${domain}`,
          ];
          if (person_name) {
            const parts = person_name.toLowerCase().split(/\s+/);
            if (parts.length >= 2) {
              patterns.push(`${parts[0]}@${domain}`);
              patterns.push(`${parts[0]}.${parts[1]}@${domain}`);
              patterns.push(`${parts[0][0]}${parts[1]}@${domain}`);
            }
          }
          for (const p of patterns) {
            emails.set(p, { email: p, confidence: "low", method: "pattern_guess", source: "generated" });
          }
        }
      }

      if (emails.size === 0 || [...emails.values()].every((e) => e.confidence === "low")) {
        methods_tried.push("web_search");
        let domain: string | null = null;
        try { domain = new URL(url).hostname.replace(/^www\./, ""); } catch { domain = null; }
        if (domain) {
          const results = await searchWeb(`@"${domain}" email contact`, 5, jinaKey);
          for (const r of results) {
            const found = extractEmailsLocal((r.description as string) || "");
            for (const e of found) {
              if (e.includes(domain) && !emails.has(e)) {
                emails.set(e, { email: e, confidence: "medium", method: "web_search", source: (r.url as string) || "" });
              }
            }
          }
        }
      }

      const sortedEmails = [...emails.values()].sort((a, b) => {
        const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
        return (order[a.confidence] ?? 3) - (order[b.confidence] ?? 3);
      });

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            company_name: company_name || url,
            url,
            emails: sortedEmails,
            total_found: sortedEmails.length,
            methods_tried,
          }, null, 2),
        }],
      };
    },
  );

  server.tool(
    "buzdev_search_social",
    `Search social media platforms for mentions, discussions, and content related to a query.

Platforms:
- hackernews: Hacker News (via Algolia API, keyless, JSON)
- github: GitHub (via GitHub API, keyless, JSON)
- reddit: Reddit search (via Jina Reader, may be rate-limited)
- youtube: YouTube search (via Jina Reader, may be rate-limited)

For deeper social access (Twitter/X, Instagram, LinkedIn), use buzdev_discover_extensions.

Parameters:
- query: Search query
- platform: "hackernews", "github", "reddit", "youtube", or "all" (default)
- max_results: Max results per platform (default 10)

Free tool — no auth required.`,
    {
      query: z.string().min(1),
      platform: z.enum(["hackernews", "github", "reddit", "youtube", "all"]).default("all"),
      max_results: z.number().int().min(1).max(50).default(10),
    },
    async (args) => {
      const platforms = args.platform === "all"
        ? ["hackernews", "github", "reddit", "youtube"]
        : [args.platform];

      const allResults: Record<string, unknown> = {};

      for (const p of platforms) {
        if (p === "hackernews") {
          try {
            const resp = await fetch(
              `https://hn.algolia.com/api/v1/search?query=${encodeURIComponent(args.query)}&tags=story&hitsPerPage=${args.max_results}`
            );
            if (resp.ok) {
              const data = await resp.json() as Record<string, unknown>;
              const hits = (data.hits || []) as Array<Record<string, unknown>>;
              allResults[p] = hits.slice(0, args.max_results).map((h) => ({
                title: h.title || h.story_title || "",
                url: h.url || `https://news.ycombinator.com/item?id=${h.objectID}`,
                points: h.points,
                num_comments: h.num_comments,
                created_at: h.created_at,
              }));
            } else {
              allResults[p] = [];
            }
          } catch {
            allResults[p] = [];
          }
        } else if (p === "github") {
          try {
            const resp = await fetch(
              `https://api.github.com/search/repositories?q=${encodeURIComponent(args.query)}&per_page=${args.max_results}`
            );
            if (resp.ok) {
              const data = await resp.json() as Record<string, unknown>;
              const items = (data.items || []) as Array<Record<string, unknown>>;
              allResults[p] = items.slice(0, args.max_results).map((item) => ({
                title: item.full_name || "",
                url: item.html_url || "",
                description: (item.description || "").substring(0, 300),
                stars: item.stargazers_count,
                language: item.language,
              }));
            } else {
              allResults[p] = [];
            }
          } catch {
            allResults[p] = [];
          }
        } else if (p === "reddit") {
          try {
            const page = await fetchPage(
              `https://www.reddit.com/search/?q=${encodeURIComponent(args.query)}&sort=relevance&t=month`,
              jinaKey
            );
            if (page.status === "ok") {
              const links: Array<Record<string, string>> = [];
              const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
              let match;
              while ((match = linkPattern.exec(page.markdown || "")) !== null) {
                const title = match[1].trim();
                const url = match[2].trim();
                if (url.startsWith("http") && !url.includes("login") && !url.includes("signup")) {
                  links.push({ title: title.substring(0, 200), url });
                }
              }
              allResults[p] = links.slice(0, args.max_results);
            } else {
              allResults[p] = [];
            }
          } catch {
            allResults[p] = [];
          }
        } else if (p === "youtube") {
          try {
            const page = await fetchPage(
              `https://www.youtube.com/results?search_query=${encodeURIComponent(args.query)}`,
              jinaKey
            );
            if (page.status === "ok") {
              const links: Array<Record<string, string>> = [];
              const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
              let match;
              while ((match = linkPattern.exec(page.markdown || "")) !== null) {
                const title = match[1].trim();
                const url = match[2].trim();
                if (url.startsWith("http") && url.includes("youtube.com/watch")) {
                  links.push({ title: title.substring(0, 200), url });
                }
              }
              allResults[p] = links.slice(0, args.max_results);
            } else {
              allResults[p] = [];
            }
          } catch {
            allResults[p] = [];
          }
        }
      }

      const totalCount = Object.values(allResults).reduce(
        (sum: number, r) => sum + (Array.isArray(r) ? r.length : 0),
        0
      );

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            query: args.query,
            platform: args.platform,
            total_results: totalCount,
            results_by_platform: allResults,
            hint: "For deeper social media access (Twitter/X, Instagram, LinkedIn), use buzdev_discover_extensions with task='social_engagement'.",
          }, null, 2),
        }],
      };
    },
  );

  // =========================================================================
  // EXPORT TOOL — free (no credit gate)
  // =========================================================================

  server.tool(
    "buzdev_export_leads",
    `Export an array of lead objects as CSV or JSON. This is the deliverable output.

The agent should:
1. Use the free tools to gather and analyze leads
2. Score and filter the results (you are the intelligence)
3. Call this tool ONLY when the user wants the final CSV/JSON output

Parameters:
- data: Array of lead objects to export
- format: "csv" (default) or "json"
- filename: Filename without extension (optional)

Free tool — no credits or auth required.`,
    {
      data: z.array(z.record(z.string(), z.any())).min(1),
      format: z.enum(["csv", "json"]).default("csv"),
      filename: z.string().optional(),
    },
    async (args) => {
      const fname = args.filename || `export_${Date.now().toString(36)}`;
      const data = args.data;
      const format = args.format;

      let content: string;
      let filename: string;

      if (format === "csv") {
        const allKeys = new Set<string>();
        for (const row of data) {
          for (const k of Object.keys(row)) allKeys.add(k);
        }
        const pf = ["company_name", "name", "url", "email", "contact_email", "phone", "industry", "location", "fit_score", "score", "potential_value", "priority", "notes"];
        const ordered = pf.filter((f) => allKeys.has(f));
        const remaining = [...allKeys].filter((f) => !ordered.includes(f)).sort();
        const fn = [...ordered, ...remaining];

        const esc = (v: unknown): string => {
          if (v === null || v === undefined) return "";
          const s = typeof v === "object" ? JSON.stringify(v) : String(v);
          return s.includes(",") || s.includes('"') || s.includes("\n")
            ? `"${s.replace(/"/g, '""')}"`
            : s;
        };

        const lines = [fn.join(",")];
        for (const row of data) {
          lines.push(fn.map((f) => esc(row[f])).join(","));
        }
        content = lines.join("\n");
        filename = `${fname}.csv`;
      } else {
        content = JSON.stringify(data, null, 2);
        filename = `${fname}.json`;
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            filename,
            format,
            row_count: data.length,
            content,
          }, null, 2),
        }],
      };
    },
  );

  // =========================================================================
  // DISCOVERY TOOL — free
  // =========================================================================

  server.tool(
    "buzdev_discover_extensions",
    `Discover complementary MCP servers, skills, and tools for tasks beyond this server's scope: rendering pitch decks, sending emails, verifying emails, competitive intelligence, social engagement.

Parameters:
- task: What you want to do next: render_pitch_deck, send_outreach_emails, verify_emails, competitive_intelligence, social_engagement

Free tool — no auth required.`,
    {
      task: z.string().min(1),
    },
    async (args) => {
      const task = args.task.toLowerCase().trim();
      if (EXTENSION_REGISTRY[task]) {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              task,
              description: EXTENSION_REGISTRY[task].description,
              extensions: EXTENSION_REGISTRY[task].extensions,
              count: EXTENSION_REGISTRY[task].extensions.length,
            }, null, 2),
          }],
        };
      }

      const matches: Array<Record<string, unknown>> = [];
      for (const [name, data] of Object.entries(EXTENSION_REGISTRY)) {
        if (task.includes(name) || name.includes(task)) {
          matches.push({
            task: name,
            description: data.description,
            extensions: data.extensions,
            count: data.extensions.length,
          });
        }
      }

      if (matches.length > 0) {
        return { content: [{ type: "text", text: JSON.stringify({ query: task, matches }, null, 2) }] };
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            query: task,
            error: `No match for '${task}'`,
            available_tasks: Object.keys(EXTENSION_REGISTRY).map((k) => ({
              task: k,
              description: EXTENSION_REGISTRY[k].description,
            })),
          }, null, 2),
        }],
      };
    },
  );

  return server;
}

// ---------------------------------------------------------------------------
// Worker entry point
// ---------------------------------------------------------------------------

export default {
  async fetch(request: Request, env: Record<string, string | undefined>, ctx: unknown): Promise<Response> {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // Health check endpoint
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(JSON.stringify({
        service: "buzdev-outreach",
        status: "ok",
        mcp_endpoint: "/mcp",
        tools: 8,
        auth: env.BUZDEV_API_KEY ? "Bearer token required (BUZDEV_API_KEY configured)" : "No auth required (open access)",
      }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    // Optional auth check
    const expectedKey = env.BUZDEV_API_KEY;
    if (expectedKey) {
      const token = extractBearerToken(request);
      if (!token || !validateToken(token, expectedKey)) {
        return new Response(JSON.stringify({
          error: "Missing or invalid authentication",
          message: "Provide your BuzDev API key as: Authorization: Bearer <key>",
        }), {
          status: 401,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        });
      }
    }

    const server = createServer();

    const { createMcpHandler } = await import("agents/mcp");
    const handler = createMcpHandler(() => server as never, {
      route: "/mcp",
    });

    return handler(request, env as never, ctx as never);
  },
} satisfies ExportedHandler;