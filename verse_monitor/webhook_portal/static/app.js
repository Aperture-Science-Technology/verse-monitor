(function(){
'use strict';

var API_BASE = '/api/v1';
var state = { view: 'home', apiKey: null, sub: null };
var _t = I18N.t;

// ── ROUTER ──
var VIEW_HASH = { home: '#home', register: '#register', docs: '#docs', dashboard: '#dashboard' };
function navTo(view) {
  state.view = view || 'home';
  window.location.hash = VIEW_HASH[state.view] || '#home';
  render();
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function getViewFromHash() {
  var h = window.location.hash;
  for (var v in VIEW_HASH) {
    if (VIEW_HASH[v] === h) return v;
  }
  return 'home';
}

// ── HELPERS ──
function $(sel){ return document.querySelector(sel); }
function esc(s){
  var d = document.createElement('div');
  d.textContent = String(s == null ? '' : s);
  return d.innerHTML;
}
function _(html){
  return html.replace(/\{\{t\.([^}]+)\}\}/g, function(m, key){ return I18N.t(key); });
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
  { id: 'roadmap_card_added',    label: _t('et.roadmap_card_added'),    desc: _t('etd.roadmap_card_added') },
  { id: 'roadmap_card_released', label: _t('et.roadmap_card_released'), desc: _t('etd.roadmap_card_released') },
  { id: 'roadmap_card_delayed',  label: _t('et.roadmap_card_delayed'),  desc: _t('etd.roadmap_card_delayed') },
  { id: 'roadmap_card_removed',  label: _t('et.roadmap_card_removed'),  desc: _t('etd.roadmap_card_removed') },
  { id: 'roadmap_card_updated',  label: _t('et.roadmap_card_updated'),  desc: _t('etd.roadmap_card_updated') },
  { id: 'patch_notes_live',      label: _t('et.patch_notes_live'),      desc: _t('etd.patch_notes_live') },
  { id: 'comm_link_published',   label: _t('et.comm_link_published'),   desc: _t('etd.comm_link_published') },
  { id: 'devtracker_post',       label: _t('et.devtracker_post'),       desc: _t('etd.devtracker_post') },
  { id: 'twisc_published',       label: _t('et.twisc_published'),       desc: _t('etd.twisc_published') },
  { id: 'monthly_report',        label: _t('et.monthly_report'),        desc: _t('etd.monthly_report') },
];

var PRIORITIES = [
  { id: 'LOW',      emoji: '🔵', label: _t('prio.LOW'),      desc: _t('priod.LOW') },
  { id: 'MEDIUM',   emoji: '🟡', label: _t('prio.MEDIUM'),   desc: _t('priod.MEDIUM') },
  { id: 'HIGH',     emoji: '🟠', label: _t('prio.HIGH'),     desc: _t('priod.HIGH') },
  { id: 'CRITICAL', emoji: '🔴', label: _t('prio.CRITICAL'), desc: _t('priod.CRITICAL') },
];

var CATEGORIES = [
  { id: '',         label: _t('cat.all'),      desc: _t('catd.all') },
  { id: 'ship',     label: _t('cat.ship'),     desc: _t('catd.ship') },
  { id: 'gameplay', label: _t('cat.gameplay'), desc: _t('catd.gameplay') },
  { id: 'tech',     label: _t('cat.tech'),     desc: _t('catd.tech') },
  { id: 'event',    label: _t('cat.event'),    desc: _t('catd.event') },
  { id: 'lore',     label: _t('cat.lore'),     desc: _t('catd.lore') },
];

// ── RENDER ──
function render(){
  var app = $('#app'); if(!app) return;
  app.innerHTML = '';
  if (state.view === 'register') renderRegister(app);
  else if (state.view === 'dashboard') renderDashboard(app);
  else if (state.view === 'docs') renderDocsView(app);
  else renderHome(app);
  // Apply i18n to static HTML elements with data-i18n
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    el.textContent = I18N.t(el.getAttribute('data-i18n'));
  });
}

