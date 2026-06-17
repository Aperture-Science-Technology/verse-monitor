/* Admin Dashboard — vanilla JS module */
var AdminDashboard = (function () {
  'use strict';

  var _container = null;
  var _tab = 'overview';
  var _refreshTimer = null;
  var API = '/api/v1';

  // Admin API key — set during init from server-rendered meta tag or prompt
  var _adminKey = '';

  var TABS = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'sources',  label: 'Sources',  icon: '📡' },
    { id: 'rag',      label: 'RAG',      icon: '🔍' },
    { id: 'webhooks', label: 'Webhooks', icon: '🔗' },
    { id: 'system',   label: 'System',   icon: '⚙️' },
  ];

  // ── HELPERS ──

  function _apiFetch(path, opts) {
    opts = opts || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (_adminKey) {
      headers['X-Admin-Key'] = _adminKey;
    }
    opts.headers = headers;
    return fetch(API + path, opts).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  function _toast(msg, type) {
    var c = document.getElementById('toasts');
    if (!c) return;
    var t = document.createElement('div');
    t.className = 'toast toast-' + (type || 'success');
    t.innerHTML = '<span>' + (type === 'error' ? '❌' : '✅') + '</span><span>' + msg + '</span>';
    c.appendChild(t);
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transform = 'translateX(16px)';
      setTimeout(function () { t.remove(); }, 300);
    }, 4000);
  }

  function _modal(title, body, confirmLabel, onConfirm) {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    var modal = document.createElement('div');
    modal.className = 'modal';
    var h3 = document.createElement('h3');
    h3.textContent = title;
    var p = document.createElement('p');
    p.textContent = body;
    var actions = document.createElement('div');
    actions.className = 'modal-actions';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary btn-sm';
    cancelBtn.textContent = 'Cancel';
    var confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-danger btn-sm';
    confirmBtn.textContent = confirmLabel || 'Confirm';
    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);
    modal.appendChild(h3);
    modal.appendChild(p);
    modal.appendChild(actions);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    cancelBtn.addEventListener('click', function () { overlay.remove(); });
    confirmBtn.addEventListener('click', function () { overlay.remove(); onConfirm(); });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.remove(); });
  }

  function _formatUptime(seconds) {
    var d = Math.floor(seconds / 86400);
    var h = Math.floor((seconds % 86400) / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return d + 'd ' + h + 'h';
    if (h > 0) return h + 'h ' + m + 'm';
    return m + 'm';
  }

  function _statCard(value, label, sub) {
    var card = document.createElement('div');
    card.className = 'admin-card admin-stat-card';
    var val = document.createElement('div');
    val.className = 'admin-stat-value';
    val.textContent = value;
    var lbl = document.createElement('div');
    lbl.className = 'admin-stat-label';
    lbl.textContent = label;
    card.appendChild(val);
    card.appendChild(lbl);
    if (sub) {
      var s = document.createElement('div');
      s.className = 'admin-stat-sub';
      s.textContent = sub;
      card.appendChild(s);
    }
    return card;
  }

  function _loading(content) {
    content.innerHTML = '';
    var el = document.createElement('div');
    el.className = 'loading';
    el.innerHTML = '<div class="spinner"></div><span>Loading…</span>';
    content.appendChild(el);
  }

  function _errorState(content, msg) {
    content.innerHTML = '';
    var el = document.createElement('div');
    el.className = 'admin-error';
    el.textContent = msg;
    content.appendChild(el);
  }

  // ── LAYOUT ──

  function init(container) {
    _container = container;
    _tab = 'overview';
    _promptAdminKey();
    _render();
  }

  function _promptAdminKey() {
    // Check if we have a key stored in sessionStorage
    var stored = sessionStorage.getItem('verse:admin_key');
    if (stored) {
      _adminKey = stored;
      return;
    }
    // Prompt the user for the admin key
    var key = prompt('Enter admin API key:');
    if (key && key.trim()) {
      _adminKey = key.trim();
      sessionStorage.setItem('verse:admin_key', _adminKey);
    }
  }

  function _render() {
    if (!_container) return;
    _container.innerHTML = '';

    var wrap = document.createElement('div');
    wrap.className = 'admin-wrap';

    var header = document.createElement('div');
    header.className = 'admin-header';
    var title = document.createElement('h2');
    title.className = 'admin-title';
    title.textContent = 'Admin Dashboard';
    header.appendChild(title);
    wrap.appendChild(header);

    var layout = document.createElement('div');
    layout.className = 'admin-layout';
    layout.appendChild(_buildSidebar());

    var content = document.createElement('div');
    content.className = 'admin-content';
    content.id = 'admin-tab-content';
    layout.appendChild(content);

    wrap.appendChild(layout);
    _container.appendChild(wrap);
    _renderTab(_tab);
  }

  function _buildSidebar() {
    var sidebar = document.createElement('nav');
    sidebar.className = 'admin-sidebar';

    TABS.forEach(function (tab) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'admin-nav-item' + (tab.id === _tab ? ' active' : '');
      btn.dataset.adminTab = tab.id;

      var icon = document.createElement('span');
      icon.className = 'admin-nav-icon';
      icon.textContent = tab.icon;
      var label = document.createElement('span');
      label.textContent = tab.label;

      btn.appendChild(icon);
      btn.appendChild(label);
      btn.addEventListener('click', function () { _switchTab(tab.id); });
      sidebar.appendChild(btn);
    });

    return sidebar;
  }

  function _switchTab(tabId) {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
    _tab = tabId;
    document.querySelectorAll('[data-admin-tab]').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.adminTab === tabId);
    });
    _renderTab(tabId);
    if (tabId === 'overview') _startRefresh();
  }

  function _startRefresh() {
    if (_refreshTimer) clearInterval(_refreshTimer);
    _refreshTimer = setInterval(function () {
      if (!_container || !document.body.contains(_container)) {
        clearInterval(_refreshTimer);
        _refreshTimer = null;
        return;
      }
      if (_tab === 'overview') _renderTab('overview');
    }, 30000);
  }

  function _renderTab(tabId) {
    var content = document.getElementById('admin-tab-content');
    if (!content) return;
    _loading(content);
    if (tabId === 'overview') _renderOverview(content);
    else if (tabId === 'sources') _renderSources(content);
    else if (tabId === 'rag') _renderRag(content);
    else if (tabId === 'webhooks') _renderWebhooks(content);
    else if (tabId === 'system') _renderSystem(content);
  }

  // ── OVERVIEW TAB ──

  function _renderOverview(content) {
    Promise.all([
      fetch(API + '/stats').then(function (r) { return r.json(); }),
      fetch(API + '/admin/system').then(function (r) { return r.json(); }),
      fetch(API + '/admin/activity').then(function (r) { return r.json(); }),
    ]).then(function (res) {
      var stats = res[0] || {};
      var system = res[1] || {};
      var activity = res[2] || {};
      var subs = stats.subscriptions || {};
      var rag = stats.rag || {};
      var mem = system.memory || {};

      content.innerHTML = '';

      var grid = document.createElement('div');
      grid.className = 'admin-stats-grid';
      [
        { v: subs.active != null ? subs.active : '—', l: 'Active Subscriptions' },
        { v: subs.total_deliveries != null ? subs.total_deliveries : '—', l: 'Total Deliveries' },
        { v: stats.alerts_stored != null ? stats.alerts_stored : '—', l: 'Alerts Stored' },
        { v: rag.total_documents != null ? rag.total_documents : '—', l: 'RAG Documents' },
        { v: mem.percent != null ? mem.percent + '%' : '—', l: 'Memory Usage', s: mem.used_mb != null ? mem.used_mb + ' / ' + mem.total_mb + ' MB' : '' },
        { v: system.uptime_seconds != null ? _formatUptime(system.uptime_seconds) : '—', l: 'System Uptime' },
      ].forEach(function (c) { grid.appendChild(_statCard(c.v, c.l, c.s)); });
      content.appendChild(grid);

      var actTitle = document.createElement('h3');
      actTitle.className = 'admin-section-title';
      actTitle.textContent = 'Recent Activity';
      content.appendChild(actTitle);

      var events = activity.events || [];
      var actList = document.createElement('div');
      actList.className = 'admin-activity-list';

      if (events.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'admin-empty';
        empty.textContent = 'No recent activity in the sc:events stream.';
        actList.appendChild(empty);
      } else {
        events.forEach(function (ev) {
          var item = document.createElement('div');
          item.className = 'admin-activity-item';

          var evType = document.createElement('span');
          evType.className = 'admin-activity-type';
          evType.textContent = ev.type || ev.event_type || 'event';

          var evTitle = document.createElement('span');
          evTitle.className = 'admin-activity-title';
          evTitle.textContent = ev.title || ev.id || '';

          var evTime = document.createElement('span');
          evTime.className = 'admin-activity-time';
          try {
            evTime.textContent = ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '';
          } catch (e) { evTime.textContent = ''; }

          item.appendChild(evType);
          item.appendChild(evTitle);
          item.appendChild(evTime);
          actList.appendChild(item);
        });
      }

      content.appendChild(actList);
    }).catch(function (e) {
      _errorState(content, 'Failed to load overview: ' + e.message);
    });
  }

  // ── SOURCES TAB ──

  function _renderSources(content) {
    fetch(API + '/admin/sources/status').then(function (r) { return r.json(); }).then(function (data) {
      content.innerHTML = '';

      var title = document.createElement('h3');
      title.className = 'admin-section-title';
      title.textContent = 'Data Sources';
      content.appendChild(title);

      var table = document.createElement('table');
      table.className = 'admin-table';

      var thead = document.createElement('thead');
      var headerRow = document.createElement('tr');
      ['Source', 'Status', 'Last Fetch', 'Errors', 'Actions'].forEach(function (h) {
        var th = document.createElement('th');
        th.textContent = h;
        headerRow.appendChild(th);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);

      var tbody = document.createElement('tbody');

      (data.sources || []).forEach(function (src) {
        var tr = document.createElement('tr');

        var tdName = document.createElement('td');
        tdName.textContent = src.name;
        tdName.style.fontWeight = '510';

        var tdStatus = document.createElement('td');
        var badge = document.createElement('span');
        badge.className = 'admin-badge admin-badge-' + (src.is_active ? 'active' : 'paused');
        badge.textContent = src.is_active ? 'Active' : 'Paused';
        tdStatus.appendChild(badge);

        var tdFetch = document.createElement('td');
        tdFetch.className = 'admin-table-meta';
        try {
          tdFetch.textContent = src.last_fetch ? new Date(src.last_fetch).toLocaleString() : 'Never';
        } catch (e) { tdFetch.textContent = src.last_fetch || 'Never'; }

        var tdErrors = document.createElement('td');
        tdErrors.textContent = src.error_count;
        tdErrors.style.color = src.error_count > 0 ? 'var(--red)' : 'var(--text4)';

        var tdActions = document.createElement('td');
        tdActions.className = 'admin-actions-cell';

        var crawlBtn = document.createElement('button');
        crawlBtn.type = 'button';
        crawlBtn.className = 'admin-btn admin-btn-primary';
        crawlBtn.textContent = 'Re-crawl';
        (function (s, btn) {
          btn.addEventListener('click', function () {
            btn.disabled = true;
            fetch(API + '/admin/sources/' + s.id + '/crawl', { method: 'POST' })
              .then(function () {
                _toast('Crawl triggered for ' + s.name);
                btn.disabled = false;
              }).catch(function () {
                _toast('Failed to trigger crawl', 'error');
                btn.disabled = false;
              });
          });
        })(src, crawlBtn);

        var pauseBtn = document.createElement('button');
        pauseBtn.type = 'button';
        pauseBtn.className = 'admin-btn ' + (src.is_active ? 'admin-btn-warn' : 'admin-btn-secondary');
        pauseBtn.textContent = src.is_active ? 'Pause' : 'Resume';
        (function (s, btn) {
          btn.addEventListener('click', function () {
            btn.disabled = true;
            fetch(API + '/admin/sources/' + s.id + '/pause', { method: 'POST' })
              .then(function (r) { return r.json(); })
              .then(function (d) {
                _toast(s.name + ' ' + d.status);
                _renderSources(content);
              }).catch(function () {
                _toast('Failed to toggle source', 'error');
                btn.disabled = false;
              });
          });
        })(src, pauseBtn);

        tdActions.appendChild(crawlBtn);
        tdActions.appendChild(pauseBtn);

        tr.appendChild(tdName);
        tr.appendChild(tdStatus);
        tr.appendChild(tdFetch);
        tr.appendChild(tdErrors);
        tr.appendChild(tdActions);
        tbody.appendChild(tr);
      });

      table.appendChild(tbody);
      content.appendChild(table);
    }).catch(function (e) {
      _errorState(content, 'Failed to load sources: ' + e.message);
    });
  }

  // ── RAG TAB ──

  function _renderRag(content) {
    Promise.all([
      fetch(API + '/stats').then(function (r) { return r.json(); }),
      fetch(API + '/admin/system').then(function (r) { return r.json(); }),
    ]).then(function (res) {
      var stats = res[0] || {};
      var system = res[1] || {};
      var rag = stats.rag || {};
      var cats = rag.categories || {};
      var ingestion = system.ingestion || {};

      content.innerHTML = '';

      var title = document.createElement('h3');
      title.className = 'admin-section-title';
      title.textContent = 'Knowledge Base (RAG)';
      content.appendChild(title);

      var grid = document.createElement('div');
      grid.className = 'admin-stats-grid';
      [
        { v: rag.total_documents || '—', l: 'Total Documents' },
        { v: cats.ships || '—',     l: 'Ships' },
        { v: cats.lore || '—',      l: 'Lore' },
        { v: cats.equipment || '—', l: 'Equipment' },
        { v: cats.weapons || '—',   l: 'Weapons' },
        { v: cats.armor || '—',     l: 'Armor' },
      ].forEach(function (c) { grid.appendChild(_statCard(c.v, c.l)); });
      content.appendChild(grid);

      // Last ingestion card
      var ingCard = document.createElement('div');
      ingCard.className = 'admin-card';
      var ingCardTitle = document.createElement('div');
      ingCardTitle.className = 'admin-card-title';
      ingCardTitle.textContent = 'Last Ingestion';
      ingCard.appendChild(ingCardTitle);

      if (ingestion.started_at) {
        var ingBody = document.createElement('div');
        ingBody.className = 'admin-card-body';
        var rows = [
          ['Started', new Date(ingestion.started_at * 1000).toLocaleString()],
          ingestion.items_fetched != null ? ['Items Fetched', ingestion.items_fetched] : null,
          ingestion.chunks_created != null ? ['Chunks Created', ingestion.chunks_created] : null,
          ingestion.elapsed_seconds != null ? ['Duration', ingestion.elapsed_seconds.toFixed(1) + 's'] : null,
        ];
        rows.forEach(function (row) {
          if (!row) return;
          var r = document.createElement('div');
          r.className = 'admin-meta-row';
          var k = document.createElement('span');
          k.textContent = row[0];
          var v = document.createElement('span');
          v.textContent = row[1];
          r.appendChild(k);
          r.appendChild(v);
          ingBody.appendChild(r);
        });
        if (ingestion.errors != null) {
          var errRow = document.createElement('div');
          errRow.className = 'admin-meta-row';
          var errK = document.createElement('span');
          errK.textContent = 'Errors';
          var errV = document.createElement('span');
          errV.textContent = ingestion.errors;
          errV.style.color = ingestion.errors > 0 ? 'var(--red)' : 'var(--green)';
          errRow.appendChild(errK);
          errRow.appendChild(errV);
          ingBody.appendChild(errRow);
        }
        ingCard.appendChild(ingBody);
      } else if (ingestion.error) {
        var ingErrEl = document.createElement('div');
        ingErrEl.className = 'admin-error-inline';
        ingErrEl.textContent = 'Last run failed: ' + ingestion.error;
        ingCard.appendChild(ingErrEl);
      } else {
        var ingNone = document.createElement('div');
        ingNone.className = 'admin-meta-empty';
        ingNone.textContent = 'No ingestion data available yet.';
        ingCard.appendChild(ingNone);
      }

      var reingestBtn = document.createElement('button');
      reingestBtn.type = 'button';
      reingestBtn.className = 'admin-btn admin-btn-primary';
      reingestBtn.style.marginTop = '14px';
      reingestBtn.textContent = 'Re-ingest Now';
      reingestBtn.addEventListener('click', function () {
        reingestBtn.disabled = true;
        fetch(API + '/admin/ingest', { method: 'POST' })
          .then(function () { _toast('Ingestion triggered'); reingestBtn.disabled = false; })
          .catch(function () { _toast('Failed to trigger ingestion', 'error'); reingestBtn.disabled = false; });
      });
      ingCard.appendChild(reingestBtn);
      content.appendChild(ingCard);

      // RAG search test card
      var testCard = document.createElement('div');
      testCard.className = 'admin-card admin-test-rag';
      var testTitle = document.createElement('div');
      testTitle.className = 'admin-card-title';
      testTitle.textContent = 'Semantic Search Test';
      testCard.appendChild(testTitle);

      var testRow = document.createElement('div');
      testRow.className = 'admin-test-row';

      var testInput = document.createElement('input');
      testInput.className = 'form-control';
      testInput.placeholder = 'Enter a search query (e.g. "Hammerhead features")';
      testInput.type = 'text';

      var testBtn = document.createElement('button');
      testBtn.type = 'button';
      testBtn.className = 'admin-btn admin-btn-secondary';
      testBtn.textContent = 'Search';

      testRow.appendChild(testInput);
      testRow.appendChild(testBtn);
      testCard.appendChild(testRow);

      var testResults = document.createElement('div');
      testResults.className = 'admin-test-results';
      testCard.appendChild(testResults);

      function doSearch() {
        var q = testInput.value.trim();
        if (!q) return;
        testBtn.disabled = true;
        testResults.innerHTML = '<div class="loading"><div class="spinner"></div><span>Searching…</span></div>';
        fetch(API + '/admin/rag/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, limit: 5 }),
        }).then(function (r) { return r.json(); }).then(function (d) {
          testBtn.disabled = false;
          testResults.innerHTML = '';
          if (d.error) {
            var errEl = document.createElement('div');
            errEl.className = 'admin-error';
            errEl.textContent = 'Search error: ' + d.error;
            testResults.appendChild(errEl);
            return;
          }
          var hits = d.results || [];
          if (hits.length === 0) {
            testResults.textContent = 'No results found.';
            return;
          }
          hits.forEach(function (hit) {
            var item = document.createElement('div');
            item.className = 'admin-rag-result';
            var itemTitle = document.createElement('div');
            itemTitle.className = 'admin-rag-result-title';
            var titleText = document.createElement('span');
            titleText.textContent = hit.title || hit.id || 'Result';
            var scoreEl = document.createElement('span');
            scoreEl.className = 'admin-badge admin-badge-active';
            scoreEl.textContent = hit.score != null ? hit.score.toFixed(3) : '';
            itemTitle.appendChild(titleText);
            itemTitle.appendChild(scoreEl);
            var itemBody = document.createElement('div');
            itemBody.className = 'admin-rag-result-body';
            itemBody.textContent = hit.content || hit.text || hit.url || JSON.stringify(hit).slice(0, 200);
            item.appendChild(itemTitle);
            item.appendChild(itemBody);
            testResults.appendChild(item);
          });
        }).catch(function (e) {
          testBtn.disabled = false;
          testResults.textContent = 'Search failed: ' + e.message;
        });
      }

      testBtn.addEventListener('click', doSearch);
      testInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') doSearch(); });

      content.appendChild(testCard);
    }).catch(function (e) {
      _errorState(content, 'Failed to load RAG data: ' + e.message);
    });
  }

  // ── WEBHOOKS TAB ──

  function _renderWebhooks(content) {
    fetch(API + '/admin/subscriptions').then(function (r) { return r.json(); }).then(function (data) {
      content.innerHTML = '';

      var titleRow = document.createElement('div');
      titleRow.className = 'admin-section-header';
      var titleEl = document.createElement('h3');
      titleEl.className = 'admin-section-title';
      titleEl.style.marginTop = '0';
      titleEl.textContent = 'All Subscriptions (' + (data.total || 0) + ')';
      titleRow.appendChild(titleEl);
      content.appendChild(titleRow);

      var subs = data.subscriptions || [];
      if (subs.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'admin-empty';
        empty.textContent = 'No subscriptions found.';
        content.appendChild(empty);
        return;
      }

      var table = document.createElement('table');
      table.className = 'admin-table';

      var thead = document.createElement('thead');
      var headerRow = document.createElement('tr');
      ['Name', 'Format', 'Priority', 'Delivered', 'Failures', 'Status', 'Created', 'Actions'].forEach(function (h) {
        var th = document.createElement('th');
        th.textContent = h;
        headerRow.appendChild(th);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);

      var tbody = document.createElement('tbody');

      subs.forEach(function (sub) {
        var tr = document.createElement('tr');

        var tdName = document.createElement('td');
        tdName.textContent = sub.name;
        tdName.style.fontWeight = '510';

        var tdFormat = document.createElement('td');
        tdFormat.textContent = sub.format;
        tdFormat.className = 'admin-table-meta';

        var tdPrio = document.createElement('td');
        tdPrio.textContent = sub.priority_min;
        tdPrio.className = 'admin-table-meta';

        var tdDel = document.createElement('td');
        tdDel.textContent = sub.total_deliveries;

        var tdFail = document.createElement('td');
        tdFail.textContent = sub.failure_count;
        tdFail.style.color = sub.failure_count > 0 ? 'var(--red)' : 'var(--text4)';

        var tdStatus = document.createElement('td');
        var badge = document.createElement('span');
        badge.className = 'admin-badge admin-badge-' + (sub.active ? 'active' : 'paused');
        badge.textContent = sub.active ? 'Active' : 'Paused';
        tdStatus.appendChild(badge);

        var tdCreated = document.createElement('td');
        tdCreated.className = 'admin-table-meta';
        try { tdCreated.textContent = new Date(sub.created_at).toLocaleDateString(); }
        catch (e) { tdCreated.textContent = sub.created_at || '—'; }

        var tdActions = document.createElement('td');
        tdActions.className = 'admin-actions-cell';

        // Test ping
        var pingBtn = document.createElement('button');
        pingBtn.type = 'button';
        pingBtn.className = 'admin-btn admin-btn-secondary';
        pingBtn.textContent = 'Test';
        (function (s, btn) {
          btn.addEventListener('click', function () {
            btn.disabled = true;
            fetch(API + '/subscriptions/' + s.api_key + '/test', { method: 'POST' })
              .then(function (r) { return r.json(); })
              .then(function (d) {
                _toast(d.status === 'ok' ? 'Ping sent!' : ('Ping failed: ' + (d.message || '')), d.status === 'ok' ? 'success' : 'error');
                btn.disabled = false;
              }).catch(function () { _toast('Ping failed', 'error'); btn.disabled = false; });
          });
        })(sub, pingBtn);

        // Pause / Resume
        var pauseBtn = document.createElement('button');
        pauseBtn.type = 'button';
        pauseBtn.className = 'admin-btn ' + (sub.active ? 'admin-btn-warn' : 'admin-btn-secondary');
        pauseBtn.textContent = sub.active ? 'Pause' : 'Resume';
        (function (s, btn) {
          btn.addEventListener('click', function () {
            btn.disabled = true;
            fetch(API + '/subscriptions/' + s.api_key, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: !s.active }),
            }).then(function () {
              _toast(s.name + (s.active ? ' paused' : ' resumed'));
              _renderWebhooks(content);
            }).catch(function () { _toast('Failed to update', 'error'); btn.disabled = false; });
          });
        })(sub, pauseBtn);

        // Delete
        var delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'admin-btn admin-btn-danger';
        delBtn.textContent = 'Delete';
        (function (s) {
          delBtn.addEventListener('click', function () {
            _modal(
              'Delete Subscription',
              'Delete "' + s.name + '"? This will permanently stop all alerts.',
              'Delete',
              function () {
                fetch(API + '/subscriptions/' + s.api_key, { method: 'DELETE' })
                  .then(function () { _toast('Subscription deleted'); _renderWebhooks(content); })
                  .catch(function () { _toast('Failed to delete', 'error'); });
              }
            );
          });
        })(sub);

        tdActions.appendChild(pingBtn);
        tdActions.appendChild(pauseBtn);
        tdActions.appendChild(delBtn);

        tr.appendChild(tdName);
        tr.appendChild(tdFormat);
        tr.appendChild(tdPrio);
        tr.appendChild(tdDel);
        tr.appendChild(tdFail);
        tr.appendChild(tdStatus);
        tr.appendChild(tdCreated);
        tr.appendChild(tdActions);
        tbody.appendChild(tr);
      });

      table.appendChild(tbody);
      content.appendChild(table);
    }).catch(function (e) {
      _errorState(content, 'Failed to load subscriptions: ' + e.message);
    });
  }

  // ── SYSTEM TAB ──

  function _renderSystem(content) {
    fetch(API + '/admin/system').then(function (r) { return r.json(); }).then(function (data) {
      content.innerHTML = '';

      var title = document.createElement('h3');
      title.className = 'admin-section-title';
      title.textContent = 'System Status';
      content.appendChild(title);

      var mem = data.memory || {};
      var disk = data.disk || {};
      var load = data.load || {};

      var grid = document.createElement('div');
      grid.className = 'admin-stats-grid';
      [
        { v: data.uptime_seconds != null ? _formatUptime(data.uptime_seconds) : '—', l: 'Uptime' },
        { v: mem.percent != null ? mem.percent + '%' : '—', l: 'Memory', s: mem.used_mb != null ? mem.used_mb + ' / ' + mem.total_mb + ' MB' : '' },
        { v: disk.percent != null ? disk.percent + '%' : '—', l: 'Disk', s: disk.used_gb != null ? disk.used_gb + ' / ' + disk.total_gb + ' GB' : '' },
        { v: load['1m'] != null ? load['1m'] : '—', l: 'Load (1m)', s: load['5m'] != null ? '5m: ' + load['5m'] + ' · 15m: ' + load['15m'] : '' },
        { v: data.redis && data.redis.ok ? '✅ OK' : '❌ Down', l: 'Redis' },
        { v: data.qdrant && data.qdrant.ok ? '✅ OK' : '❌ Down', l: 'Qdrant' },
      ].forEach(function (c) { grid.appendChild(_statCard(c.v, c.l, c.s)); });
      content.appendChild(grid);

      // Docker containers
      if (data.docker_containers && data.docker_containers.length > 0) {
        var dockerTitle = document.createElement('h3');
        dockerTitle.className = 'admin-section-title';
        dockerTitle.textContent = 'Docker Containers';
        content.appendChild(dockerTitle);

        var dockerTable = document.createElement('table');
        dockerTable.className = 'admin-table';
        var dThead = document.createElement('thead');
        var dHeaderRow = document.createElement('tr');
        ['Container', 'Status'].forEach(function (h) {
          var th = document.createElement('th');
          th.textContent = h;
          dHeaderRow.appendChild(th);
        });
        dThead.appendChild(dHeaderRow);
        dockerTable.appendChild(dThead);
        var dTbody = document.createElement('tbody');
        data.docker_containers.forEach(function (c) {
          var tr = document.createElement('tr');
          var tdName = document.createElement('td');
          tdName.textContent = c.name;
          var tdStatus = document.createElement('td');
          var isUp = c.status && c.status.toLowerCase().indexOf('up') === 0;
          var b = document.createElement('span');
          b.className = 'admin-badge admin-badge-' + (isUp ? 'active' : 'error');
          b.textContent = c.status;
          tdStatus.appendChild(b);
          tr.appendChild(tdName);
          tr.appendChild(tdStatus);
          dTbody.appendChild(tr);
        });
        dockerTable.appendChild(dTbody);
        content.appendChild(dockerTable);
      }

      // Actions
      var actTitle = document.createElement('h3');
      actTitle.className = 'admin-section-title';
      actTitle.textContent = 'Actions';
      content.appendChild(actTitle);

      var actionsBar = document.createElement('div');
      actionsBar.className = 'admin-actions-bar';

      var flushBtn = document.createElement('button');
      flushBtn.type = 'button';
      flushBtn.className = 'admin-btn admin-btn-warn';
      flushBtn.textContent = 'Flush Cache';
      flushBtn.addEventListener('click', function () {
        _modal('Flush Cache', 'Remove all verse:* cache keys (subscription data is safe). Continue?', 'Flush', function () {
          fetch(API + '/admin/cache/flush', { method: 'POST' })
            .then(function (r) { return r.json(); })
            .then(function (d) { _toast('Cache flushed — ' + d.keys_removed + ' keys removed'); })
            .catch(function () { _toast('Failed to flush cache', 'error'); });
        });
      });

      var reindexBtn = document.createElement('button');
      reindexBtn.type = 'button';
      reindexBtn.className = 'admin-btn admin-btn-warn';
      reindexBtn.textContent = 'Trigger Full Re-index';
      reindexBtn.addEventListener('click', function () {
        _modal('Full Re-index', 'Trigger a complete wiki ingestion cycle. This may take several minutes.', 'Re-index', function () {
          fetch(API + '/admin/ingest', { method: 'POST' })
            .then(function () { _toast('Re-index triggered'); })
            .catch(function () { _toast('Failed to trigger re-index', 'error'); });
        });
      });

      actionsBar.appendChild(flushBtn);
      actionsBar.appendChild(reindexBtn);
      content.appendChild(actionsBar);
    }).catch(function (e) {
      _errorState(content, 'Failed to load system data: ' + e.message);
    });
  }

  // ── PUBLIC API ──

  function render() {
    if (_container) _render();
  }

  function destroy() {
    if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
    _container = null;
  }

  return { init: init, render: render, destroy: destroy };
})();
