/**
 * GlobalVox RSVP — Main Application Controller (Vanilla JS)
 * Coordinates campaign lifecycle, live metrics, table rendering, CSV imports, and detail modals.
 */

(function() {
    'use strict';

    // Application State
    const state = {
        currentCampaignId: null,
        campaigns: [],
        currentFilter: 'ALL',
        searchQuery: '',
        isExecuting: false
    };

    // DOM Elements
    const elements = {
        loginContainer: document.getElementById('login-container'),
        dashboardContainer: document.getElementById('dashboard-container'),
        userNav: document.getElementById('user-nav'),
        navUsername: document.getElementById('nav-username'),
        formLogin: document.getElementById('form-login'),
        loginUsername: document.getElementById('login-username'),
        loginPassword: document.getElementById('login-password'),
        btnQuickFill: document.getElementById('btn-quick-fill'),
        btnLogout: document.getElementById('btn-logout'),

        campaignSelector: document.getElementById('campaign-selector'),
        campaignStatusBadge: document.getElementById('campaign-status-badge'),
        metaEventName: document.getElementById('meta-event-name'),
        metaEventDate: document.getElementById('meta-event-date'),
        metaEventLocation: document.getElementById('meta-event-location'),
        btnStartCampaign: document.getElementById('btn-start-campaign'),
        startBtnText: document.getElementById('start-btn-text'),
        startBtnIcon: document.getElementById('start-btn-icon'),
        btnOpenNewCampaign: document.getElementById('btn-open-new-campaign'),
        btnOpenImport: document.getElementById('btn-open-import'),

        metricTotal: document.getElementById('metric-total'),
        metricConfirmed: document.getElementById('metric-confirmed'),
        metricDeclined: document.getElementById('metric-declined'),
        metricUndecided: document.getElementById('metric-undecided'),
        metricPending: document.getElementById('metric-pending'),
        metricFailed: document.getElementById('metric-failed'),

        tableSearch: document.getElementById('table-search'),
        inviteeTbody: document.getElementById('invitee-tbody'),
        filterTabs: document.querySelectorAll('.tab-btn'),

        modalNewCampaign: document.getElementById('modal-new-campaign'),
        formNewCampaign: document.getElementById('form-new-campaign'),
        modalImportCsv: document.getElementById('modal-import-csv'),
        csvFileInput: document.getElementById('csv-file-input'),
        btnPreviewCsv: document.getElementById('btn-preview-csv'),
        btnCommitCsv: document.getElementById('btn-commit-csv'),
        previewOutput: document.getElementById('preview-output'),
        previewSummaryPills: document.getElementById('preview-summary-pills'),
        previewErrorsBox: document.getElementById('preview-errors-box'),
        previewTbody: document.getElementById('preview-tbody'),

        modalInviteeDetail: document.getElementById('modal-invitee-detail'),
        detailName: document.getElementById('detail-name'),
        detailPhone: document.getElementById('detail-phone'),
        detailEmail: document.getElementById('detail-email'),
        detailStatus: document.getElementById('detail-status'),
        detailTimeline: document.getElementById('detail-timeline'),

        toastContainer: document.getElementById('toast-container')
    };

    // ==========================================
    // UI Helpers & Toasts
    // ==========================================
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        elements.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 200);
        }, 3500);
    }

    function openModal(modal) {
        if (modal) modal.classList.add('active');
    }

    function closeModal(modal) {
        if (modal) modal.classList.remove('active');
    }

    // Bind all close buttons
    document.querySelectorAll('[data-close]').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-close');
            closeModal(document.getElementById(targetId));
        });
    });

    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal(overlay);
        });
    });

    // ==========================================
    // Authentication Handlers
    // ==========================================
    function checkAuthState() {
        if (Auth.isAuthenticated()) {
            const user = Auth.getUser();
            elements.navUsername.textContent = user ? user.username : 'event_manager';
            elements.loginContainer.style.display = 'none';
            elements.dashboardContainer.style.display = 'block';
            elements.userNav.style.display = 'flex';
            loadInitialData();
        } else {
            elements.loginContainer.style.display = 'flex';
            elements.dashboardContainer.style.display = 'none';
            elements.userNav.style.display = 'none';
        }
    }

    elements.btnQuickFill.addEventListener('click', () => {
        elements.loginUsername.value = 'event_manager';
        elements.loginPassword.value = 'GlobalVox@2026!';
    });

    elements.formLogin.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = elements.loginUsername.value;
        const pass = elements.loginPassword.value;

        try {
            await Auth.login(user, pass);
            showToast('Signed in successfully.');
            checkAuthState();
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

    elements.btnLogout.addEventListener('click', async () => {
        await Auth.logout();
        showToast('Logged out successfully.');
        checkAuthState();
    });

    // ==========================================
    // Campaign Management
    // ==========================================
    async function loadInitialData() {
        try {
            const res = await Auth.authFetch('/api/campaigns/');
            if (!res.ok) throw new Error('Failed to load campaigns');
            const data = await res.json();
            state.campaigns = data.results || data || [];

            if (state.campaigns.length === 0) {
                // Seed the official assessment default campaign if none exists
                await createDefaultCampaign();
            } else {
                renderCampaignSelector();
                selectCampaign(state.campaigns[0].id);
            }
        } catch (err) {
            showToast(err.message, 'error');
        }
    }

    async function createDefaultCampaign() {
        try {
            const payload = {
                name: 'Annual Business Meet — RSVP',
                event_name: 'GlobalVox Annual Business Meet',
                event_date: '2026-10-25',
                event_location: 'Ahmedabad',
                objective: 'AI agent should contact each invitee and determine whether they will attend the event.',
                enroll_all_invitees: true
            };
            const res = await Auth.authFetch('/api/campaigns/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const newCamp = await res.json();
                state.campaigns = [newCamp];
                renderCampaignSelector();
                selectCampaign(newCamp.id);
            }
        } catch (e) {
            console.error(e);
        }
    }

    function renderCampaignSelector() {
        elements.campaignSelector.innerHTML = '';
        state.campaigns.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.name} (${c.event_name})`;
            elements.campaignSelector.appendChild(opt);
        });
    }

    elements.campaignSelector.addEventListener('change', (e) => {
        selectCampaign(parseInt(e.target.value));
    });

    async function selectCampaign(campaignId) {
        state.currentCampaignId = campaignId;
        elements.campaignSelector.value = campaignId;
        await refreshCampaignDetails();
        await loadInvitees();
    }

    async function refreshCampaignDetails() {
        if (!state.currentCampaignId) return;

        try {
            const res = await Auth.authFetch(`/api/campaigns/${state.currentCampaignId}/`);
            if (!res.ok) return;
            const camp = await res.json();

            // Meta
            elements.metaEventName.textContent = camp.event_name;
            elements.metaEventDate.textContent = camp.event_date;
            elements.metaEventLocation.textContent = camp.event_location;

            // Status Badge
            const status = camp.status;
            elements.campaignStatusBadge.textContent = status;
            elements.campaignStatusBadge.className = `badge badge-${status.toLowerCase()}`;

            // Metrics
            const m = camp.metrics || {};
            elements.metricTotal.textContent = (m.total_invitees || 0).toLocaleString();
            elements.metricConfirmed.textContent = (m.confirmed || 0).toLocaleString();
            elements.metricDeclined.textContent = (m.declined || 0).toLocaleString();
            elements.metricUndecided.textContent = (m.undecided || 0).toLocaleString();
            elements.metricPending.textContent = (m.pending || 0).toLocaleString();
            elements.metricFailed.textContent = (m.failed || 0).toLocaleString();

            // Start button state
            if (status === 'COMPLETED') {
                elements.btnStartCampaign.disabled = true;
                elements.startBtnText.textContent = 'Campaign Completed';
                elements.startBtnIcon.textContent = '✅';
            } else if (status === 'RUNNING') {
                elements.btnStartCampaign.disabled = true;
                elements.startBtnText.textContent = 'Running Calls...';
                elements.startBtnIcon.textContent = '⏳';
            } else {
                elements.btnStartCampaign.disabled = false;
                elements.startBtnText.textContent = 'Start Campaign';
                elements.startBtnIcon.textContent = '📞';
            }
        } catch (err) {
            console.error('Error refreshing campaign:', err);
        }
    }

    // ==========================================
    // Campaign Execution Handlers
    // ==========================================
    elements.btnStartCampaign.addEventListener('click', async () => {
        if (!state.currentCampaignId || state.isExecuting) return;

        if (!confirm('Initiate AI Voice Calling campaign for all pending invitees?')) return;

        state.isExecuting = true;
        elements.btnStartCampaign.disabled = true;
        elements.startBtnText.textContent = 'Calling in progress...';
        elements.startBtnIcon.textContent = '⏳';

        try {
            const res = await Auth.authFetch(`/api/campaigns/${state.currentCampaignId}/start/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            const data = await res.json();
            if (!res.ok) {
                const msg = data.error ? data.error.message : 'Failed to start campaign';
                throw new Error(msg);
            }

            showToast(`Campaign completed! ${data.calls_dispatched} calls processed (${data.successful_calls} connected).`);
            await refreshCampaignDetails();
            await loadInvitees();
        } catch (err) {
            showToast(err.message, 'error');
            await refreshCampaignDetails();
        } finally {
            state.isExecuting = false;
        }
    });

    // ==========================================
    // Invitee Table & Filtering
    // ==========================================
    async function loadInvitees() {
        if (!state.currentCampaignId) return;

        let url = `/api/campaigns/${state.currentCampaignId}/invitees/?`;
        if (state.currentFilter !== 'ALL') {
            url += `rsvp_status=${encodeURIComponent(state.currentFilter)}&`;
        }
        if (state.searchQuery) {
            url += `search=${encodeURIComponent(state.searchQuery)}&`;
        }

        try {
            const res = await Auth.authFetch(url);
            if (!res.ok) throw new Error('Failed to load invitees');
            const data = await res.json();
            const results = data.results || data || [];
            renderInviteeTable(results);
        } catch (err) {
            console.error(err);
        }
    }

    function renderInviteeTable(invitees) {
        elements.inviteeTbody.innerHTML = '';

        if (invitees.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 8;
            td.style.textAlign = 'center';
            td.style.padding = '2rem';
            td.style.color = 'var(--text-muted)';
            td.textContent = 'No invitees match the selected criteria.';
            tr.appendChild(td);
            elements.inviteeTbody.appendChild(tr);
            return;
        }

        invitees.forEach(inv => {
            const tr = document.createElement('tr');

            // 1. Name
            const tdName = document.createElement('td');
            tdName.style.fontWeight = '600';
            tdName.textContent = inv.name;
            tr.appendChild(tdName);

            // 2. Masked Phone
            const tdPhone = document.createElement('td');
            tdPhone.className = 'cell-masked';
            tdPhone.textContent = inv.phone_masked;
            tr.appendChild(tdPhone);

            // 3. Email
            const tdEmail = document.createElement('td');
            tdEmail.style.color = 'var(--text-secondary)';
            tdEmail.textContent = inv.email;
            tr.appendChild(tdEmail);

            // 4. RSVP Status Badge
            const tdRsvp = document.createElement('td');
            const rBadge = document.createElement('span');
            rBadge.className = `badge badge-${inv.rsvp_status.toLowerCase()}`;
            rBadge.textContent = inv.rsvp_status;
            tdRsvp.appendChild(rBadge);
            tr.appendChild(tdRsvp);

            // 5. Call Status Badge
            const tdCall = document.createElement('td');
            const cBadge = document.createElement('span');
            cBadge.className = `badge badge-${inv.call_status.toLowerCase()}`;
            cBadge.textContent = inv.call_status;
            tdCall.appendChild(cBadge);
            tr.appendChild(tdCall);

            // 6. Attempts
            const tdAttempts = document.createElement('td');
            tdAttempts.style.textAlign = 'center';
            tdAttempts.textContent = inv.attempt_count;
            tr.appendChild(tdAttempts);

            // 7. Notes
            const tdNotes = document.createElement('td');
            tdNotes.className = 'cell-notes';
            tdNotes.textContent = inv.notes || '—';
            tdNotes.title = inv.notes || '';
            tr.appendChild(tdNotes);

            // 8. Action
            const tdAction = document.createElement('td');
            const btnInspect = document.createElement('button');
            btnInspect.className = 'btn btn-secondary';
            btnInspect.style.padding = '0.3rem 0.65rem';
            btnInspect.style.fontSize = '0.75rem';
            btnInspect.textContent = 'View Details';
            btnInspect.addEventListener('click', () => openInviteeDetail(inv));
            tdAction.appendChild(btnInspect);
            tr.appendChild(tdAction);

            elements.inviteeTbody.appendChild(tr);
        });
    }

    // Tab Filter Handlers
    elements.filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            elements.filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            state.currentFilter = tab.getAttribute('data-filter');
            loadInvitees();
        });
    });

    // Search Input Debounce
    let searchTimer = null;
    elements.tableSearch.addEventListener('input', (e) => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.searchQuery = e.target.value.trim();
            loadInvitees();
        }, 300);
    });

    // ==========================================
    // Individual Invitee Inspection Modal
    // ==========================================
    async function openInviteeDetail(inv) {
        elements.detailName.textContent = inv.name;
        elements.detailPhone.textContent = inv.phone_masked;
        elements.detailEmail.textContent = inv.email;
        elements.detailStatus.innerHTML = `<span class="badge badge-${inv.rsvp_status.toLowerCase()}">${inv.rsvp_status}</span> <span class="badge badge-${inv.call_status.toLowerCase()}">${inv.call_status}</span>`;

        elements.detailTimeline.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1rem 0;">Loading complete call history audit trail...</div>';
        openModal(elements.modalInviteeDetail);

        try {
            const res = await Auth.authFetch(`/api/campaigns/${inv.campaign_id}/invitees/${inv.invitee_id}/`);
            if (!res.ok) throw new Error('Failed to load call history details');
            const data = await res.json();

            // Refresh metadata
            elements.detailName.textContent = data.invitee.name;
            elements.detailPhone.textContent = data.invitee.phone_masked;
            elements.detailEmail.textContent = data.invitee.email;
            elements.detailStatus.innerHTML = `
                <span class="badge badge-${data.rsvp_status.toLowerCase()}">${data.rsvp_status}</span>
                <span class="badge badge-${data.call_status.toLowerCase()}">${data.call_status}</span>
                <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 0.5rem;">(${data.attempt_count} attempts)</span>
            `;

            elements.detailTimeline.innerHTML = '';
            const attempts = data.attempts || [];

            if (attempts.length === 0) {
                elements.detailTimeline.innerHTML = `
                    <div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.75rem 0;">
                        No calls attempted yet for this contact in <strong>${data.campaign.name}</strong>.
                        Click <em>"Start Campaign"</em> to initiate the automated voice calling process.
                    </div>
                `;
                return;
            }

            attempts.forEach(att => {
                const item = document.createElement('div');
                item.className = 'timeline-item';

                const time = document.createElement('div');
                time.className = 'timeline-time';
                const dateStr = att.started_at ? new Date(att.started_at).toLocaleString() : 'Just now';
                time.innerHTML = `<strong>Attempt #${att.attempt_number}</strong> &bull; ${dateStr} &bull; Duration: <strong>${att.duration_seconds}s</strong>`;

                const headerPills = document.createElement('div');
                headerPills.style.margin = '0.35rem 0';
                
                const sBadge = document.createElement('span');
                sBadge.className = `badge badge-${att.status.toLowerCase()}`;
                sBadge.textContent = att.status;
                
                const oBadge = document.createElement('span');
                oBadge.className = `badge badge-${(att.rsvp_outcome || 'pending').toLowerCase()}`;
                oBadge.textContent = `Outcome: ${att.rsvp_outcome}`;
                oBadge.style.marginLeft = '0.35rem';
                
                const idSpan = document.createElement('span');
                idSpan.style.fontFamily = 'monospace';
                idSpan.style.fontSize = '0.75rem';
                idSpan.style.color = 'var(--text-muted)';
                idSpan.style.marginLeft = '0.5rem';
                idSpan.textContent = `ID: ${att.provider_call_id}`;

                headerPills.appendChild(sBadge);
                headerPills.appendChild(oBadge);
                headerPills.appendChild(idSpan);

                const desc = document.createElement('div');
                desc.className = 'timeline-desc';
                desc.textContent = att.transcript_summary || 'No transcript summary recorded.';

                if (att.error_code) {
                    const errBox = document.createElement('div');
                    errBox.style.marginTop = '0.35rem';
                    errBox.style.color = '#f87171';
                    errBox.style.fontSize = '0.75rem';
                    errBox.textContent = `Carrier Error [${att.error_code}]: ${att.error_message}`;
                    desc.appendChild(errBox);
                }

                item.appendChild(time);
                item.appendChild(headerPills);
                item.appendChild(desc);
                elements.detailTimeline.appendChild(item);
            });
        } catch (e) {
            elements.detailTimeline.innerHTML = `<div style="color: var(--status-failed); padding: 0.75rem 0;">Error loading call attempts: ${e.message}</div>`;
        }
    }

    // ==========================================
    // New Campaign Modal Handlers
    // ==========================================
    elements.btnOpenNewCampaign.addEventListener('click', () => {
        openModal(elements.modalNewCampaign);
    });

    elements.formNewCampaign.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('camp-name').value.trim(),
            event_name: document.getElementById('camp-event-name').value.trim(),
            event_date: document.getElementById('camp-event-date').value,
            event_location: document.getElementById('camp-event-location').value.trim(),
            objective: document.getElementById('camp-objective').value.trim(),
            enroll_all_invitees: document.getElementById('camp-enroll-all').checked
        };

        try {
            const res = await Auth.authFetch('/api/campaigns/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error ? data.error.message : 'Campaign creation failed');

            showToast(`Campaign "${payload.name}" created successfully.`);
            closeModal(elements.modalNewCampaign);
            elements.formNewCampaign.reset();
            await loadInitialData();
            selectCampaign(data.id);
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

    // ==========================================
    // CSV Import Modal Handlers
    // ==========================================
    let stagedCsvFile = null;

    elements.btnOpenImport.addEventListener('click', () => {
        elements.csvFileInput.value = '';
        elements.previewOutput.style.display = 'none';
        elements.btnCommitCsv.disabled = true;
        stagedCsvFile = null;
        openModal(elements.modalImportCsv);
    });

    elements.csvFileInput.addEventListener('change', (e) => {
        stagedCsvFile = e.target.files[0] || null;
        elements.previewOutput.style.display = 'none';
        elements.btnCommitCsv.disabled = true;
    });

    elements.btnPreviewCsv.addEventListener('click', async () => {
        if (!stagedCsvFile) {
            showToast('Please select a CSV file first.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', stagedCsvFile);
        formData.append('preview_only', 'true');

        try {
            elements.btnPreviewCsv.disabled = true;
            elements.btnPreviewCsv.textContent = 'Validating...';

            const token = Auth.getAccessToken();
            const res = await fetch('/api/invitees/import/?preview_only=true', {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });

            const data = await res.json();
            if (!res.ok) {
                const msg = data.error ? data.error.message : (data.file ? data.file[0] : 'Validation failed.');
                throw new Error(msg);
            }

            renderCsvPreview(data);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            elements.btnPreviewCsv.disabled = false;
            elements.btnPreviewCsv.textContent = '🔍 Validate & Preview';
        }
    });

    function renderCsvPreview(data) {
        elements.previewOutput.style.display = 'block';
        elements.previewSummaryPills.innerHTML = `
            <span class="badge" style="background: #1e293b; color: #fff;">Total: ${data.total_rows}</span>
            <span class="badge badge-confirmed">Valid: ${data.valid_count}</span>
            <span class="badge badge-failed">Invalid: ${data.invalid_count}</span>
        `;

        // Render errors
        elements.previewErrorsBox.innerHTML = '';
        if (data.errors && data.errors.length > 0) {
            const errList = document.createElement('div');
            errList.style.background = 'rgba(239, 68, 68, 0.1)';
            errList.style.border = '1px solid rgba(239, 68, 68, 0.3)';
            errList.style.borderRadius = 'var(--radius-sm)';
            errList.style.padding = '0.75rem';
            errList.style.fontSize = '0.75rem';
            errList.style.color = '#fca5a5';
            errList.style.maxHeight = '120px';
            errList.style.overflowY = 'auto';

            data.errors.forEach(err => {
                const item = document.createElement('div');
                item.textContent = `Row ${err.row}: ${err.reasons.join('; ')}`;
                errList.appendChild(item);
            });
            elements.previewErrorsBox.appendChild(errList);
        }

        // Render sample valid
        elements.previewTbody.innerHTML = '';
        (data.sample_valid || []).forEach(row => {
            const tr = document.createElement('tr');
            const tdName = document.createElement('td');
            tdName.textContent = row.name;
            const tdPhone = document.createElement('td');
            tdPhone.textContent = row.phone;
            const tdEmail = document.createElement('td');
            tdEmail.textContent = row.email;
            tr.appendChild(tdName);
            tr.appendChild(tdPhone);
            tr.appendChild(tdEmail);
            elements.previewTbody.appendChild(tr);
        });

        // Enable commit if valid rows exist
        elements.btnCommitCsv.disabled = data.valid_count === 0;
    }

    elements.btnCommitCsv.addEventListener('click', async () => {
        if (!stagedCsvFile) return;

        const formData = new FormData();
        formData.append('file', stagedCsvFile);
        formData.append('preview_only', 'false');

        try {
            elements.btnCommitCsv.disabled = true;
            elements.btnCommitCsv.textContent = 'Importing...';

            const token = Auth.getAccessToken();
            const res = await fetch('/api/invitees/import/', {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error ? data.error.message : 'Import failed');

            showToast(`Successfully imported ${data.imported_count} invitees!`);
            closeModal(elements.modalImportCsv);

            // Re-enroll in current campaign if user desires
            if (state.currentCampaignId) {
                // Refresh metrics and table
                await refreshCampaignDetails();
                await loadInvitees();
            }
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            elements.btnCommitCsv.disabled = false;
            elements.btnCommitCsv.textContent = '💾 Commit to Database';
        }
    });

    // ==========================================
    // Bootstrap
    // ==========================================
    document.addEventListener('DOMContentLoaded', () => {
        checkAuthState();
    });

})();