// ── HOME ──
function renderHome(app){
  app.innerHTML = '';

  // ── HERO ──
  var hero = document.createElement('div');
  hero.className = 'hero';
  hero.innerHTML =
    '<div class="hero-badge">' + _t('hero.badge') + '</div>' +
    '<h1 class="hero-title">' + _t('hero.title') + '</h1>' +
    '<p class="hero-subtitle">' + _t('hero.subtitle') + '</p>' +
    '<div class="hero-cta">' +
      '<button class="btn btn-primary btn-xl" id="hero-cta">' + _t('hero.cta') + '</button>' +
      '<button class="btn btn-ghost btn-xl" id="hero-mcp">' + _t('hero.mcpBtn') + '</button>' +
    '</div>' +
    '<span class="hero-cta-hint">' + _t('hero.hint') + '</span>';
  app.appendChild(hero);
  $('#hero-cta').addEventListener('click', function(){ navTo('register'); });
  $('#hero-mcp').addEventListener('click', function(){ document.getElementById('mcp').scrollIntoView({behavior:'smooth'}); });

  // ── PLATFORMS ──
  var platforms = document.createElement('div');
  platforms.className = 'container';
  platforms.innerHTML =
    '<div class="section-label">' + _t('platforms.label') + '</div>' +
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
    '<div class="section-label">' + _t('features.label') + '</div>' +
    '<h2 class="section-title">' + _t('features.title') + '</h2>' +
    '<p class="section-subtitle">' + _t('features.subtitle') + '</p>' +
    '<div class="features-grid">' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div><h3>' + _t('features.0.title') + '</h3><p>' + _t('features.0.desc') + '</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div><h3>' + _t('features.1.title') + '</h3><p>' + _t('features.1.desc') + '</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div><h3>' + _t('features.2.title') + '</h3><p>' + _t('features.2.desc') + '</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div><h3>' + _t('features.3.title') + '</h3><p>' + _t('features.3.desc') + '</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div><h3>' + _t('features.4.title') + '</h3><p>' + _t('features.4.desc') + '</p></div>' +
      '<div class="feature-card"><div class="feature-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div><h3>' + _t('features.5.title') + '</h3><p>' + _t('features.5.desc') + '</p></div>' +
    '</div>';
  app.appendChild(featuresSection);

  // ── MCP SECTION ──
  var mcpSection = document.createElement('div');
  mcpSection.className = 'section mcp-section';
  mcpSection.id = 'mcp';
  mcpSection.innerHTML =
    '<div class="container"><div class="mcp-grid">' +
      '<div class="mcp-content">' +
        '<div class="section-label">' + _t('mcp.label') + '</div>' +
        '<h3>' + _t('mcp.title') + '</h3>' +
        '<p>' + _t('mcp.desc') + '</p>' +
        '<ul class="mcp-use-cases">' +
          '<li>' + _t('mcp.0') + '</li>' +
          '<li>' + _t('mcp.1') + '</li>' +
          '<li>' + _t('mcp.2') + '</li>' +
          '<li>' + _t('mcp.3') + '</li>' +
        '</ul>' +
      '</div>' +
      '<div><div class="code-block">' +
        '<div class="code-block-header"><span class="code-block-lang">mcp.json</span><button class="code-block-copy" id="mcp-copy-btn">' + _t('mcp.copy') + '</button></div>' +
        '<pre><span class="punct">{</span>\n  <span class="key">"mcpServers"</span><span class="punct">:</span> <span class="punct">{</span>\n    <span class="key">"verse-monitor"</span><span class="punct">:</span> <span class="punct">{</span>\n      <span class="key">"url"</span><span class="punct">:</span> <span class="str">"https://verse-monitor.aperture-agency.org/mcp"</span>\n    <span class="punct">}</span>\n  <span class="punct">}</span>\n<span class="punct">}</span></pre>' +
      '</div></div>' +
    '</div></div>';
  app.appendChild(mcpSection);
  $('#mcp-copy-btn').addEventListener('click', function(){
    navigator.clipboard.writeText('{\n  "mcpServers": {\n    "verse-monitor": {\n      "url": "https://verse-monitor.aperture-agency.org/mcp"\n    }\n  }\n}');
    showToast(_t('mcp.copied'));
  });

  // ── DATA SCOPE DISCLAIMER ──
  var disclaimerSection = document.createElement('div');
  disclaimerSection.className = 'container section';
  disclaimerSection.id = 'sources';
  disclaimerSection.innerHTML =
    '<div class="section-label">' + _t('scope.label') + '</div>' +
    '<h2 class="section-title">' + _t('scope.title') + '</h2>' +
    '<p class="section-subtitle">' + _t('scope.subtitle') + '</p>' +
    '<div class="disclaimer-card">' +
      '<h3><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg> ' + _t('scope.cardTitle') + '</h3>' +
      '<p><strong>' + _t('scope.available') + '</strong> ' + _t('scope.availableText') + '</p>' +
      '<p><strong>' + _t('scope.improving') + '</strong> ' + _t('scope.improvingText') + '</p>' +
      '<p><strong>' + _t('scope.missing') + '</strong> ' + _t('scope.missingText') + '</p>' +
      '<div class="disclaimer-links"><button class="footer-link-btn" id="sources-docs-link">' + _t('scope.docsLink') + '</button><a href="https://github.com/Aperture-Science-Technology/verse-monitor/issues" target="_blank" rel="noopener">' + _t('scope.requestLink') + '</a><a href="mailto:contact@aperture-agency.org">' + _t('scope.contactLink') + '</a></div>' +
    '</div>';
  app.appendChild(disclaimerSection);

  // ── EVENT TYPES ──
  var eventSection = document.createElement('div');
  eventSection.className = 'container section';
  eventSection.innerHTML =
    '<div class="section-label">' + _t('events.label') + '</div>' +
    '<h2 class="section-title">' + _t('events.title') + '</h2>' +
    '<p class="section-subtitle">' + _t('events.subtitle') + '</p>' +
    '<div class="event-chips">' +
      '<span class="event-chip">' + EVENT_TYPES[0].label + '</span><span class="event-chip">' + EVENT_TYPES[5].label + '</span><span class="event-chip">' + EVENT_TYPES[6].label + '</span><span class="event-chip">' + EVENT_TYPES[7].label + '</span><span class="event-chip">' + EVENT_TYPES[8].label + '</span><span class="event-chip">' + EVENT_TYPES[9].label + '</span>' +
    '</div>';
  app.appendChild(eventSection);

  // ── PRICING ──
  var pricingSection = document.createElement('div');
  pricingSection.className = 'container section';
  pricingSection.id = 'pricing';
  pricingSection.innerHTML =
    '<div class="section-label">' + _t('pricing.label') + '</div>' +
    '<h2 class="section-title">' + _t('pricing.title') + '</h2>' +
    '<p class="section-subtitle">' + _t('pricing.subtitle') + '</p>' +
    '<div class="pricing-grid">' +
      '<div class="pricing-card pricing-card-featured">' +
        '<div class="pricing-name">' + _t('pricing.free.name') + '</div><div class="pricing-price">$0<span>/month</span></div>' +
        '<div class="pricing-desc">' + _t('pricing.free.desc') + '</div>' +
        '<ul class="pricing-features"><li>' + _t('pricing.free.0') + '</li><li>' + _t('pricing.free.1') + '</li><li>' + _t('pricing.free.2') + '</li><li>' + _t('pricing.free.3') + '</li><li>' + _t('pricing.free.4') + '</li></ul>' +
        '<button class="btn btn-primary btn-full" id="pricing-free-btn">' + _t('pricing.free.btn') + '</button>' +
      '</div>' +
      '<div class="pricing-card">' +
        '<div class="pricing-name">' + _t('pricing.pro.name') + '</div><div class="pricing-price">TBD<span>/month</span></div>' +
        '<div class="pricing-desc">' + _t('pricing.pro.desc') + '</div>' +
        '<ul class="pricing-features"><li>' + _t('pricing.pro.0') + '</li><li>' + _t('pricing.pro.1') + '</li><li>' + _t('pricing.pro.2') + '</li><li>' + _t('pricing.pro.3') + '</li><li>' + _t('pricing.pro.4') + '</li></ul>' +
        '<button class="btn btn-secondary btn-full" disabled>' + _t('pricing.pro.btn') + '</button>' +
        '<div class="pricing-coming">' + _t('pricing.pro.coming') + '</div>' +
      '</div>' +
    '</div>';
  app.appendChild(pricingSection);
  $('#pricing-free-btn').addEventListener('click', function(){ navTo('register'); });

  // ── CTA ──
  var ctaSection = document.createElement('div');
  ctaSection.className = 'container section';
  ctaSection.style.textAlign = 'center';
  ctaSection.innerHTML = '<h2 class="section-title">' + _t('cta.title') + '</h2><p class="section-subtitle">' + _t('cta.subtitle') + '</p><button class="btn btn-primary btn-xl" id="cta-bottom-btn">' + _t('cta.btn') + '</button>';
  app.appendChild(ctaSection);
  $('#cta-bottom-btn').addEventListener('click', function(){ navTo('register'); });
}

