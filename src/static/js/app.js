/* Warframe Relic Tracker - Client-Side SPA */

(function() {
    'use strict';

    // API Base
    var API_BASE = '';

    // Current state
    var currentView = 'dashboard';
    var relicsData = [];
    var overviewData = null;
    var currentFilter = {
        tier: null,
        vaulted: null,
        obtained: null,
        search: ''
    };

    // DOM helpers
    function $(sel) { return document.querySelector(sel); }
    function $$(sel) { return document.querySelectorAll(sel); }

    function el(tag, attrs, children) {
        var e = document.createElement(tag);
        if (attrs) {
            for (var k in attrs) {
                if (k === 'className') e.className = attrs[k];
                else if (k === 'innerHTML') e.innerHTML = attrs[k];
                else if (k === 'textContent') e.textContent = attrs[k];
                else if (k.indexOf('on') === 0) e.addEventListener(k.substring(2).toLowerCase(), attrs[k]);
                else e.setAttribute(k, attrs[k]);
            }
        }
        if (children) {
            if (typeof children === 'string') e.innerHTML = children;
            else if (Array.isArray(children)) {
                children.forEach(function(c) { if (c) e.appendChild(c); });
            }
        }
        return e;
    }

    // API client
    function apiGet(path) {
        return fetch(API_BASE + path)
            .then(function(r) {
                if (!r.ok) throw new Error('API error: ' + r.status);
                return r.json();
            });
    }

    function apiPost(path) {
        return fetch(API_BASE + path, { method: 'POST' })
            .then(function(r) {
                if (!r.ok) throw new Error('API error: ' + r.status);
                return r.json();
            });
    }

    // Sync data
    window.syncData = function() {
        var statusEl = $('#sync-status');
        statusEl.textContent = 'Syncing...';
        apiPost('/api/sync')
            .then(function(data) {
                statusEl.textContent = 'Sync complete!';
                setTimeout(function() { statusEl.textContent = ''; }, 3000);
                refreshCurrentView();
            })
            .catch(function(err) {
                statusEl.textContent = 'Sync failed: ' + err.message;
            });
    };

    // Show loading
    function showLoading() {
        $('#content').innerHTML = '<div class="loading">Loading...</div>';
    }

    // Show error
    function showError(msg) {
        $('#content').innerHTML = '<div class="error-message">' + escapeHtml(msg) + '</div>';
    }

    // Escape HTML
    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Tier tag class
    function tierClass(tier) {
        return 'tag tag-' + (tier || '').toLowerCase();
    }

    // Rarity class
    function rarityClass(rarity) {
        if (!rarity) return '';
        var r = rarity.toLowerCase();
        if (r === 'common') return 'rarity-common';
        if (r === 'uncommon') return 'rarity-uncommon';
        if (r === 'rare') return 'rarity-rare';
        return '';
    }

    // Router
    function navigate(view) {
        currentView = view;
        window.location.hash = view;

        // Update nav
        $$('.nav-link').forEach(function(link) {
            link.classList.remove('active');
            if (link.getAttribute('data-view') === view) {
                link.classList.add('active');
            }
        });

        loadView(view);
    }

    function loadView(view) {
        showLoading();

        switch (view) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'relics':
                loadRelics();
                break;
            case 'collection':
                loadCollection();
                break;
            default:
                loadDashboard();
        }
    }

    // Dashboard view
    function loadDashboard() {
        apiGet('/api/overview')
            .then(function(data) {
                overviewData = data;
                renderDashboard(data);
            })
            .catch(function(err) {
                showError('Failed to load dashboard: ' + err.message);
            });
    }

    function renderDashboard(data) {
        var html = '';

        html += '<div class="view-header"><h2>Dashboard</h2></div>';

        // Stats panel
        html += '<div class="panel">';
        html += '<div class="panel-header">Overview Statistics</div>';
        html += '<div class="panel-body">';
        html += '<table class="stats-table">';
        html += '<tr><td class="stats-label">Total Relics:</td><td class="stats-value">' + (data.total_relics || 0) + '</td></tr>';
        html += '<tr><td class="stats-label">Obtained:</td><td class="stats-value">' + (data.obtained_relics || 0) + '</td></tr>';
        html += '<tr><td class="stats-label">Vaulted:</td><td class="stats-value">' + (data.vaulted_relics || 0) + '</td></tr>';
        html += '<tr><td class="stats-label">Total Ducat Value:</td><td class="stats-value ducat-value">' + (data.total_ducat_value || 0) + ' ducats</td></tr>';
        html += '<tr><td class="stats-label">Completion:</td><td class="stats-value">';
        var pct = data.completion_pct || 0;
        html += '<div class="progress-bar"><div class="progress-fill" style="width: ' + pct + '%;"></div></div> ';
        html += pct.toFixed(1) + '%</td></tr>';
        html += '</table>';
        html += '</div></div>';

        // Tier breakdown
        if (data.by_tier && data.by_tier.length) {
            html += '<div class="panel">';
            html += '<div class="panel-header">Tier Breakdown</div>';
            html += '<div class="panel-body">';
            html += '<table>';
            html += '<tr><th>Tier</th><th>Total</th><th>Obtained</th><th>Progress</th></tr>';
            data.by_tier.forEach(function(t) {
                var tierPct = t.total > 0 ? ((t.obtained / t.total) * 100).toFixed(1) : '0.0';
                html += '<tr>';
                html += '<td><span class="' + tierClass(t.tier) + '">' + escapeHtml(t.tier) + '</span></td>';
                html += '<td>' + t.total + '</td>';
                html += '<td>' + t.obtained + '</td>';
                html += '<td><div class="progress-bar"><div class="progress-fill" style="width: ' + tierPct + '%;"></div></div> ' + tierPct + '%</td>';
                html += '</tr>';
            });
            html += '</table>';
            html += '</div></div>';
        }

        $('#content').innerHTML = html;
    }

    // Relics view
    function loadRelics() {
        var params = buildFilterParams();
        var url = '/api/relics' + (params ? '?' + params : '');

        apiGet(url)
            .then(function(data) {
                relicsData = data;
                renderRelics(data);
            })
            .catch(function(err) {
                showError('Failed to load relics: ' + err.message);
            });
    }

    function buildFilterParams() {
        var parts = [];
        if (currentFilter.tier) parts.push('tier=' + encodeURIComponent(currentFilter.tier));
        if (currentFilter.vaulted !== null) parts.push('vaulted=' + currentFilter.vaulted);
        if (currentFilter.obtained !== null) parts.push('obtained=' + currentFilter.obtained);
        return parts.join('&');
    }

    function renderRelics(data) {
        var html = '';

        html += '<div class="view-header"><h2>Relic Browser</h2></div>';

        // Filter controls
        html += '<div class="filter-controls">';
        html += '<div class="filter-group">';
        html += '<span class="filter-label">Tier:</span> ';
        html += '<a href="javascript:void(0)" onclick="filterTier(null)" class="' + (!currentFilter.tier ? 'active-filter' : '') + '">All</a> ';
        html += '<a href="javascript:void(0)" onclick="filterTier(\'Lith\')" class="' + (currentFilter.tier === 'Lith' ? 'active-filter' : '') + '"><span class="' + tierClass('Lith') + '">Lith</span></a> ';
        html += '<a href="javascript:void(0)" onclick="filterTier(\'Meso\')" class="' + (currentFilter.tier === 'Meso' ? 'active-filter' : '') + '"><span class="' + tierClass('Meso') + '">Meso</span></a> ';
        html += '<a href="javascript:void(0)" onclick="filterTier(\'Neo\')" class="' + (currentFilter.tier === 'Neo' ? 'active-filter' : '') + '"><span class="' + tierClass('Neo') + '">Neo</span></a> ';
        html += '<a href="javascript:void(0)" onclick="filterTier(\'Axi\')" class="' + (currentFilter.tier === 'Axi' ? 'active-filter' : '') + '"><span class="' + tierClass('Axi') + '">Axi</span></a> ';
        html += '</div>';
        html += '<div class="filter-group">';
        html += '<label><input type="checkbox" id="filter-vaulted" ' + (currentFilter.vaulted === 'true' ? 'checked' : '') + ' onchange="filterVaulted(this.checked)"> Vaulted Only</label> ';
        html += '<label><input type="checkbox" id="filter-obtained" ' + (currentFilter.obtained === 'true' ? 'checked' : '') + ' onchange="filterObtained(this.checked)"> Obtained Only</label> ';
        html += '</div>';
        html += '</div>';

        // Search
        html += '<div class="search-box">';
        html += '<input type="text" id="search-input" placeholder="Search relics..." value="' + escapeHtml(currentFilter.search) + '" oninput="searchRelics(this.value)"> ';
        html += '<span class="toolbar-text">' + data.length + ' relics</span>';
        html += '</div>';

        // Relics table
        var filtered = filterBySearch(data, currentFilter.search);

        if (filtered.length === 0) {
            html += '<div class="empty-state">No relics found matching your criteria.</div>';
        } else {
            html += '<div class="panel">';
            html += '<table>';
            html += '<tr><th>Name</th><th>Tier</th><th>Status</th><th>Qty</th><th>Drops</th><th>Ducats</th><th>Vaulted</th></tr>';
            filtered.forEach(function(r) {
                var name = r.name || 'Unknown';
                var id = r.id;
                html += '<tr class="clickable-row" onclick="openRelic(' + id + ')">';
                html += '<td><a class="row-link">' + escapeHtml(name) + '</a></td>';
                html += '<td><span class="' + tierClass(r.tier) + '">' + escapeHtml(r.tier) + '</span></td>';
                html += '<td class="' + (r.obtained ? 'status-obtained' : 'status-missing') + '">' + (r.obtained ? 'Obtained' : 'Missing') + '</td>';
                html += '<td class="quantity">' + (r.quantity || 0) + '</td>';
                html += '<td>' + (r.drop_count || 0) + '</td>';
                html += '<td class="ducat-value">' + (r.total_ducats || 0) + '</td>';
                html += '<td>' + (r.vaulted ? '<span class="vaulted">VAULTED</span>' : '-') + '</td>';
                html += '</tr>';
            });
            html += '</table>';
            html += '</div>';
        }

        $('#content').innerHTML = html;
    }

    function filterBySearch(data, query) {
        if (!query) return data;
        var q = query.toLowerCase();
        return data.filter(function(r) {
            return (r.name || '').toLowerCase().indexOf(q) !== -1;
        });
    }

    // Filter functions (global)
    window.filterTier = function(tier) {
        currentFilter.tier = tier;
        loadRelics();
    };

    window.filterVaulted = function(checked) {
        currentFilter.vaulted = checked ? 'true' : null;
        loadRelics();
    };

    window.filterObtained = function(checked) {
        currentFilter.obtained = checked ? 'true' : null;
        loadRelics();
    };

    window.searchRelics = function(query) {
        currentFilter.search = query;
        // Re-render with existing data
        if (relicsData) {
            renderRelics(relicsData);
        }
    };

    // Collection view
    function loadCollection() {
        apiGet('/api/relics?obtained=true')
            .then(function(data) {
                renderCollection(data);
            })
            .catch(function(err) {
                // Try loading all and filter client-side
                apiGet('/api/relics')
                    .then(function(data) {
                        var obtained = data.filter(function(r) { return r.obtained; });
                        renderCollection(obtained);
                    })
                    .catch(function(err2) {
                        showError('Failed to load collection: ' + err2.message);
                    });
            });
    }

    function renderCollection(data) {
        var html = '';

        html += '<div class="view-header"><h2>My Collection</h2></div>';

        if (!data || data.length === 0) {
            html += '<div class="empty-state">No relics obtained yet. Start tracking your collection!</div>';
            $('#content').innerHTML = html;
            return;
        }

        // Summary
        var totalQty = 0;
        var totalDucats = 0;
        data.forEach(function(r) {
            totalQty += (r.quantity || 0);
            totalDucats += (r.total_ducats || 0);
        });

        html += '<div class="panel">';
        html += '<div class="panel-header">Collection Summary</div>';
        html += '<div class="panel-body">';
        html += '<table class="stats-table">';
        html += '<tr><td class="stats-label">Relics Obtained:</td><td class="stats-value">' + data.length + '</td></tr>';
        html += '<tr><td class="stats-label">Total Quantity:</td><td class="stats-value">' + totalQty + '</td></tr>';
        html += '<tr><td class="stats-label">Total Ducat Value:</td><td class="stats-value ducat-value">' + totalDucats + ' ducats</td></tr>';
        html += '</table>';
        html += '</div></div>';

        // Collection table
        html += '<div class="panel">';
        html += '<div class="panel-header">Obtained Relics</div>';
        html += '<div class="panel-body">';
        html += '<table>';
        html += '<tr><th>Name</th><th>Tier</th><th>Qty</th><th>Drops</th><th>Ducats</th><th>Vaulted</th></tr>';
        data.forEach(function(r) {
            html += '<tr class="clickable-row" onclick="openRelic(' + r.id + ')">';
            html += '<td><a class="row-link">' + escapeHtml(r.name) + '</a></td>';
            html += '<td><span class="' + tierClass(r.tier) + '">' + escapeHtml(r.tier) + '</span></td>';
            html += '<td class="quantity">' + (r.quantity || 0) + '</td>';
            html += '<td>' + (r.drop_count || 0) + '</td>';
            html += '<td class="ducat-value">' + (r.total_ducats || 0) + '</td>';
            html += '<td>' + (r.vaulted ? '<span class="vaulted">VAULTED</span>' : '-') + '</td>';
            html += '</tr>';
        });
        html += '</table>';
        html += '</div></div>';

        $('#content').innerHTML = html;
    }

    // Relic detail modal
    window.openRelic = function(id) {
        var overlay = $('#modal-overlay');
        var content = $('#modal-content');

        overlay.style.display = 'block';
        content.innerHTML = '<div class="modal-header"><span class="close-btn" onclick="closeModal()">&times;</span> Loading...</div><div class="modal-body"><div class="loading">Loading relic details...</div></div>';

        apiGet('/api/relics/' + id)
            .then(function(data) {
                renderRelicModal(data);
            })
            .catch(function(err) {
                content.innerHTML = '<div class="modal-header"><span class="close-btn" onclick="closeModal()">&times;</span> Error</div><div class="modal-body"><div class="error-message">Failed to load relic details.</div></div>';
            });
    };

    function renderRelicModal(data) {
        var content = $('#modal-content');
        var html = '';

        html += '<div class="modal-header">';
        html += '<span class="close-btn" onclick="closeModal()">&times;</span>';
        html += escapeHtml(data.name);
        if (data.vaulted) html += ' <span class="vaulted">VAULTED</span>';
        html += '</div>';

        html += '<div class="modal-body">';

        // Info table
        html += '<table class="stats-table">';
        html += '<tr><td class="stats-label">Tier:</td><td><span class="' + tierClass(data.tier) + '">' + escapeHtml(data.tier) + '</span></td></tr>';
        html += '<tr><td class="stats-label">Status:</td><td class="' + (data.obtained ? 'status-obtained' : 'status-missing') + '">' + (data.obtained ? 'Obtained' : 'Missing') + '</td></tr>';
        html += '<tr><td class="stats-label">Quantity:</td><td class="quantity">' + (data.quantity || 0) + ' ';
        html += '<button class="btn btn-small" onclick="changeQty(' + data.id + ', -1)">-</button> ';
        html += '<button class="btn btn-small" onclick="changeQty(' + data.id + ', 1)">+</button>';
        html += '</td></tr>';
        if (data.introduced) {
            html += '<tr><td class="stats-label">Introduced:</td><td>' + escapeHtml(data.introduced) + '</td></tr>';
        }
        if (data.vaulted_version) {
            html += '<tr><td class="stats-label">Vaulted Version:</td><td>' + escapeHtml(data.vaulted_version) + '</td></tr>';
        }
        html += '<tr><td class="stats-label">Baro Item:</td><td>' + (data.is_baro ? 'Yes' : 'No') + '</td></tr>';
        if (data.notes) {
            html += '<tr><td class="stats-label">Notes:</td><td>' + escapeHtml(data.notes) + '</td></tr>';
        }
        html += '</table>';

        // Toggle obtained
        html += '<div style="margin: 10px 0;">';
        html += '<button class="btn btn-primary" onclick="toggleObtained(' + data.id + ')">' + (data.obtained ? 'Mark as Not Obtained' : 'Mark as Obtained') + '</button>';
        html += '</div>';

        // Drops table
        if (data.drops && data.drops.length > 0) {
            html += '<div class="section">';
            html += '<strong>Drop Table:</strong>';
            html += '<table>';
            html += '<tr><th>Item</th><th>Part</th><th>Rarity</th><th>Count</th><th>Ducats</th></tr>';
            data.drops.forEach(function(drop) {
                html += '<tr>';
                html += '<td>' + escapeHtml(drop.item_name) + '</td>';
                html += '<td>' + escapeHtml(drop.part_name) + '</td>';
                html += '<td><span class="' + rarityClass(drop.rarity) + '">' + escapeHtml(drop.rarity) + '</span></td>';
                html += '<td>' + (drop.item_count || 1) + '</td>';
                html += '<td class="ducat-value">' + (drop.ducat_value || 0) + '</td>';
                html += '</tr>';
            });
            html += '</table>';
            html += '</div>';
        }

        html += '</div>';

        html += '<div class="modal-footer">';
        html += '<button class="btn" onclick="closeModal()">Close</button>';
        html += '</div>';

        content.innerHTML = html;
    }

    window.closeModal = function() {
        $('#modal-overlay').style.display = 'none';
    };

    window.toggleObtained = function(id) {
        apiPost('/api/collection/' + id + '/toggle')
            .then(function() {
                closeModal();
                refreshCurrentView();
            })
            .catch(function(err) {
                alert('Failed to update: ' + err.message);
            });
    };

    window.changeQty = function(id, delta) {
        // Get current qty from modal, estimate
        var qtyEl = document.querySelector('.quantity');
        if (qtyEl) {
            var current = parseInt(qtyEl.textContent) || 0;
            var newQty = Math.max(0, current + delta);
            apiPost('/api/collection/' + id + '/quantity?qty=' + newQty)
                .then(function() {
                    // Refresh modal
                    openRelic(id);
                })
                .catch(function(err) {
                    alert('Failed to update quantity: ' + err.message);
                });
        }
    };

    // Refresh current view
    function refreshCurrentView() {
        loadView(currentView);
    }

    // Hash routing
    function handleHashChange() {
        var hash = window.location.hash.replace('#', '') || 'dashboard';
        if (hash !== currentView) {
            navigate(hash);
        }
    }

    // Init
    function init() {
        window.addEventListener('hashchange', handleHashChange);

        // Close modal on overlay click
        $('#modal-overlay').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        // Nav links
        $$('.nav-link').forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                var view = this.getAttribute('data-view');
                navigate(view);
            });
        });

        // Initial load: sync then dashboard
        var hash = window.location.hash.replace('#', '') || 'dashboard';
        currentView = hash;

        // Update nav active state
        $$('.nav-link').forEach(function(link) {
            link.classList.remove('active');
            if (link.getAttribute('data-view') === hash) {
                link.classList.add('active');
            }
        });

        showLoading();
        apiPost('/api/sync')
            .then(function() {
                loadView(currentView);
            })
            .catch(function() {
                // Sync failed, try loading anyway
                loadView(currentView);
            });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
