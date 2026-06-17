var I18N = (function(){
  var lang = localStorage.getItem('lang') || (navigator.language||'en').split('-')[0];
  if(lang !== 'fr' && lang !== 'en') lang = 'en';
  
  var dict = {
    // ── NAV ──
    'nav.features':    { fr: 'Fonctionnalités', en: 'Features' },
    'nav.mcp':         { fr: 'MCP', en: 'MCP' },
    'nav.sources':     { fr: 'Sources', en: 'Sources' },
    'nav.pricing':     { fr: 'Tarifs', en: 'Pricing' },
    'nav.getStarted':  { fr: 'Commencer', en: 'Get Started' },
    'nav.dashboard':   { fr: 'Tableau de bord', en: 'Dashboard' },
    
    // ── HERO ──
    'hero.badge':      { fr: 'Plateforme de veille Star Citizen', en: 'Star Citizen Intelligence Platform' },
    'hero.title':      { fr: 'Veille Star Citizen en temps réel, livrée partout', en: 'Real-time Star Citizen intelligence, delivered anywhere' },
    'hero.subtitle':   { fr: 'Suivez les changements de la roadmap, patch notes, Comm-Links et dev posts — livrés sur Discord ou webhook en temps réel.', en: 'Track roadmap changes, patch notes, Comm-Links, and dev posts — delivered to Discord or webhook in real-time.' },
    'hero.cta':        { fr: 'Créer un abonnement gratuit', en: 'Create Free Subscription' },
    'hero.mcpBtn':     { fr: 'Utiliser comme outil MCP →', en: 'Use as MCP Tool →' },
    'hero.hint':       { fr: 'Gratuit · Sans compte · 30 secondes', en: 'Free · No account needed · Takes 30 seconds' },
    
    // ── PLATFORMS ──
    'platforms.label': { fr: 'Livré sur votre plateforme', en: 'Delivered to your platform' },
    
    // ── FEATURES ──
    'features.label':  { fr: 'Fonctionnalités', en: 'Features' },
    'features.title':  { fr: "Tout ce qu'il faut pour rester informé", en: 'Everything you need to stay informed' },
    'features.subtitle': { fr: 'Surveillez chaque aspect du développement Star Citizen avec des filtres granulaires et une livraison en temps réel.', en: 'Monitor every aspect of Star Citizen development with granular filters and real-time delivery.' },
    'features.0.title': { fr: 'Veille en temps réel', en: 'Real-time Monitoring' },
    'features.0.desc':  { fr: 'Surveille les sources RSI toutes les quelques minutes. Détecte les mises à jour, Comm-Links et dev posts dès leur publication.', en: 'Polls RSI sources every few minutes. Detects updates, new Comm-Links, and dev posts as they happen.' },
    'features.1.title': { fr: 'Filtrage intelligent', en: 'Smart Filtering' },
    'features.1.desc':  { fr: "Mots-clés, catégories, types d'événements et priorités. Recevez uniquement les alertes qui vous intéressent.", en: 'Keywords, categories, event types, and priority levels. Only receive alerts that match what you actually care about.' },
    'features.2.title': { fr: 'Livraison multiplateforme', en: 'Multi-Platform Delivery' },
    'features.2.desc':  { fr: 'Discord ou JSON webhook. Formatage natif pour Discord avec embeds et contenu riche. JSON générique pour tout autre usage.', en: 'Discord or JSON webhook. Native formatting for Discord with embeds and rich content. Generic JSON for everything else.' },
    'features.3.title': { fr: 'Recherche vectorielle (Qdrant)', en: 'Vector Search (Qdrant)' },
    'features.3.desc':  { fr: 'Recherche sémantique dans les données Star Citizen ingérées. Vaisseaux, lore, équipements — recherche en langage naturel.', en: 'Semantic search across ingested Star Citizen data. Ships, lore, equipment — searchable via natural language.' },
    'features.4.title': { fr: 'Intégration MCP', en: 'MCP Integration' },
    'features.4.desc':  { fr: 'Utilisez Verse Monitor comme outil MCP dans Claude Code, Cursor et autres clients compatibles MCP.', en: 'Use Verse Monitor as an MCP tool in Claude Code, Cursor, and other MCP-compatible clients.' },
    'features.5.title': { fr: 'Dashboard de livraison', en: 'Delivery Dashboard' },
    'features.5.desc':  { fr: 'Suivez les livraisons, échecs et limites de débit par abonnement. Pings de test et gestion complète.', en: 'Track deliveries, failures, and rate limits per subscription. Test pings and full configuration management.' },
    
    // ── MCP SECTION ──
    'mcp.label':       { fr: 'Intégration MCP', en: 'MCP Integration' },
    'mcp.title':       { fr: 'Utilisez Verse Monitor comme outil MCP', en: 'Use Verse Monitor as an MCP Tool' },
    'mcp.desc':        { fr: "Verse Monitor expose un serveur Model Context Protocol permettant aux assistants IA de rechercher des données Star Citizen, résumer les notes de patch et rédiger des articles — le tout depuis votre client MCP-compatible favori.", en: 'Verse Monitor exposes a Model Context Protocol server that lets AI assistants search Star Citizen data, summarize patch notes, and help you write articles — all from your favorite MCP-compatible client.' },
    'mcp.0':           { fr: 'Rechercher vaisseaux, lore et équipements en langage naturel', en: 'Search ships, lore, and equipment with natural language' },
    'mcp.1':           { fr: 'Résumer les notes de patch et changements de roadmap', en: 'Summarize patch notes and roadmap changes' },
    'mcp.2':           { fr: 'Rechercher les discussions communautaires et Comm-Links', en: 'Research community discussions and Comm-Links' },
    'mcp.3':           { fr: "Rédiger des articles et mises à jour communautaires avec citations sourcées", en: 'Draft articles and community updates with sourced citations' },
    'mcp.copy':        { fr: 'Copier', en: 'Copy' },
    'mcp.copied':      { fr: 'Configuration copiée !', en: 'Configuration copied!' },
    
    // ── DATA SCOPE ──
    'scope.label':     { fr: 'Données & Sources', en: 'Data Scope & Coverage' },
    'scope.title':     { fr: 'Transparence sur les données disponibles', en: "Transparent about what's available" },
    'scope.subtitle':  { fr: "Nous croyons en l'honnêteté sur la couverture des données. Voici ce que vous pouvez chercher aujourd'hui et ce qui arrive.", en: "We believe in honesty about data coverage. Here's what you can search today and what's coming." },
    'scope.cardTitle': { fr: 'Couverture actuelle', en: 'Current Coverage' },
    'scope.available': { fr: 'Disponible maintenant :', en: 'Available now:' },
    'scope.availableText': { fr: "Spécifications des vaisseaux, entrées Galactapedia, Comm-Links et données d'équipements. Roadmap, notes de patch et dev tracker via le système d'alertes.", en: 'Ship specifications, Galactapedia lore entries, Comm-Links, and equipment/items data. Roadmap changes, patch notes, and dev tracker posts via the alert system.' },
    'scope.improving': { fr: 'En amélioration continue :', en: 'Improving continuously:' },
    'scope.improvingText': { fr: 'Nous ingérons activement plus de sources. Nouveaux types de données et contenu historique ajoutés en continu.', en: "We're actively ingesting more sources and expanding coverage. New data types and deeper historical content are added on a rolling basis." },
    'scope.missing':   { fr: 'Il manque quelque chose ?', en: 'Missing something?' },
    'scope.missingText': { fr: "Si vous avez besoin de données non couvertes, contactez-nous — nous priorisons selon la demande communautaire.", en: "If you need specific data that isn't covered yet, reach out — we prioritize ingestion based on community demand." },
    'scope.docsLink':  { fr: 'Voir la documentation complète →', en: 'View full documentation →' },
    'scope.requestLink': { fr: 'Demander une source →', en: 'Request a source →' },
    'scope.contactLink': { fr: 'Contactez-nous →', en: 'Contact us →' },
    
    // ── EVENT TYPES ──
    'events.label':    { fr: "Types d'événements surveillés", en: 'Monitored Event Types' },
    'events.title':    { fr: 'Couverture complète', en: 'Comprehensive coverage' },
    'events.subtitle': { fr: 'Chaque source majeure de mises à jour Star Citizen, surveillée et filtrée pour vous.', en: 'Every major source of Star Citizen development updates, monitored and filtered for you.' },
    
    // ── PRICING ──
    'pricing.label':   { fr: 'Tarifs', en: 'Pricing' },
    'pricing.title':   { fr: 'Commencez gratuitement, évoluez selon vos besoins', en: 'Start free, scale when you need to' },
    'pricing.subtitle': { fr: "Pas de carte bancaire. Commencez en moins d'une minute.", en: 'No credit card required. Get started in under a minute.' },
    'pricing.free.name':  { fr: 'Gratuit', en: 'Free' },
    'pricing.free.desc':  { fr: "Tout ce qu'il faut pour suivre le développement Star Citizen.", en: 'Everything you need to stay on top of Star Citizen development.' },
    'pricing.free.0':     { fr: 'Abonnements webhook illimités', en: 'Unlimited webhook subscriptions' },
    'pricing.free.1':     { fr: "Tous types d'événements et filtres", en: 'All event types and filters' },
    'pricing.free.2':     { fr: '30 alertes/heure par abonnement', en: '30 alerts/hour per subscription' },
    'pricing.free.3':     { fr: 'Discord, Webhook JSON', en: 'Discord, JSON Webhook' },
    'pricing.free.4':     { fr: 'Dashboard et statistiques', en: 'Delivery dashboard & stats' },
    'pricing.free.btn':   { fr: 'Commencer — Gratuit', en: 'Get Started — Free' },
    'pricing.pro.name':   { fr: 'Pro', en: 'Pro' },
    'pricing.pro.desc':   { fr: 'Pour les power users et communautés qui ont besoin de plus.', en: 'For power users and communities that need more.' },
    'pricing.pro.0':      { fr: 'Limites de débit supérieures', en: 'Higher rate limits' },
    'pricing.pro.1':      { fr: 'Support prioritaire', en: 'Priority support' },
    'pricing.pro.2':      { fr: 'Ingestion de sources personnalisées', en: 'Custom source ingestion' },
    'pricing.pro.3':      { fr: 'Règles de filtrage avancées', en: 'Advanced filtering rules' },
    'pricing.pro.4':      { fr: 'Accès API', en: 'API access' },
    'pricing.pro.btn':    { fr: 'Bientôt disponible', en: 'Coming Soon' },
    'pricing.pro.coming': { fr: 'Prévu pour Q3 2026', en: 'Planned for Q3 2026' },
    
    // ── CTA ──
    'cta.title':       { fr: 'Prêt à rester informé ?', en: 'Ready to stay informed?' },
    'cta.subtitle':    { fr: "Configurez votre premier abonnement webhook en moins d'une minute. Pas de compte requis.", en: 'Set up your first webhook subscription in under a minute. No account required.' },
    'cta.btn':         { fr: 'Créer un abonnement gratuit', en: 'Create Free Subscription' },
    
    // ── REGISTER ──
    'reg.back':        { fr: "← Retour à l'accueil", en: '← Back to home' },
    'reg.header':      { fr: '🚀 Nouvel abonnement', en: '🚀 New Subscription' },
    'reg.headerDesc':  { fr: 'Configurez votre webhook pour recevoir des alertes Star Citizen filtrées.', en: 'Configure your webhook to receive filtered Star Citizen alerts.' },
    'reg.step1':       { fr: 'Nom du projet / canal', en: 'Project / Channel Name' },
    'reg.step1Ph':     { fr: 'ex: StarCitizen FR', en: 'e.g. StarCitizen FR' },
    'reg.step2':       { fr: 'URL du webhook', en: 'Webhook URL' },
    'reg.step2Ph':     { fr: 'https://discord.com/api/webhooks/…', en: 'https://discord.com/api/webhooks/…' },
    'reg.step2Hint':   { fr: 'Discord : collez l\'URL du webhook fourni par Discord. JSON : n\'importe quel endpoint HTTPS acceptant des POST JSON.', en: 'Discord: paste the webhook URL provided by Discord. JSON: any HTTPS endpoint that accepts JSON POST.' },
    'reg.step3':       { fr: 'Format de sortie', en: 'Output Format' },
    'reg.step3Hint':   { fr: 'Discord pour une intégration native. JSON générique pour tout autre usage (Zapier, Make, n8n, serveur personnalisé).', en: 'Discord for native integration. Generic JSON for any other use (Zapier, Make, n8n, custom server).' },
    'reg.step4':       { fr: 'Priorité minimum', en: 'Minimum Priority' },
    'reg.step4Hint':   { fr: 'Recevez uniquement les alertes de ce niveau ou supérieur.', en: 'Only receive alerts at or above this level.' },
    'reg.step5':       { fr: "Types d'événements", en: 'Event Types' },
    'reg.step5Hint':   { fr: "Sélectionnez les types d'alertes à recevoir. Laissez vide pour tout recevoir.", en: 'Select which types of alerts to receive. Leave empty to receive all types.' },
    'reg.step6':       { fr: 'Mots-clés', en: 'Keywords' },
    'reg.step6Opt':    { fr: '(optionnel)', en: '(optional)' },
    'reg.step6Hint':   { fr: 'Seules les alertes contenant au moins un de ces mots seront envoyées. Insensible à la casse.', en: 'Only alerts containing at least one of these words will be sent. Case-insensitive.' },
    'reg.step6Ph':     { fr: 'Tapez un mot, appuyez sur Entrée', en: 'Type a word, press Enter' },
    'reg.step7':       { fr: 'Catégorie', en: 'Category' },
    'reg.step7Opt':    { fr: '(optionnel)', en: '(optional)' },
    'reg.step7Hint':   { fr: 'Filtrer les alertes par catégorie thématique.', en: 'Filter alerts by broad topic category.' },
    'reg.step8':       { fr: 'Limite de débit', en: 'Rate Limit' },
    'reg.step8Hint':   { fr: 'Alertes maximum par heure. Évite le spam pendant les périodes chargées.', en: 'Maximum alerts per hour. Helps prevent channel spam during busy periods.' },
    'reg.rateLabel':   { fr: 'alertes / heure', en: 'alerts / hour' },
    'reg.submit':      { fr: "🚀 Créer l'abonnement", en: '🚀 Create Subscription' },
    'reg.submitting':  { fr: 'Création…', en: 'Creating…' },
    'reg.errNameUrl':  { fr: "Le nom et l'URL du webhook sont requis.", en: 'Name and webhook URL are required.' },
    'reg.errHttps':    { fr: "L'URL du webhook doit commencer par https://", en: 'Webhook URL must start with https://' },
    'reg.errNetwork':  { fr: 'Erreur réseau. Veuillez réessayer.', en: 'Network error. Please try again.' },
    'reg.errFailed':   { fr: "Échec de la création de l'abonnement", en: 'Failed to create subscription' },
    
    // ── DASHBOARD ──
    'dash.apiKey':     { fr: '🔑 Clé API', en: '🔑 API Key' },
    'dash.apiKeyDesc': { fr: 'Gardez cette clé secrète. Utilisez-la pour accéder à ce dashboard.', en: 'Keep this key secret. Use it to access this dashboard.' },
    'dash.copy':       { fr: '📋 Copier', en: '📋 Copy' },
    'dash.copied':     { fr: 'Clé API copiée !', en: 'API key copied!' },
    'dash.stats':      { fr: '📈 Statistiques de livraison', en: '📈 Delivery Stats' },
    'dash.delivered':  { fr: 'Livrées', en: 'Delivered' },
    'dash.failures':   { fr: 'Échecs', en: 'Failures' },
    'dash.rateLimit':  { fr: 'Limite de débit', en: 'Rate Limit' },
    'dash.config':     { fr: '⚙️ Configuration', en: '⚙️ Configuration' },
    'dash.priority':   { fr: 'Priorité', en: 'Priority' },
    'dash.eventTypes': { fr: "Types d'événements", en: 'Event Types' },
    'dash.keywords':   { fr: 'Mots-clés', en: 'Keywords' },
    'dash.category':   { fr: 'Catégorie', en: 'Category' },
    'dash.format':     { fr: 'Format', en: 'Format' },
    'dash.created':    { fr: 'Créé le', en: 'Created' },
    'dash.lastDeliv':  { fr: 'Dernière livraison', en: 'Last Delivery' },
    'dash.never':      { fr: 'Jamais', en: 'Never' },
    'dash.all':        { fr: 'Tous', en: 'All' },
    'dash.none':       { fr: 'Aucun', en: 'None' },
    'dash.actions':    { fr: 'Actions', en: 'Actions' },
    'dash.testPing':   { fr: '🧪 Tester le ping', en: '🧪 Test Ping' },
    'dash.delete':     { fr: '🗑️ Supprimer', en: '🗑️ Delete' },
    'dash.pingSent':   { fr: 'Ping de test envoyé !', en: 'Test ping sent!' },
    'dash.pingFailed': { fr: "Échec de l'envoi du test", en: 'Failed to send test' },
    'dash.subDeleted': { fr: 'Abonnement supprimé', en: 'Subscription deleted' },
    
    // ── MODALS ──
    'modal.deleteTitle':  { fr: "Supprimer l'abonnement", en: 'Delete Subscription' },
    'modal.deleteBody':   { fr: "Êtes-vous sûr ? Cela arrêtera toutes les alertes et c'est irréversible.", en: 'Are you sure? This will permanently stop all alerts and cannot be undone.' },
    'modal.cancel':       { fr: 'Annuler', en: 'Cancel' },
    'modal.confirm':      { fr: 'Supprimer', en: 'Delete' },
    'modal.apiKeyTitle':  { fr: '🔑 Accès au dashboard', en: '🔑 Access Dashboard' },
    'modal.apiKeyDesc':   { fr: 'Entrez votre clé API pour voir vos statistiques et configuration.', en: 'Enter your API key to view your subscription details, delivery stats, and configuration.' },
    'modal.apiKeyPh':     { fr: 'Entrez votre clé API', en: 'Enter your API key' },
    'modal.access':       { fr: 'Accéder', en: 'Access' },
    
    // ── API KEY MODAL ERRORS ──
    'dash.invalidKey':    { fr: 'Clé API invalide. Abonnement non trouvé.', en: 'Invalid API key. Subscription not found.' },
    'dash.backHome':      { fr: "← Retour à l'accueil", en: '← Back to home' },
    
    // ── DOCS ──
    'docs.back':       { fr: '← Retour', en: '← Back' },
    'docs.title':      { fr: 'Données & Sources', en: 'Data & Sources' },
    'docs.subtitle':   { fr: "Voici exactement ce que Verse Monitor surveille, d'où ça vient, et ce qu'on en extrait.", en: "Here's exactly what Verse Monitor monitors, where it comes from, and what we extract." },
    'docs.activeSubs': { fr: 'Abonnements actifs', en: 'Active Subscriptions' },
    'docs.deliveries': { fr: 'Alertes livrées', en: 'Alerts Delivered' },
    'docs.roadmapCards': { fr: 'Cartes Roadmap', en: 'Roadmap Cards' },
    'docs.ragDocs':    { fr: 'Documents connaissances', en: 'Knowledge Documents' },
    'docs.needApi':    { fr: "Besoin de l'API complète ?", en: 'Need the full API?' },
    'docs.apiDesc':    { fr: 'Documentation technique pour développeurs avec tous les endpoints et exemples.', en: 'Technical documentation for developers with all endpoints and examples.' },
    'docs.apiBtn':     { fr: "Voir l'API Reference →", en: 'View API Reference →' },
    
    // ── DOCS SOURCES ──
    'docs.src1.title': { fr: 'Devtracker — Posts Spectrum', en: 'Devtracker — Spectrum Posts' },
    'docs.src1.badge': { fr: 'Toutes les 2 min', en: 'Every 2 min' },
    'docs.src1.desc':  { fr: 'Les posts officiels des développeurs sur Spectrum. Chaque message est récupéré dans son intégralité (~6 000 caractères).', en: 'Official developer posts on Spectrum. Each message is fully retrieved (~6,000 characters).' },
    'docs.src1.0':     { fr: 'Le titre complet du post', en: 'The full post title' },
    'docs.src1.1':     { fr: 'Le nom du développeur (ex: Nicou-CIG)', en: 'Developer name (e.g. Nicou-CIG)' },
    'docs.src1.2':     { fr: 'Le contenu intégral du message (~6 000 caractères)', en: 'The full message content (~6,000 characters)' },
    'docs.src1.3':     { fr: 'La date de publication', en: 'Publication date' },
    'docs.src1.ex':    { fr: '"Alpha 4.8.1 Known Issues Update" de Nicou-CIG — le post complet avec tous les bugs connus et correctifs en cours.', en: '"Alpha 4.8.1 Known Issues Update" by Nicou-CIG — the full post with all known bugs and ongoing fixes.' },
    'docs.src1.cov':   { fr: 'Mises à jour de patch (Known Issues, hotfixes), annonces de features, réponses communautaires, calendriers.', en: 'Patch updates (Known Issues, hotfixes), feature announcements, community responses, release schedules.' },
    
    'docs.src2.title': { fr: 'Comm-Links — Articles officiels RSI', en: 'Comm-Links — Official RSI Articles' },
    'docs.src2.badge': { fr: 'Toutes les 5 min', en: 'Every 5 min' },
    'docs.src2.desc':  { fr: 'Les articles publiés par Roberts Space Industries. Chaque article est récupéré en entier (~4 000 caractères).', en: 'Articles published by Roberts Space Industries. Each article is fully retrieved (~4,000 characters).' },
    'docs.src2.0':     { fr: "Le titre complet de l'article", en: 'The full article title' },
    'docs.src2.1':     { fr: 'La catégorie (transmission, engineering, etc.)', en: 'Category (transmission, engineering, etc.)' },
    'docs.src2.2':     { fr: 'Le contenu intégral (~4 000 caractères)', en: 'Full content (~4,000 characters)' },
    'docs.src2.3':     { fr: 'Sous-titres, paragraphes et listes', en: 'Subtitles, paragraphs and lists' },
    'docs.src2.ex':    { fr: '"Star Citizen Monthly Report — June 2025" — le rapport complet avec l\'état de chaque département.', en: '"Star Citizen Monthly Report — June 2025" — the full report with each department\'s status.' },
    'docs.src2.cov':   { fr: 'Rapports mensuels, This Week in Star Citizen, Behind the Ships, annonces de ventes et événements, interviews.', en: 'Monthly reports, This Week in Star Citizen, Behind the Ships, sale/event announcements, interviews.' },
    
    'docs.src3.title': { fr: 'Roadmap — Calendrier de développement', en: 'Roadmap — Development Schedule' },
    'docs.src3.badge': { fr: 'Toutes les 5 min', en: 'Every 5 min' },
    'docs.src3.desc':  { fr: 'Le calendrier public de développement de CIG. 798 cartes surveillées en permanence.', en: "CIG's public development schedule. 798 cards monitored continuously." },
    'docs.src3.0':     { fr: 'Cartes ajoutées, retardées, publiées ou supprimées', en: 'Cards added, delayed, released, or removed' },
    'docs.src3.1':     { fr: 'Le statut (Tentative, Committed, Released)', en: 'Status (Tentative, Committed, Released)' },
    'docs.src3.2':     { fr: 'Le patch ciblé (4.8, 4.9, 5.0, etc.)', en: 'Targeted patch (4.8, 4.9, 5.0, etc.)' },
    'docs.src3.3':     { fr: 'La description complète de chaque feature', en: 'Full description of each feature' },
    'docs.src3.ex':    { fr: '"Server Meshing" passe de Tentative à Released dans le patch 4.8 → alerte CRITICAL immédiate.', en: '"Server Meshing" moves from Tentative to Released in patch 4.8 → immediate CRITICAL alert.' },
    'docs.src3.cov':   { fr: '🆕 Feature ajoutée • ✅ Feature publiée • ⚠️ Feature retardée • 🗑️ Feature retirée • 📝 Détails mis à jour', en: '🆕 Feature added • ✅ Feature released • ⚠️ Feature delayed • 🗑️ Feature removed • 📝 Details updated' },
    
    'docs.rag.title':   { fr: 'Base de connaissances', en: 'Knowledge Base' },
    'docs.rag.badge':   { fr: '3 334 documents', en: '3,334 documents' },
    'docs.rag.desc':    { fr: 'Base vectorisée pour la recherche sémantique. Interrogeable via MCP (Claude Code, Cursor, etc.).', en: 'Vectorized base for semantic search. Queryable via MCP (Claude Code, Cursor, etc.).' },
    'docs.rag.0':       { fr: 'vaisseaux', en: 'ships' },
    'docs.rag.1':       { fr: 'entrées Galactapedia', en: 'Galactapedia entries' },
    'docs.rag.2':       { fr: 'équipements', en: 'equipment' },
    'docs.rag.3':       { fr: 'armes', en: 'weapons' },
    'docs.rag.4':       { fr: 'armures', en: 'armor' },
    
    'docs.whatWeGet':  { fr: "Ce qu'on récupère", en: 'What we collect' },
    'docs.covered':    { fr: 'Contenu couvert', en: 'Covered content' },
    'docs.example':    { fr: 'Exemple :', en: 'Example:' },
    
    // ── FOOTER ──
    'footer.docs':     { fr: 'Documentation', en: 'Documentation' },
    'footer.contact':  { fr: 'Contact', en: 'Contact' },
    'footer.tagline':  { fr: 'Verse Monitor — Plateforme de veille Star Citizen', en: 'Verse Monitor — Star Citizen Intelligence Platform' },
    'footer.disclaimer': { fr: 'Non affilié à Cloud Imperium Games ou Roberts Space Industries. Star Citizen et marques associées sont des marques de Cloud Imperium Games.', en: 'Not affiliated with Cloud Imperium Games or Roberts Space Industries. Star Citizen and related marks are trademarks of Cloud Imperium Games.' },
    
    // ── TOASTS ──
    'toast.copied':     { fr: 'Copié !', en: 'Copied!' },
    'toast.pingSent':  { fr: 'Ping de test envoyé !', en: 'Test ping sent!' },
    'toast.pingFailed': { fr: "Échec de l'envoi", en: 'Failed to send test' },
    'toast.subDeleted': { fr: 'Abonnement supprimé', en: 'Subscription deleted' },
    'toast.apiKeyCopied': { fr: 'Clé API copiée !', en: 'API key copied!' },
    'toast.configCopied': { fr: 'Configuration copiée !', en: 'Configuration copied!' },
    
    // ── LOADING ──
    'loading':         { fr: 'Chargement…', en: 'Loading…' },
    'loadingDash':     { fr: 'Chargement du dashboard…', en: 'Loading dashboard…' },
    
    // ── EVENT TYPE LABELS ──
    'et.roadmap_card_added':    { fr: 'Cartes ajoutées', en: 'Cards Added' },
    'et.roadmap_card_released': { fr: 'Publiées', en: 'Released' },
    'et.roadmap_card_delayed':  { fr: 'Retardées', en: 'Delayed' },
    'et.roadmap_card_removed':  { fr: 'Supprimées', en: 'Removed' },
    'et.roadmap_card_updated':  { fr: 'Mises à jour', en: 'Updated' },
    'et.patch_notes_live':      { fr: 'Notes de patch', en: 'Patch Notes' },
    'et.comm_link_published':   { fr: 'Comm-Links', en: 'Comm-Links' },
    'et.devtracker_post':       { fr: 'Dev Posts', en: 'Dev Posts' },
    'et.twisc_published':       { fr: 'This Week in SC', en: 'This Week in SC' },
    'et.monthly_report':        { fr: 'Rapports mensuels', en: 'Monthly Reports' },
    
    // ── PRIORITY LABELS ──
    'prio.LOW':      { fr: 'Basse', en: 'Low' },
    'prio.MEDIUM':   { fr: 'Standard', en: 'Standard' },
    'prio.HIGH':     { fr: 'Haute', en: 'High' },
    'prio.CRITICAL': { fr: 'Critique', en: 'Critical' },
    
    // ── CATEGORY LABELS ──
    'cat.all':       { fr: 'Toutes catégories', en: 'All Categories' },
    'cat.ship':      { fr: 'Vaisseaux', en: 'Ships' },
    'cat.gameplay':  { fr: 'Gameplay', en: 'Gameplay' },
    'cat.tech':      { fr: 'Technologie', en: 'Technology' },
    'cat.event':     { fr: 'Événements en jeu', en: 'In-Game Events' },
    'cat.lore':      { fr: 'Lore', en: 'Lore' },

    // ── EVENT TYPE DESCRIPTIONS ──
    'etd.roadmap_card_added':    { fr: 'Nouvelles cartes apparaissant sur la roadmap', en: 'New cards appearing on the roadmap' },
    'etd.roadmap_card_released': { fr: 'Cartes passant dans un patch LIVE', en: 'Cards moving to a LIVE patch' },
    'etd.roadmap_card_delayed':  { fr: 'Cartes repoussées à un patch ultérieur', en: 'Cards pushed to a later patch' },
    'etd.roadmap_card_removed':  { fr: 'Cartes supprimées de la roadmap', en: 'Cards removed from the roadmap' },
    'etd.roadmap_card_updated':  { fr: 'Détails de carte modifiés (titre, description, patch)', en: 'Card details changed (title, description, patch)' },
    'etd.patch_notes_live':      { fr: 'Publication officielle des notes de patch LIVE', en: 'Official LIVE patch notes publication' },
    'etd.comm_link_published':   { fr: 'Comm-Links RSI (rapports hebdomadaires, aperçus)', en: 'RSI Comm-Links (weekly reports, sneak peeks)' },
    'etd.devtracker_post':       { fr: 'Posts individuels de développeurs sur le tracker', en: 'Individual developer posts on the progress tracker' },
    'etd.twisc_published':       { fr: 'Newsletter hebdomadaire "This Week in Star Citizen"', en: 'Weekly newsletter "This Week in Star Citizen"' },
    'etd.monthly_report':        { fr: 'Rapports de production mensuels', en: 'Monthly production reports' },

    // ── PRIORITY DESCRIPTIONS ──
    'priod.LOW':      { fr: 'Toutes les alertes, même mineures', en: 'All alerts including minor ones' },
    'priod.MEDIUM':   { fr: 'Ignorer les alertes mineures, garder les changements significatifs', en: 'Skip minor alerts, keep meaningful changes' },
    'priod.HIGH':     { fr: 'Événements importants uniquement (sorties, retards, patches)', en: 'Only important events (releases, delays, patches)' },
    'priod.CRITICAL': { fr: 'Alertes critiques uniquement (sorties majeures, changements majeurs)', en: 'Critical alerts only (major releases, breaking changes)' },

    // ── MODAL (missing key fix) ──
    'modal.deleteBtn': { fr: 'Supprimer', en: 'Delete' },

    // ── ADMIN ──
    'admin.title':    { fr: 'Tableau de bord admin', en: 'Admin Dashboard' },
    'admin.overview': { fr: 'Vue d\'ensemble', en: 'Overview' },
    'admin.sources':  { fr: 'Sources', en: 'Sources' },
    'admin.rag':      { fr: 'RAG', en: 'RAG' },
    'admin.webhooks': { fr: 'Webhooks', en: 'Webhooks' },
    'admin.system':   { fr: 'Système', en: 'System' },

    // ── ADMIN SOURCES ──
    'admin.sources.name':      { fr: 'Source', en: 'Source' },
    'admin.sources.status':    { fr: 'Statut', en: 'Status' },
    'admin.sources.lastFetch': { fr: 'Dernier fetch', en: 'Last Fetch' },
    'admin.sources.nextFetch': { fr: 'Prochain fetch', en: 'Next Fetch' },
    'admin.sources.errors':    { fr: 'Erreurs', en: 'Errors' },
    'admin.sources.actions':   { fr: 'Actions', en: 'Actions' },
    'admin.sources.crawl':     { fr: 'Re-crawler', en: 'Re-crawl' },
    'admin.sources.pause':     { fr: 'Mettre en pause', en: 'Pause' },
    'admin.sources.resume':    { fr: 'Reprendre', en: 'Resume' },

    // ── ADMIN RAG ──
    'admin.rag.totalChunks':   { fr: 'Total chunks', en: 'Total Chunks' },
    'admin.rag.categories':    { fr: 'Catégories', en: 'Categories' },
    'admin.rag.lastIngestion': { fr: 'Dernière ingestion', en: 'Last Ingestion' },
    'admin.rag.reingest':      { fr: 'Ré-ingérer maintenant', en: 'Re-ingest Now' },

    // ── ADMIN WEBHOOKS ──
    'admin.webhooks.all':    { fr: 'Tous les abonnements', en: 'All Subscriptions' },
    'admin.webhooks.test':   { fr: 'Tester', en: 'Test' },
    'admin.webhooks.delete': { fr: 'Supprimer', en: 'Delete' },

    // ── ADMIN SYSTEM ──
    'admin.system.uptime':     { fr: 'Uptime', en: 'Uptime' },
    'admin.system.memory':     { fr: 'Mémoire', en: 'Memory' },
    'admin.system.disk':       { fr: 'Disque', en: 'Disk' },
    'admin.system.load':       { fr: 'Charge', en: 'Load' },
    'admin.system.redis':      { fr: 'Redis', en: 'Redis' },
    'admin.system.qdrant':     { fr: 'Qdrant', en: 'Qdrant' },
    'admin.system.scheduler':  { fr: 'Scheduler', en: 'Scheduler' },
    'admin.system.flushCache': { fr: 'Vider le cache', en: 'Flush Cache' },
    'admin.system.reindex':    { fr: 'Ré-indexer', en: 'Re-index' },

    // ── CATEGORY DESCRIPTIONS ──
    'catd.all':       { fr: 'Aucun filtre — tout recevoir', en: 'No category filter — receive everything' },
    'catd.ship':      { fr: 'Changements liés aux vaisseaux, stats, sorties', en: 'Ship-related changes, stats, releases' },
    'catd.gameplay':  { fr: 'Mécaniques de jeu, systèmes, FPS, missions', en: 'Game mechanics, systems, FPS, missions' },
    'catd.tech':      { fr: 'Moteur, rendu, réseau, performance', en: 'Engine, rendering, netcode, performance' },
    'catd.event':     { fr: 'Événements en jeu, IAE, Invictus, patches', en: 'In-game events, IAE, Invictus, patches' },
    'catd.lore':      { fr: 'Galactapedia, Comm-Links, actualités de l\'univers', en: 'Galactapedia, Comm-Links, universe news' },
  };
  
  function t(key, fallback){
    var entry = dict[key];
    if(!entry) return fallback || key;
    return entry[lang] || entry.en || fallback || key;
  }
  
  function setLang(l){
    lang = l;
    localStorage.setItem('lang', l);
    document.documentElement.lang = l;
  }
  
  function getLang(){ return lang; }
  
  return { t: t, setLang: setLang, getLang: getLang, dict: dict };
})();