// ── DOCS ──
function renderDocsContent(){
  return '<div class="docs-hero">' +
    '<a href="#" class="docs-back" id="docs-back-link">' + _t('docs.back') + '</a>' +
    '<h1 class="hero-title" style="font-size:2em">' + _t('docs.title') + '</h1>' +
    '<p class="hero-subtitle">' + _t('docs.subtitle') + '</p>' +
  '</div>' +

  '<div class="container"><div class="docs-stats" id="docs-stats">' +
    '<div class="docs-stat"><div class="docs-stat-value" id="stat-subs">—</div><div class="docs-stat-label">' + _t('docs.activeSubs') + '</div></div>' +
    '<div class="docs-stat"><div class="docs-stat-value" id="stat-deliveries">—</div><div class="docs-stat-label">' + _t('docs.deliveries') + '</div></div>' +
    '<div class="docs-stat"><div class="docs-stat-value" id="stat-cards">—</div><div class="docs-stat-label">' + _t('docs.roadmapCards') + '</div></div>' +
    '<div class="docs-stat"><div class="docs-stat-value" id="stat-rag">—</div><div class="docs-stat-label">' + _t('docs.ragDocs') + '</div></div>' +
  '</div></div>' +

  '<div class="container"><div class="docs-sources">' +

    (function(){
      var _src1Title = _t('docs.src1.title'), _src1Badge = _t('docs.src1.badge'), _src1Desc = _t('docs.src1.desc');
      var _src1Items = [ _t('docs.src1.0'), _t('docs.src1.1'), _t('docs.src1.2'), _t('docs.src1.3') ];
      var _src1Ex = _t('docs.src1.ex'), _src1Cov = _t('docs.src1.cov');
      var _src2Title = _t('docs.src2.title'), _src2Badge = _t('docs.src2.badge'), _src2Desc = _t('docs.src2.desc');
      var _src2Items = [ _t('docs.src2.0'), _t('docs.src2.1'), _t('docs.src2.2'), _t('docs.src2.3') ];
      var _src2Ex = _t('docs.src2.ex'), _src2Cov = _t('docs.src2.cov');
      var _src3Title = _t('docs.src3.title'), _src3Badge = _t('docs.src3.badge'), _src3Desc = _t('docs.src3.desc');
      var _src3Items = [ _t('docs.src3.0'), _t('docs.src3.1'), _t('docs.src3.2'), _t('docs.src3.3') ];
      var _src3Ex = _t('docs.src3.ex'), _src3Cov = _t('docs.src3.cov');
      return srcCard('📡', _src1Title, _src1Badge, _src1Desc, _src1Items, _src1Ex, _src1Cov) +
        srcCard('📰', _src2Title, _src2Badge, _src2Desc, _src2Items, _src2Ex, _src2Cov) +
        srcCard('🗺️', _src3Title, _src3Badge, _src3Desc, _src3Items, _src3Ex, _src3Cov);
    })() +

    '<div class="docs-source-card docs-rag">' +
      '<div class="docs-source-head"><div class="docs-source-icon">🔍</div><div><h3>' + _t('docs.rag.title') + '</h3><span class="docs-badge">' + _t('docs.rag.badge') + '</span></div></div>' +
      '<p>' + _t('docs.rag.desc') + '</p>' +
      '<div class="docs-rag-grid">' +
        '<div>🚀 <strong>548</strong> ' + _t('docs.rag.0') + '</div><div>📖 <strong>437</strong> ' + _t('docs.rag.1') + '</div>' +
        '<div>🔧 <strong>783</strong> ' + _t('docs.rag.2') + '</div><div>🔫 <strong>783</strong> ' + _t('docs.rag.3') + '</div><div>🛡️ <strong>783</strong> ' + _t('docs.rag.4') + '</div>' +
      '</div>' +
    '</div>' +

  '</div></div>' +

  '<div class="container section" style="text-align:center">' +
    '<h3 class="section-title" style="font-size:1.2em">' + _t('docs.needApi') + '</h3>' +
    '<p class="section-subtitle" style="margin-bottom:20px">' + _t('docs.apiDesc') + '</p>' +
    '<a href="/api/v1/docs" class="btn btn-secondary" target="_blank" rel="noopener">' + _t('docs.apiBtn') + '</a>' +
  '</div>';
}

