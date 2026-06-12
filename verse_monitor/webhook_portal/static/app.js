(function(){
'use strict';

var API_BASE = '/api/v1';
var state = { view: 'home', apiKey: null, sub: null };

// ── HELPERS ──
function $(sel){ return document.querySelector(sel); }
function esc(s){
  var d = document.createElement('div');
  d.textContent = String(s == null ? '' : s);
  return d.innerHTML;
}
function showToast(msg, type){
  var c = $('#toasts'); if(!c) return;
  var t = document.createElement('div');
  t.className = 'toast toast-' + (type||'success');
  t.innerHTML = '<span>' + (type==='error'?'❌':'✅') + '</span><span>' + msg + '</span>';
  c.appendChild(t);
  setTimeout(function(){ t.style.opacity='0'; t.style.transform='translateX(16px)'; setTimeout(function(){ t.remove(); }, 300); }, 4000);
}

// ── DATA ──
var EVENT_TYPES = [
  { id: 'roadmap_card_added',    label: 'Cards Added',    desc: 'New cards appearing on the roadmap' },
  { id: 'roadmap_card_released', label: 'Released',       desc: 'Cards moving to a LIVE patch' },
  { id: 'roadmap_card_delayed',  label: 'Delayed',        desc: 'Cards pushed to a later patch' },
  { id: 'roadmap_card_removed',  label: 'Removed',        desc: 'Cards removed from the roadmap' },
  { id: 'roadmap_card_updated',  label: 'Updated',        desc: 'Card details changed (title, description, patch)' },
  { id: 'patch_notes_live',      label: 'Patch Notes',    desc: 'Official LIVE patch notes publication' },
  { id: 'comm_link_published',   label: 'Comm-Links',     desc: 'RSI Comm-Links (weekly reports, sneak peeks)' },
  { id: 'devtracker_post',       label: 'Dev Posts',      desc: 'Individual developer posts on the progress tracker' },
  { id: 'twisc_published',       label: 'This Week in SC', desc: 'Weekly newsletter "This Week in Star Citizen"' },
  { id: 'monthly_report',        label: 'Monthly Reports', desc: 'Monthly production reports' },
];

var PRIORITIES = [
  { id: 'LOW',      emoji: '🔵', label: 'All',         desc: 'Every alert regardless of importance' },
  { id: 'MEDIUM',   emoji: '🟡', label: 'Standard',    desc: 'Skip minor updates, keep meaningful changes' },
  { id: 'HIGH',     emoji: '🟠', label: 'Major only',  desc: 'Only significant events (releases, delays, patches)' },
  { id: 'CRITICAL', emoji: '🔴', label: 'Critical',   desc: 'Only critical alerts (major releases, breaking changes)' },
];

var CATEGORIES = [
  { id: '',         label: 'All Categories',  desc: 'No category filter — receive everything' },
  { id: 'ship',     label: 'Ships',          desc: 'Ship-related changes, stats, releases' },
  { id: 'gameplay', label: 'Gameplay',       desc: 'Game mechanics, systems, FPS, missions' },
  { id: 'tech',     label: 'Technology',     desc: 'Engine, rendering, netcode, performance' },
  { id: 'event',    label: 'Events',         desc: 'In-game events, IAE, Invictus, patches' },
  { id: 'lore',     label: 'Lore',           desc: 'Galactapedia, Comm-Links, universe news' },
];

// ── RENDER ──
function render(){
  var app = $('#app'); if(!app) return;
  app.innerHTML = '';
  if (state.view === 'register') renderRegister(app);
  else if (state.view === 'dashboard') renderDashboard(app);
  else renderHome(app);
}

// ── HOME ──
function renderHome(app){
  app.innerHTML = '';

  // ── HERO ──
  var hero = document.createElement('div');
  hero.className = 'hero';
  hero.innerHTML =
    '<div class="hero-badge">Star Citizen Intelligence Platform</div>' +
    '<h1 class="hero-title">Real-time Star Citizen&nbsp;intelligence, delivered&nbsp;anywhere</h1>' +
    '<p class="hero-subtitle">Track roadmap changes, patch notes, Comm-Links, and dev posts — delivered to your Discord, Slack, Telegram, or webhook endpoint in real-time.</p>' +
    '<div class="hero-cta">' +
      '<button class="btn btn-primary btn-xl" id="hero-cta">Create Free Subscription</button>' +
      '<button class="btn btn-ghost btn-xl" id="hero-mcp">Use as MCP Tool →</button>' +
    '</div>' +
    '<span class="hero-cta-hint">Free · No account needed · Takes 30 seconds</span>';
  app.appendChild(hero);
  $('#hero-cta').addEventListener('click', function(){ state.view='register'; render(); window.scrollTo({top:0,behavior:'smooth'}); });
  $('#hero-mcp').addEventListener('click', function(){ document.getElementById('mcp').scrollIntoView({behavior:'smooth'}); });

  // ── PLATFORMS ──
  var platforms = document.createElement('div');
  platforms.className = 'container';
  platforms.innerHTML =
    '<div class="section-label">Delivered to your platform</div>' +
    '<div class="platforms-row">' +
      '<span class="plogo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.36.698.772 1.362 1.225 1.993a19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg> Discord</span>' +
      '<span class="plogo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52z" fill="#E01E5A"/><path d="M6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" fill="#E01E5A"/><path d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834z" fill="#36C5F0"/><path d="M8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" fill="#36C5F0"/><path d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834z" fill="#2EB67D"/><path d="M17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" fill="#2EB67D"/><path d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52z" fill="#ECB22E"/><path d="M15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#ECB22E"/></svg> Slack</span>' +
      '<span class="plogo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#26A5E4"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg> Telegram</span>' +
      '<span class="plogo"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#8a8f98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg> Webhook</span>' +
    '</div>';
  app.appendChild(platforms);

  // ── FEATURES ──
  var featuresSection = document.createElement('div');
  featuresSection.className = 'container section';
  featuresSection.id = 'features';
  featuresSection.innerHTML =
    '<div class="section-label">Features</div>' +
    '<h2 class="section-title">Everything you need to stay informed</h2>' +
    '<p class="section-subtitle">Monitor every aspect of Star Citizen development with granular filters and real-time delivery.</p>' +
    '<div class="features-grid">' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><h3>Real-time Monitoring</h3><p>Polls RSI sources every few minutes for changes. Detect roadmap updates, new Comm-Links, and dev posts as they happen.</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div><h3>Smart Filtering</h3><p>Keywords, categories, event types, and priority levels. Only receive alerts that match what you actually care about.</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div><h3>Multi-Platform Delivery</h3><p>Discord, Slack, Telegram, or raw JSON webhooks. Native formatting for each platform with embeds and rich content.</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div><h3>Vector Search (Qdrant)</h3><p>Semantic search across ingested Star Citizen data. Ships, lore, equipment, and more — searchable via natural language.</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div><h3>MCP Integration</h3><p>Use Verse Monitor as an MCP tool in Claude Code, Cursor, and other MCP-compatible clients. Search, research, and write.</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div><h3>Delivery Dashboard</h3><p>Track deliveries, failures, and rate limits per subscription. Test pings and full configuration management.</p></div>' +
    '</div>';
  app.appendChild(featuresSection);

  // ── MCP SECTION ──
  var mcpSection = document.createElement('div');
  mcpSection.className = 'section mcp-section';
  mcpSection.id = 'mcp';
  mcpSection.innerHTML =
    '<div class="container"><div class="mcp-grid">' +
      '<div class="mcp-content">' +
        '<div class="section-label">MCP Integration</div>' +
        '<h3>Use Verse Monitor as an MCP Tool</h3>' +
        '<p>Verse Monitor exposes a Model Context Protocol server that lets AI assistants search Star Citizen data, summarize patch notes, and help you write articles — all from your favorite MCP-compatible client.</p>' +
        '<ul class="mcp-use-cases">' +
          '<li>Search ships, lore, and equipment with natural language</li>' +
          '<li>Summarize patch notes and roadmap changes</li>' +
          '<li>Research community discussions and Comm-Links</li>' +
          '<li>Draft articles and community updates with sourced citations</li>' +
        '</ul>' +
      '</div>' +
      '<div><div class="code-block">' +
        '<div class="code-block-header"><span class="code-block-lang">mcp.json</span><button class="code-block-copy" id="mcp-copy-btn">Copy</button></div>' +
        '<pre><span class="punct">{</span>\n  <span class="key">"mcpServers"</span><span class="punct">:</span> <span class="punct">{</span>\n    <span class="key">"verse-monitor"</span><span class="punct">:</span> <span class="punct">{</span>\n      <span class="key">"url"</span><span class="punct">:</span> <span class="str">"https://verse-monitor.aperture-agency.org/mcp"</span>\n    <span class="punct">}</span>\n  <span class="punct">}</span>\n<span class="punct">}</span></pre>' +
      '</div></div>' +
    '</div></div>';
  app.appendChild(mcpSection);
  $('#mcp-copy-btn').addEventListener('click', function(){
    navigator.clipboard.writeText('{\n  "mcpServers": {\n    "verse-monitor": {\n      "url": "https://verse-monitor.aperture-agency.org/mcp"\n    }\n  }\n}');
    showToast('Configuration copied!');
  });

  // ── DATA SCOPE DISCLAIMER ──
  var disclaimerSection = document.createElement('div');
  disclaimerSection.className = 'container section';
  disclaimerSection.id = 'sources';
  disclaimerSection.innerHTML =
    '<div class="section-label">Data Scope & Coverage</div>' +
    '<h2 class="section-title">Transparent about what\'s available</h2>' +
    '<p class="section-subtitle">We believe in honesty about data coverage. Here\'s what you can search today and what\'s coming.</p>' +
    '<div class="disclaimer-card">' +
      '<h3><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg> Current Coverage</h3>' +
      '<p><strong>Available now:</strong> Ship specifications, Galactapedia lore entries, Comm-Links, and equipment/items data from the Star Citizen Wiki API. Roadmap changes, patch notes, and dev tracker posts via the alert system.</p>' +
      '<p><strong>Improving continuously:</strong> We\'re actively ingesting more sources and expanding coverage. New data types and deeper historical content are added on a rolling basis.</p>' +
      '<p><strong>Missing something?</strong> If you need specific data that isn\'t covered yet, reach out — we prioritize ingestion based on community demand.</p>' +
      '<div class="disclaimer-links"><a href="https://github.com/Aperture-Science-Technology/verse-mcp/issues" target="_blank" rel="noopener">Request a source →</a><a href="mailto:contact@aperture-agency.org">Contact us →</a></div>' +
    '</div>';
  app.appendChild(disclaimerSection);

  // ── EVENT TYPES ──
  var eventSection = document.createElement('div');
  eventSection.className = 'container section';
  eventSection.innerHTML =
    '<div class="section-label">Monitored Event Types</div>' +
    '<h2 class="section-title">Comprehensive coverage</h2>' +
    '<p class="section-subtitle">Every major source of Star Citizen development updates, monitored and filtered for you.</p>' +
    '<div class="event-chips">' +
      '<span class="event-chip">Roadmap Changes</span><span class="event-chip">Patch Notes</span><span class="event-chip">Comm-Links</span><span class="event-chip">Dev Tracker Posts</span><span class="event-chip">This Week in SC</span><span class="event-chip">Monthly Reports</span>' +
    '</div>';
  app.appendChild(eventSection);

  // ── PRICING ──
  var pricingSection = document.createElement('div');
  pricingSection.className = 'container section';
  pricingSection.id = 'pricing';
  pricingSection.innerHTML =
    '<div class="section-label">Pricing</div>' +
    '<h2 class="section-title">Start free, scale when you need to</h2>' +
    '<p class="section-subtitle">No credit card required. Get started in under a minute.</p>' +
    '<div class="pricing-grid">' +
      '<div class="pricing-card pricing-card-featured">' +
        '<div class="pricing-name">Free</div><div class="pricing-price">$0<span>/month</span></div>' +
        '<div class="pricing-desc">Everything you need to stay on top of Star Citizen development.</div>' +
        '<ul class="pricing-features"><li>Unlimited webhook subscriptions</li><li>All event types and filters</li><li>30 alerts/hour per subscription</li><li>Discord, Slack, Telegram, Webhook</li><li>Delivery dashboard & stats</li></ul>' +
        '<button class="btn btn-primary btn-full" id="pricing-free-btn">Get Started — Free</button>' +
      '</div>' +
      '<div class="pricing-card">' +
        '<div class="pricing-name">Pro</div><div class="pricing-price">TBD<span>/month</span></div>' +
        '<div class="pricing-desc">For power users and communities that need more.</div>' +
        '<ul class="pricing-features"><li>Higher rate limits</li><li>Priority support</li><li>Custom source ingestion</li><li>Advanced filtering rules</li><li>API access</li></ul>' +
        '<button class="btn btn-secondary btn-full" disabled>Coming Soon</button>' +
        '<div class="pricing-coming">Planned for Q3 2026</div>' +
      '</div>' +
    '</div>';
  app.appendChild(pricingSection);
  $('#pricing-free-btn').addEventListener('click', function(){ state.view='register'; render(); window.scrollTo({top:0,behavior:'smooth'}); });

  // ── CTA ──
  var ctaSection = document.createElement('div');
  ctaSection.className = 'container section';
  ctaSection.style.textAlign = 'center';
  ctaSection.innerHTML = '<h2 class="section-title">Ready to stay informed?</h2><p class="section-subtitle">Set up your first webhook subscription in under a minute. No account required.</p><button class="btn btn-primary btn-xl" id="cta-bottom-btn">Create Free Subscription</button>';
  app.appendChild(ctaSection);
  $('#cta-bottom-btn').addEventListener('click', function(){ state.view='register'; render(); window.scrollTo({top:0,behavior:'smooth'}); });
}

function goDashboard(){
  var key = ($('#home-key-input')||{}).value || ($('#key-input')||{}).value;
  if(key && key.trim()){ state.apiKey = key.trim(); state.view = 'dashboard'; loadDashboard(key.trim()); }
}

// ── REGISTER ──
function renderRegister(app){
  var wrap = document.createElement('div');
  wrap.className = 'container';
  wrap.style.maxWidth = '640px';
  wrap.style.paddingTop = '48px';
  wrap.style.paddingBottom = '48px';

  var back = document.createElement('a');
  back.href = '#'; back.className = 'back-link'; back.textContent = '← Back to home';
  back.addEventListener('click', function(e){ e.preventDefault(); state.view='home'; render(); });
  wrap.appendChild(back);

  var header = document.createElement('div');
  header.className = 'form-page-header';
  header.innerHTML = '<h2>🚀 New Subscription</h2><p>Configure your webhook to receive filtered Star Citizen alerts.</p>';
  wrap.appendChild(header);

  var card = document.createElement('div');
  card.className = 'card';
  card.id = 'register-card';

  var alertBox = document.createElement('div');
  alertBox.className = 'alert alert-error';
  alertBox.style.display = 'none';
  alertBox.innerHTML = '<span class="icon">⚠️</span><span id="alert-msg"></span>';
  card.appendChild(alertBox);
  function showAlert(msg){ $('#alert-msg').textContent = msg; alertBox.style.display = 'flex'; }

  // 1. Name
  var g1 = document.createElement('div'); g1.className = 'form-group';
  g1.innerHTML = '<div class="section-label-form"><span class="section-num">1</span><label>Project / Channel Name</label></div><input class="form-control" id="f-name" placeholder="e.g. StarCitizen FR">';
  card.appendChild(g1);

  // 2. Webhook URL
  var g2 = document.createElement('div'); g2.className = 'form-group';
  g2.innerHTML = '<div class="section-label-form"><span class="section-num">2</span><label>Webhook URL</label></div><input class="form-control" id="f-url" placeholder="https://discord.com/api/webhooks/…"><div class="form-hint">Discord, Slack, Telegram Bot API, or any HTTPS endpoint that accepts JSON POST.</div>';
  card.appendChild(g2);

  // 3. Output Format
  var g3 = document.createElement('div'); g3.className = 'form-group';
  g3.innerHTML = '<div class="section-label-form"><span class="section-num">3</span><label>Output Format</label></div>';
  var fmtGrid = document.createElement('div'); fmtGrid.className = 'format-grid';
  var formats = [
    { id: 'discord',  icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.36.698.772 1.362 1.225 1.993a19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>', label: 'Discord' },
    { id: 'slack',    icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22"><path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52z" fill="#E01E5A"/><path d="M6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" fill="#E01E5A"/><path d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834z" fill="#36C5F0"/><path d="M8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" fill="#36C5F0"/><path d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834z" fill="#2EB67D"/><path d="M17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" fill="#2EB67D"/><path d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52z" fill="#ECB22E"/><path d="M15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#ECB22E"/></svg>', label: 'Slack' },
    { id: 'telegram', icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="#26A5E4"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.96 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>', label: 'Telegram' },
    { id: 'generic',  icon: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#8a8f98" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>', label: 'JSON' },
  ];
  var selectedFormat = 'discord';
  formats.forEach(function(f){
    var fc = document.createElement('div');
    fc.className = 'format-card' + (f.id === 'discord' ? ' selected' : '');
    fc.dataset.id = f.id;
    fc.innerHTML = '<div class="check">✓</div><div class="icon">' + f.icon + '</div><div class="label">' + f.label + '</div>';
    fc.addEventListener('click', function(){
      fmtGrid.querySelectorAll('.format-card').forEach(function(c){ c.classList.remove('selected'); });
      fc.classList.add('selected'); selectedFormat = f.id;
    });
    fmtGrid.appendChild(fc);
  });
  g3.appendChild(fmtGrid);
  var fmtHint = document.createElement('div');
  fmtHint.className = 'form-hint';
  fmtHint.textContent = 'Discord, Slack, Telegram (Bot API), or any HTTPS endpoint that accepts JSON POST. For other platforms, use the Generic JSON format with a bridge service (Zapier, Make, n8n).';
  g3.parentNode.insertBefore(fmtHint, g3.nextSibling);
  card.appendChild(g3);

  // 4. Priority
  var g4 = document.createElement('div'); g4.className = 'form-group';
  g4.innerHTML = '<div class="section-label-form"><span class="section-num">4</span><label>Minimum Priority</label></div><div class="form-hint">Only receive alerts at or above this level.</div>';
  var priSel = document.createElement('div'); priSel.className = 'priority-selector';
  var selectedPriority = 'MEDIUM';
  PRIORITIES.forEach(function(p){
    var po = document.createElement('div');
    po.className = 'priority-option' + (p.id === 'MEDIUM' ? ' selected' : '');
    po.dataset.id = p.id;
    po.innerHTML = '<div class="emoji">' + p.emoji + '</div><div class="label">' + p.label + '</div><div class="sublabel">' + p.desc + '</div>';
    po.addEventListener('click', function(){
      priSel.querySelectorAll('.priority-option').forEach(function(o){ o.classList.remove('selected'); });
      po.classList.add('selected'); selectedPriority = p.id;
    });
    priSel.appendChild(po);
  });
  g4.appendChild(priSel);
  card.appendChild(g4);

  // 5. Event Types
  var g5 = document.createElement('div'); g5.className = 'form-group';
  g5.innerHTML = '<div class="section-label-form"><span class="section-num">5</span><label>Event Types</label></div><div class="form-hint">Select which types of alerts to receive. Leave empty to receive all types.</div>';
  var chipGrid = document.createElement('div'); chipGrid.className = 'chip-grid';
  var selectedTypes = [];
  EVENT_TYPES.forEach(function(t){
    var chip = document.createElement('div');
    chip.className = 'chip'; chip.dataset.id = t.id;
    chip.innerHTML = '<span>' + t.label + '</span>';
    chip.title = t.desc;
    chip.addEventListener('click', function(){
      chip.classList.toggle('selected');
      var idx = selectedTypes.indexOf(t.id);
      if(idx >= 0) selectedTypes.splice(idx, 1); else selectedTypes.push(t.id);
    });
    chipGrid.appendChild(chip);
  });
  g5.appendChild(chipGrid);
  card.appendChild(g5);

  // 6. Keywords
  var g6 = document.createElement('div'); g6.className = 'form-group';
  g6.innerHTML = '<div class="section-label-form"><span class="section-num">6</span><label>Keywords <span style="color:var(--text4);font-weight:400">(optional)</span></label></div><div class="form-hint">Only alerts containing at least one of these words will be sent. Case-insensitive.</div>';
  var tagsWrap = document.createElement('div'); tagsWrap.className = 'tags-input'; tagsWrap.id = 'tags-wrap';
  var tagsInput = document.createElement('input'); tagsInput.placeholder = 'Type a word, press Enter';
  var keywords = [];
  function renderTags(){
    tagsWrap.querySelectorAll('.tag').forEach(function(t){ t.remove(); });
    keywords.forEach(function(k){
      var tag = document.createElement('span'); tag.className = 'tag';
      tag.innerHTML = k + '<span class="remove">×</span>';
      tag.querySelector('.remove').addEventListener('click', function(){ keywords.splice(keywords.indexOf(k), 1); renderTags(); });
      tagsWrap.insertBefore(tag, tagsInput);
    });
  }
  tagsInput.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){ e.preventDefault(); var v = tagsInput.value.trim(); if(v && keywords.indexOf(v) < 0){ keywords.push(v); tagsInput.value = ''; renderTags(); } }
  });
  tagsWrap.appendChild(tagsInput);
  g6.appendChild(tagsWrap);
  card.appendChild(g6);

  // 7. Category
  var g7 = document.createElement('div'); g7.className = 'form-group';
  g7.innerHTML = '<div class="section-label-form"><span class="section-num">7</span><label>Category <span style="color:var(--text4);font-weight:400">(optional)</span></label></div><div class="form-hint">Filter alerts by broad topic category.</div>';
  var selCat = document.createElement('select'); selCat.className = 'form-control'; selCat.id = 'f-cat';
  CATEGORIES.forEach(function(c){
    var opt = document.createElement('option'); opt.value = c.id; opt.textContent = c.label + (c.desc ? ' — ' + c.desc : '');
    selCat.appendChild(opt);
  });
  g7.appendChild(selCat);
  card.appendChild(g7);

  // 8. Rate Limit
  var g8 = document.createElement('div'); g8.className = 'form-group';
  g8.innerHTML = '<div class="section-label-form"><span class="section-num">8</span><label>Rate Limit</label></div><div class="form-hint">Maximum alerts per hour. Helps prevent channel spam during busy periods.</div>';
  var rateRow = document.createElement('div'); rateRow.style.cssText = 'display:flex;align-items:center;gap:10px;';
  var rateInput = document.createElement('input'); rateInput.className = 'form-control'; rateInput.id = 'f-rate';
  rateInput.type = 'number'; rateInput.value = '30'; rateInput.min = '1'; rateInput.max = '100'; rateInput.style.width = '80px';
  var rateLabel = document.createElement('span'); rateLabel.style.cssText = 'color:var(--text2);font-size:.88em;'; rateLabel.textContent = 'alerts / hour';
  rateRow.appendChild(rateInput); rateRow.appendChild(rateLabel);
  g8.appendChild(rateRow);
  card.appendChild(g8);

  // Submit
  var submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary btn-lg btn-full';
  submitBtn.textContent = '🚀 Create Subscription';
  submitBtn.addEventListener('click', function(){
    var name = ($('#f-name')||{}).value||'';
    var url  = ($('#f-url')||{}).value||'';
    if(!name.trim() || !url.trim()){ showAlert('Name and webhook URL are required.'); return; }
    if(!url.trim().startsWith('https://')){ showAlert('Webhook URL must start with https://'); return; }
    submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Creating…';
    api('/subscriptions', {
      method: 'POST',
      body: JSON.stringify({ name: name.trim(), webhook_url: url.trim(), format: selectedFormat, priority_min: selectedPriority, event_types: selectedTypes, keywords: keywords, category: ($('#f-cat')||{}).value||null, rate_limit: parseInt(($('#f-rate')||{}).value)||30 })
    }).then(function(resp){
      submitBtn.disabled = false; submitBtn.textContent = '🚀 Create Subscription';
      if(resp.status === 201){
        window.history.replaceState({}, '', '?key=' + resp.data.api_key);
        state.apiKey = resp.data.api_key; state.view = 'dashboard';
        loadDashboard(resp.data.api_key);
      } else { showAlert((resp.data||{}).detail || 'Failed to create subscription'); }
    }).catch(function(){ submitBtn.disabled = false; submitBtn.textContent = '🚀 Create Subscription'; showAlert('Network error. Please try again.'); });
  });
  card.appendChild(submitBtn);
  wrap.appendChild(card);
  app.appendChild(wrap);
}

// ── DASHBOARD ──
function renderDashboard(app){
  var s = state.sub;
  if(!s){ app.innerHTML='<div class="loading"><div class="spinner"></div><span>Loading dashboard…</span></div>'; return; }

  var header = document.createElement('div'); header.className = 'container';
  header.innerHTML = '<div class="dash-header"><h1>📊 ' + esc(s.name) + '</h1><span class="dash-badge ' + (s.active ? 'dash-badge-active' : 'dash-badge-inactive') + '"><span class="dash-badge-dot"></span>' + (s.active ? 'Active' : 'Inactive') + '</span></div>';
  app.appendChild(header);

  // API Key
  var keyCard = document.createElement('div'); keyCard.className = 'container';
  keyCard.innerHTML = '<div class="card"><div class="card-title">🔑 API Key</div><div class="card-desc">Keep this key secret. Use it to access this dashboard.</div><div class="key-box"><span class="key">' + esc(s.api_key||state.apiKey) + '</span><button class="btn btn-secondary btn-sm" id="copy-key-btn">📋 Copy</button></div></div>';
  app.appendChild(keyCard);
  $('#copy-key-btn').addEventListener('click', function(){ navigator.clipboard.writeText(state.apiKey); showToast('API key copied!'); });

  // Stats
  var statsCard = document.createElement('div'); statsCard.className = 'container';
  statsCard.innerHTML = '<div class="card"><div class="card-title">📈 Delivery Stats</div><div class="stats-grid">' +
    '<div class="stat-card"><div class="value">' + s.total_deliveries + '</div><div class="label">Delivered</div></div>' +
    '<div class="stat-card"><div class="value" style="color:' + (s.failure_count>0?'var(--red)':'var(--green)') + '">' + s.failure_count + '</div><div class="label">Failures</div></div>' +
    '<div class="stat-card"><div class="value">' + s.rate_limit + '/hr</div><div class="label">Rate Limit</div></div>' +
    '</div></div>';
  app.appendChild(statsCard);

  // Config
  var configCard = document.createElement('div'); configCard.className = 'container';
  var ul = document.createElement('ul'); ul.className = 'config-list';
  function li(k,v){ var node = document.createElement('li'); node.innerHTML = '<span class="key">' + k + '</span><span class="value">' + v + '</span>'; return node; }
  ul.appendChild(li('Priority', '≥ ' + esc(s.priority_min)));
  ul.appendChild(li('Event Types', (s.event_types && s.event_types.length) ? esc(s.event_types.join(', ')) : 'All'));
  ul.appendChild(li('Keywords', (s.keywords && s.keywords.length) ? esc(s.keywords.join(', ')) : 'None'));
  ul.appendChild(li('Category', esc(s.category) || 'All'));
  ul.appendChild(li('Format', esc(s.format)));
  ul.appendChild(li('Created', new Date(s.created_at).toLocaleString()));
  ul.appendChild(li('Last Delivery', s.last_delivery ? new Date(s.last_delivery).toLocaleString() : 'Never'));
  configCard.innerHTML = '<div class="card"><div class="card-title">⚙️ Configuration</div></div>';
  configCard.querySelector('.card').appendChild(ul);
  app.appendChild(configCard);

  // Actions
  var actionsCard = document.createElement('div'); actionsCard.className = 'container';
  actionsCard.innerHTML = '<div class="card"><div class="card-title">Actions</div><div class="actions">' +
    '<button class="btn btn-secondary btn-sm" id="test-ping-btn">🧪 Test Ping</button>' +
    '<button class="btn btn-danger btn-sm" id="delete-sub-btn">🗑️ Delete</button>' +
    '</div></div>';
  app.appendChild(actionsCard);
  $('#test-ping-btn').addEventListener('click', function(){
    var btn = $('#test-ping-btn'); btn.disabled = true;
    api('/subscriptions/' + state.apiKey + '/test', { method: 'POST' })
      .then(function(){ showToast('Test ping sent!'); btn.disabled = false; })
      .catch(function(){ showToast('Failed to send test', 'error'); btn.disabled = false; });
  });
  $('#delete-sub-btn').addEventListener('click', function(){
    showModal('Delete Subscription', 'Are you sure? This will permanently stop all alerts and cannot be undone.', function(){
      api('/subscriptions/' + state.apiKey, { method: 'DELETE' }).then(function(){
        window.history.replaceState({}, '', '/');
        state = { view: 'home', apiKey: null, sub: null };
        render(); showToast('Subscription deleted');
      });
    });
  });
}

// ── API ──
function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  return fetch(API_BASE + path, opts).then(function(r){
    return r.json().then(function(d){ return { status: r.status, data: d }; });
  });
}

function loadDashboard(key){
  api('/subscriptions/' + key).then(function(resp){
    if(resp.status === 200){
      state.sub = resp.data; state.apiKey = key; render();
    } else {
      state.view = 'home';
      var app = $('#app'); app.innerHTML = '';
      var err = document.createElement('div'); err.className = 'alert alert-error'; err.innerHTML = '<span class="icon">⚠️</span><span>Invalid API key. Subscription not found.</span>';
      app.appendChild(err);
      var back = document.createElement('p');
      var backLink = document.createElement('a'); backLink.href = '#'; backLink.textContent = '← Back to home';
      backLink.addEventListener('click', function(e){ e.preventDefault(); state.view = 'home'; render(); });
      back.appendChild(backLink);
      app.appendChild(back);
    }
  });
}

// ── MODAL ──
function showModal(title, body, onConfirm){
  var overlay = document.createElement('div'); overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal"><h3>' + title + '</h3><p>' + body + '</p><div class="modal-actions"><button class="btn btn-secondary btn-sm" id="modal-cancel">Cancel</button><button class="btn btn-danger btn-sm" id="modal-confirm">Delete</button></div></div>';
  document.body.appendChild(overlay);
  var cancelBtn = overlay.querySelector('#modal-cancel');
  var confirmBtn = overlay.querySelector('#modal-confirm');
  if(cancelBtn) cancelBtn.addEventListener('click', function(){ overlay.remove(); });
  if(confirmBtn) confirmBtn.addEventListener('click', function(){ overlay.remove(); onConfirm(); });
  overlay.addEventListener('click', function(e){ if(e.target === overlay) overlay.remove(); });
}

// ── API KEY MODAL ──
function showApiKeyModal(){
  var overlay = document.createElement('div');
  overlay.className = 'api-key-overlay';
  overlay.innerHTML =
    '<div class="api-key-modal">' +
      '<h3>🔑 Access Dashboard</h3>' +
      '<p>Enter your API key to view your subscription details, delivery stats, and configuration.</p>' +
      '<input class="form-control" id="api-key-input" placeholder="Enter your API key" type="password" autocomplete="off">' +
      '<div class="modal-actions">' +
        '<button class="btn btn-secondary btn-sm" id="api-key-cancel">Cancel</button>' +
        '<button class="btn btn-primary btn-sm" id="api-key-submit">Access</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);
  var input = overlay.querySelector('#api-key-input');
  input.focus();
  overlay.querySelector('#api-key-cancel').addEventListener('click', function(){ overlay.remove(); });
  overlay.querySelector('#api-key-submit').addEventListener('click', submitApiKey);
  input.addEventListener('keydown', function(e){ if(e.key === 'Enter') submitApiKey(); });
  overlay.addEventListener('click', function(e){ if(e.target === overlay) overlay.remove(); });
  function submitApiKey(){
    var key = input.value.trim();
    if(!key){ return; }
    overlay.remove();
    state.apiKey = key; state.view = 'dashboard'; loadDashboard(key);
  }
}

// ── NAV ──
$('#nav-home').addEventListener('click', function(e){
  e.preventDefault(); window.history.replaceState({},'','/');
  state = {view:'home',apiKey:null,sub:null}; render();
});
$('#nav-get-started').addEventListener('click', function(e){
  e.preventDefault(); state.view='register'; render(); window.scrollTo({top:0,behavior:'smooth'});
});
$('#nav-dash-btn').addEventListener('click', function(){
  showApiKeyModal();
});

// ── INIT ──
var params = new URLSearchParams(window.location.search);
var key = params.get('key');
if(key){ state.apiKey=key; state.view='dashboard'; loadDashboard(key); }
else { render(); }

})();