function srcCard(icon, title, badge, desc, items, example, covered){
  var itemsHtml = items.map(function(i){ return '<li>' + i + '</li>'; }).join('');
  return '<div class="docs-source-card">' +
    '<div class="docs-source-head"><div class="docs-source-icon">' + icon + '</div><div><h3>' + title + '</h3><span class="docs-badge">' + badge + '</span></div></div>' +
    '<p>' + desc + '</p>' +
    '<div class="docs-block"><h4>' + _t('docs.whatWeGet') + '</h4><ul>' + itemsHtml + '</ul></div>' +
    '<div class="docs-block"><h4>' + _t('docs.covered') + '</h4><div class="docs-example"><strong>' + _t('docs.example') + '</strong> ' + example + '</div><p>' + covered + '</p></div>' +
    '</div>';
}

function renderDocsView(app){
  var wrap = document.createElement('div');
  wrap.innerHTML = renderDocsContent();
  app.appendChild(wrap);
  var backLink = wrap.querySelector('#docs-back-link');
  if(backLink) backLink.addEventListener('click', function(e){ e.preventDefault(); navTo('home'); });
  loadDocsStats();
}

function loadDocsStats(){
  fetch('/api/v1/stats').then(function(r){ return r.json(); }).then(function(data){
    var subs = data.subscriptions || {};
    var src = data.sources || {};
    var rag = data.rag || {};
    var el;
    el = document.getElementById('stat-subs'); if(el) el.textContent = subs.active != null ? subs.active : '—';
    el = document.getElementById('stat-deliveries'); if(el) el.textContent = subs.total_deliveries != null ? subs.total_deliveries : '—';
    el = document.getElementById('stat-cards'); if(el) el.textContent = src.roadmap_cards_monitored || '—';
    el = document.getElementById('stat-rag'); if(el) el.textContent = rag.total_documents || '—';
  }).catch(function(){});
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
  back.href = '#'; back.className = 'back-link'; back.textContent = _t('reg.back');
  back.addEventListener('click', function(e){ e.preventDefault(); navTo('home'); });
  wrap.appendChild(back);

  var header = document.createElement('div');
  header.className = 'form-page-header';
  header.innerHTML = '<h2>' + _t('reg.header') + '</h2><p>' + _t('reg.headerDesc') + '</p>';
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
  g1.innerHTML = '<div class="section-label-form"><span class="section-num">1</span><label>' + _t('reg.step1') + '</label></div><input class="form-control" id="f-name" placeholder="' + _t('reg.step1Ph') + '">';
  card.appendChild(g1);

  // 2. Webhook URL
  var g2 = document.createElement('div'); g2.className = 'form-group';
  g2.innerHTML = '<div class="section-label-form"><span class="section-num">2</span><label>' + _t('reg.step2') + '</label></div><input class="form-control" id="f-url" placeholder="' + _t('reg.step2Ph') + '"><div class="form-hint" id="url-hint">' + _t('reg.step2Hint') + '</div><div class="form-hint telegram-hint" id="telegram-hint" style="display:none;margin-top:6px;padding:10px 14px;background:rgba(38,165,228,0.08);border:1px solid rgba(38,165,228,0.2);border-radius:8px;font-size:0.85em;line-height:1.5;color:var(--text2)">' + _t('reg.step2TelegramHint') + '</div>';
  card.appendChild(g2);

  // Show/hide Telegram hint when format changes
  function updateUrlHint(){
    var isTele = selectedFormat === 'telegram';
    var th = $('#telegram-hint');
    var uh = $('#url-hint');
    if(th) th.style.display = isTele ? 'block' : 'none';
    if(uh) uh.style.display = isTele ? 'none' : 'block';
    var urlInput = $('#f-url');
    if(urlInput){
      urlInput.placeholder = isTele ? 'https://votre-serveur.com/telegram-webhook' : 'https://discord.com/api/webhooks/…';
    }
  }

  // 3. Output Format
  var g3 = document.createElement('div'); g3.className = 'form-group';
  g3.innerHTML = '<div class="section-label-form"><span class="section-num">3</span><label>' + _t('reg.step3') + '</label></div>';
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
      updateUrlHint();
    });
    fmtGrid.appendChild(fc);
  });
  g3.appendChild(fmtGrid);
  var fmtHint = document.createElement('div');
  fmtHint.className = 'form-hint';
  fmtHint.textContent = _t('reg.step3Hint');
  card.appendChild(g3);
  card.appendChild(fmtHint);

  // 4. Priority
  var g4 = document.createElement('div'); g4.className = 'form-group';
  g4.innerHTML = '<div class="section-label-form"><span class="section-num">4</span><label>' + _t('reg.step4') + '</label></div><div class="form-hint">' + _t('reg.step4Hint') + '</div>';
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
  g5.innerHTML = '<div class="section-label-form"><span class="section-num">5</span><label>' + _t('reg.step5') + '</label></div><div class="form-hint">' + _t('reg.step5Hint') + '</div>';
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
  g6.innerHTML = '<div class="section-label-form"><span class="section-num">6</span><label>' + _t('reg.step6') + ' <span style="color:var(--text4);font-weight:400">' + _t('reg.step6Opt') + '</span></label></div><div class="form-hint">' + _t('reg.step6Hint') + '</div>';
  var tagsWrap = document.createElement('div'); tagsWrap.className = 'tags-input'; tagsWrap.id = 'tags-wrap';
  var tagsInput = document.createElement('input'); tagsInput.placeholder = _t('reg.step6Ph');
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
  g7.innerHTML = '<div class="section-label-form"><span class="section-num">7</span><label>' + _t('reg.step7') + ' <span style="color:var(--text4);font-weight:400">' + _t('reg.step7Opt') + '</span></label></div><div class="form-hint">' + _t('reg.step7Hint') + '</div>';
  var selCat = document.createElement('select'); selCat.className = 'form-control'; selCat.id = 'f-cat';
  CATEGORIES.forEach(function(c){
    var opt = document.createElement('option'); opt.value = c.id; opt.textContent = c.label + (c.desc ? ' — ' + c.desc : '');
    selCat.appendChild(opt);
  });
  g7.appendChild(selCat);
  card.appendChild(g7);

  // 8. Rate Limit
  var g8 = document.createElement('div'); g8.className = 'form-group';
  g8.innerHTML = '<div class="section-label-form"><span class="section-num">8</span><label>' + _t('reg.step8') + '</label></div><div class="form-hint">' + _t('reg.step8Hint') + '</div>';
  var rateRow = document.createElement('div'); rateRow.style.cssText = 'display:flex;align-items:center;gap:10px;';
  var rateInput = document.createElement('input'); rateInput.className = 'form-control'; rateInput.id = 'f-rate';
  rateInput.type = 'number'; rateInput.value = '30'; rateInput.min = '1'; rateInput.max = '100'; rateInput.style.width = '80px';
  var rateLabel = document.createElement('span'); rateLabel.style.cssText = 'color:var(--text2);font-size:.88em;'; rateLabel.textContent = _t('reg.rateLabel');
  rateRow.appendChild(rateInput); rateRow.appendChild(rateLabel);
  g8.appendChild(rateRow);
  card.appendChild(g8);

  // Submit
  var submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary btn-lg btn-full';
  submitBtn.textContent = _t('reg.submit');
  submitBtn.addEventListener('click', function(){
    var name = ($('#f-name')||{}).value||'';
    var url  = ($('#f-url')||{}).value||'';
    if(!name.trim() || !url.trim()){ showAlert(_t('reg.errNameUrl')); return; }
    if(!url.trim().startsWith('https://')){ showAlert(_t('reg.errHttps')); return; }
    submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> ' + _t('reg.submitting');
    api('/subscriptions', {
      method: 'POST',
      body: JSON.stringify({ name: name.trim(), webhook_url: url.trim(), format: selectedFormat, priority_min: selectedPriority, event_types: selectedTypes, keywords: keywords, category: ($('#f-cat')||{}).value||null, rate_limit: parseInt(($('#f-rate')||{}).value)||30 })
    }).then(function(resp){
      submitBtn.disabled = false; submitBtn.textContent = _t('reg.submit');
      if(resp.status === 201){
        window.history.replaceState({}, '', '?key=' + resp.data.api_key);
        state.apiKey = resp.data.api_key; navTo('dashboard');
        loadDashboard(resp.data.api_key);
      } else { showAlert((resp.data||{}).detail || _t('reg.errFailed')); }
    }).catch(function(){ submitBtn.disabled = false; submitBtn.textContent = _t('reg.submit'); showAlert(_t('reg.errNetwork')); });
  });
  card.appendChild(submitBtn);
  wrap.appendChild(card);
  app.appendChild(wrap);
}

// ── DASHBOARD ──
function renderDashboard(app){
  var s = state.sub;
  if(!s){ app.innerHTML='<div class="loading"><div class="spinner"></div><span>' + _t('loadingDash') + '</span></div>'; return; }

  var header = document.createElement('div'); header.className = 'container';
  header.innerHTML = '<div class="dash-header"><h1>📊 ' + esc(s.name) + '</h1><span class="dash-badge ' + (s.active ? 'dash-badge-active' : 'dash-badge-inactive') + '"><span class="dash-badge-dot"></span>' + (s.active ? _t('dash.active') : _t('dash.inactive')) + '</span></div>';
  app.appendChild(header);

  // API Key
  var keyCard = document.createElement('div'); keyCard.className = 'container';
  keyCard.innerHTML = '<div class="card"><div class="card-title">' + _t('dash.apiKey') + '</div><div class="card-desc">' + _t('dash.apiKeyDesc') + '</div><div class="key-box"><span class="key">' + esc(s.api_key||state.apiKey) + '</span><button class="btn btn-secondary btn-sm" id="copy-key-btn">' + _t('dash.copy') + '</button></div></div>';
  app.appendChild(keyCard);
  $('#copy-key-btn').addEventListener('click', function(){ navigator.clipboard.writeText(state.apiKey); showToast(_t('dash.copied')); });

  // Stats
  var statsCard = document.createElement('div'); statsCard.className = 'container';
  statsCard.innerHTML = '<div class="card"><div class="card-title">' + _t('dash.stats') + '</div><div class="stats-grid">' +
    '<div class="stat-card"><div class="value">' + s.total_deliveries + '</div><div class="label">' + _t('dash.delivered') + '</div></div>' +
    '<div class="stat-card"><div class="value" style="color:' + (s.failure_count>0?'var(--red)':'var(--green)') + '">' + s.failure_count + '</div><div class="label">' + _t('dash.failures') + '</div></div>' +
    '<div class="stat-card"><div class="value">' + s.rate_limit + '/hr</div><div class="label">' + _t('dash.rateLimit') + '</div></div>' +
    '</div></div>';
  app.appendChild(statsCard);

  // Config
  var configCard = document.createElement('div'); configCard.className = 'container';
  var ul = document.createElement('ul'); ul.className = 'config-list';
  function li(k,v){ var node = document.createElement('li'); node.innerHTML = '<span class="key">' + k + '</span><span class="value">' + v + '</span>'; return node; }
  ul.appendChild(li(_t('dash.priority'), '≥ ' + esc(s.priority_min)));
  ul.appendChild(li(_t('dash.eventTypes'), (s.event_types && s.event_types.length) ? esc(s.event_types.join(', ')) : _t('dash.all')));
  ul.appendChild(li(_t('dash.keywords'), (s.keywords && s.keywords.length) ? esc(s.keywords.join(', ')) : _t('dash.none')));
  ul.appendChild(li(_t('dash.category'), esc(s.category) || _t('dash.all')));
  ul.appendChild(li(_t('dash.format'), esc(s.format)));
  ul.appendChild(li(_t('dash.created'), new Date(s.created_at).toLocaleString()));
  ul.appendChild(li(_t('dash.lastDelivery'), s.last_delivery ? new Date(s.last_delivery).toLocaleString() : _t('dash.never')));
  configCard.innerHTML = '<div class="card"><div class="card-title">' + _t('dash.config') + '</div></div>';
  configCard.querySelector('.card').appendChild(ul);
  app.appendChild(configCard);

  // Actions
  var actionsCard = document.createElement('div'); actionsCard.className = 'container';
  actionsCard.innerHTML = '<div class="card"><div class="card-title">' + _t('dash.actions') + '</div><div class="actions">' +
    '<button class="btn btn-secondary btn-sm" id="test-ping-btn">' + _t('dash.testPing') + '</button>' +
    '<button class="btn btn-danger btn-sm" id="delete-sub-btn">' + _t('dash.delete') + '</button>' +
    '</div></div>';
  app.appendChild(actionsCard);
  $('#test-ping-btn').addEventListener('click', function(){
    var btn = $('#test-ping-btn'); btn.disabled = true;
    api('/subscriptions/' + state.apiKey + '/test', { method: 'POST' })
      .then(function(){ showToast(_t('toast.pingSent')); btn.disabled = false; })
      .catch(function(){ showToast(_t('toast.pingFailed'), 'error'); btn.disabled = false; });
  });
  $('#delete-sub-btn').addEventListener('click', function(){
    showModal(_t('modal.deleteTitle'), _t('modal.deleteBody'), function(){
      api('/subscriptions/' + state.apiKey, { method: 'DELETE' }).then(function(){
        window.history.replaceState({}, '/', '/');
        state = { view: 'home', apiKey: null, sub: null }; navTo('home'); showToast(_t('toast.subDeleted'));
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
      navTo('home');
      var app = $('#app'); app.innerHTML = '';
      var err = document.createElement('div'); err.className = 'alert alert-error'; err.innerHTML = '<span class="icon">⚠️</span><span>' + _t('dash.invalidKey') + '</span>';
      app.appendChild(err);
      var back = document.createElement('p');
      var backLink = document.createElement('a'); backLink.href = '#'; backLink.textContent = _t('dash.backHome');
      backLink.addEventListener('click', function(e){ e.preventDefault(); navTo('home'); });
      back.appendChild(backLink);
      app.appendChild(back);
    }
  });
}

// ── MODAL ──
function showModal(title, body, onConfirm){
  var overlay = document.createElement('div'); overlay.className = 'modal-overlay';
  overlay.innerHTML = '<div class="modal"><h3>' + title + '</h3><p>' + body + '</p><div class="modal-actions"><button class="btn btn-secondary btn-sm" id="modal-cancel">' + _t('modal.cancel') + '</button><button class="btn btn-danger btn-sm" id="modal-confirm">' + _t('modal.deleteBtn') + '</button></div></div>';
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

  var modal = document.createElement('div');
  modal.className = 'api-key-modal';

  var heading = document.createElement('h3');
  heading.textContent = _t('modal.apiKeyTitle');

  var desc = document.createElement('p');
  desc.textContent = _t('modal.apiKeyDesc');

  var input = document.createElement('input');
  input.className = 'form-control';
  input.type = 'password';
  input.placeholder = _t('modal.apiKeyPh');
  input.autocomplete = 'off';

  var actions = document.createElement('div');
  actions.className = 'modal-actions';

  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn btn-secondary btn-sm';
  cancelBtn.textContent = _t('modal.cancel');

  var submitBtn = document.createElement('button');
  submitBtn.className = 'btn btn-primary btn-sm';
  submitBtn.textContent = _t('modal.access');

  var closeBtn = document.createElement('button');
  closeBtn.className = 'api-key-modal-close';
  closeBtn.textContent = '✕';

  actions.appendChild(cancelBtn);
  actions.appendChild(submitBtn);
  modal.appendChild(closeBtn);
  modal.appendChild(heading);
  modal.appendChild(desc);
  modal.appendChild(input);
  modal.appendChild(actions);
  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  requestAnimationFrame(function(){ input.focus(); });

  function close(){ overlay.remove(); }
  function submitApiKey(){
    var key = input.value.trim();
    if(!key){ return; }
    close();
    state.apiKey = key; state.view = 'dashboard'; loadDashboard(key);
  }

  cancelBtn.addEventListener('click', close);
  closeBtn.addEventListener('click', close);
  submitBtn.addEventListener('click', submitApiKey);
  input.addEventListener('keydown', function(e){
    if(e.key === 'Enter') submitApiKey();
    if(e.key === 'Escape') close();
  });
  overlay.addEventListener('click', function(e){ if(e.target === overlay) close(); });
}

// ── NAV ──
$('#nav-home').addEventListener('click', function(e){
  e.preventDefault(); navTo('home');
});
$('#nav-get-started').addEventListener('click', function(e){
  e.preventDefault(); navTo('register');
});
$('#nav-dash-btn').addEventListener('click', function(){
  showApiKeyModal();
});

// ── LANGUAGE SWITCHER ──
var _langButtons = document.querySelectorAll('.lang-btn');
function _updateLangButtons(){
  _langButtons.forEach(function(btn){
    btn.classList.toggle('active', btn.id === 'lang-' + I18N.getLang());
  });
}
_updateLangButtons();
document.getElementById('lang-fr').addEventListener('click', function(){
  I18N.setLang('fr'); _updateLangButtons(); render();
});
document.getElementById('lang-en').addEventListener('click', function(){
  I18N.setLang('en'); _updateLangButtons(); render();
});

// ── INIT ──
var params = new URLSearchParams(window.location.search);
var key = params.get('key');
var hashView = getViewFromHash();
if(key){ state.apiKey=key; state.view='dashboard'; window.location.hash = '#dashboard'; loadDashboard(key); }
else if(hashView !== 'home'){ state.view = hashView; render(); }
else { render(); }

// Handle hash navigation (back/forward, manual URL change)
window.addEventListener('hashchange', function(){
  var v = getViewFromHash();
  if(v !== state.view){
    state.view = v;
    render();
  }
});

// ── GLOBAL EVENT DELEGATION (persists across re-renders) ──
document.addEventListener('click', function(e){
  var t = e.target;
  // Footer docs link
  if (t.id === 'footer-docs'){ e.preventDefault(); e.stopPropagation(); navTo('docs'); }
  // Sources docs link (dynamically created)
  if (t.id === 'sources-docs-link'){ e.preventDefault(); e.stopPropagation(); navTo('docs'); }
});

})();
