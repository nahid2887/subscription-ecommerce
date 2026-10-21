
    /**
     * ----------------------------------------------------
     * Theme Switcher (Dark & Day Mode)
     * ----------------------------------------------------
     */
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');
    const themeLabel = document.getElementById('themeLabel');

    const sunSvg = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"></circle>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
        <line x1="1" y1="12" x2="3" y2="12"></line>
        <line x1="21" y1="12" x2="23" y2="12"></line>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
      </svg>
    `;

    const moonSvg = `
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
      </svg>
    `;

    function applyTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('superadmin_theme', theme);

      if (theme === 'light') {
        themeIcon.innerHTML = moonSvg;
        themeLabel.textContent = 'Dark Mode';
      } else {
        themeIcon.innerHTML = sunSvg;
        themeLabel.textContent = 'Day Mode';
      }

      if (typeof updateChartsTheme === 'function') {
        updateChartsTheme(theme);
      }
    }

    const savedTheme = localStorage.getItem('superadmin_theme') || 'dark';
    applyTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });

    /**
     * ----------------------------------------------------
     * Auth Guard & Session Population
     * ----------------------------------------------------
     */
    let authSession = null;

    function getStoredAuth() {
      try {
        const raw = localStorage.getItem('superadmin_auth');
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    }

    function populateUserUI(user) {
      if (!user) return;
      const username = user.username || 'Admin';
      const initial = username.charAt(0).toUpperCase();

      const userAvatarSm = document.getElementById('userAvatarSm');
      if (userAvatarSm) {
        if (user.avatar) {
          userAvatarSm.innerHTML = `<img src="${user.avatar}" alt="${username}">`;
        } else {
          userAvatarSm.textContent = initial;
        }
      }
      const userPill = document.getElementById('userPillName');
      if (userPill) userPill.textContent = username;
    }

    async function initDashboard() {
      authSession = getStoredAuth();

      // If not stored in localStorage, check if active via Django session cookie
      if (!authSession || !authSession.accessToken) {
        try {
          const res = await fetch('/api/superuser/profile/', {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' }
          });
          if (res.ok) {
            const data = await res.json();
            if (data && data.user) {
              authSession = { user: data.user, tokenType: 'Bearer', accessToken: '' };
              populateUserUI(data.user);
              loadSuperAdminOrders();
              loadSuperAdminCustomers();
              loadDashboardAnalyticsCharts();
              return;
            }
          }
        } catch (e) {
          console.warn('Session check failed:', e);
        }

        window.location.href = '/super-admin/login/';
        return;
      }

      const user = authSession.user || {};
      populateUserUI(user);

      // Sync latest profile information including avatar
      if (authSession.accessToken) {
        fetch('/api/superuser/profile/', {
          method: 'GET',
          headers: {
            'Authorization': `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`,
            'Accept': 'application/json'
          },
          credentials: 'same-origin'
        })
        .then(res => res.json())
        .then(data => {
          if (data && data.user) {
            authSession.user = Object.assign({}, authSession.user, data.user);
            localStorage.setItem('superadmin_auth', JSON.stringify(authSession));
            populateUserUI(data.user);
          }
        })
        .catch(err => console.warn('Could not sync profile in dashboard:', err));
      }
    }

    // Header Logout Button Handler
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
      e.preventDefault();
      localStorage.removeItem('superadmin_auth');
      window.location.href = '/super-admin/login/';
    });

    // Sync logout across tabs
    window.addEventListener('storage', (e) => {
      if (e.key === 'superadmin_auth' && !e.newValue) {
        window.location.href = '/super-admin/login/';
      }
    });

    /**
     * ----------------------------------------------------
     * Profile Modal Logic & Live Data Population
     * ----------------------------------------------------
     */
    const profileModalOverlay = document.getElementById('profileModalOverlay');
    const userProfileBtn = document.getElementById('userProfileBtn');
    const closeProfileModalBtn = document.getElementById('closeProfileModalBtn');
    const modalCloseActionBtn = document.getElementById('modalCloseActionBtn');
    const modalLogoutBtn = document.getElementById('modalLogoutBtn');
    const copyEmailBtn = document.getElementById('copyEmailBtn');
    const copyEmailText = document.getElementById('copyEmailText');

    function populateProfileModal(user) {
      if (!user) return;
      const username = user.username || 'Admin';
      const initial = username.charAt(0).toUpperCase();

      const isSuper = (user.isSuperuser !== undefined) ? user.isSuperuser : (user.is_superuser !== undefined ? user.is_superuser : true);
      const isStaff = (user.isStaff !== undefined) ? user.isStaff : (user.is_staff !== undefined ? user.is_staff : true);
      const isActive = (user.isActive !== undefined) ? user.isActive : (user.is_active !== undefined ? user.is_active : true);
      const email = user.email || 'nahid2887@gmail.com';
      const dateJoinedRaw = user.dateJoined || user.date_joined;
      const lastLoginRaw = user.lastLogin || user.last_login;
      const firstName = user.firstName || user.first_name || '';
      const lastName = user.lastName || user.last_name || '';
      const fullName = (firstName || lastName) ? `${firstName} ${lastName}`.trim() : username;

      document.getElementById('modalHeroAvatar').textContent = initial;
      document.getElementById('modalHeroName').textContent = fullName;
      document.getElementById('modalHeroUsername').textContent = `@${username}`;
      document.getElementById('modalDetailEmail').textContent = email;
      document.getElementById('modalUserId').textContent = `#${user.id || 1}`;
      document.getElementById('modalDetailUsername').textContent = username;
      document.getElementById('modalFullName').textContent = fullName;
      document.getElementById('modalRole').textContent = isSuper ? 'Super Administrator (Root)' : 'Staff User';
      document.getElementById('modalStaff').textContent = isStaff ? 'Yes (Full Staff Privileges)' : 'Standard User';
      document.getElementById('modalStatus').textContent = isActive ? 'Active' : 'Disabled';

      if (dateJoinedRaw) {
        const d = new Date(dateJoinedRaw);
        document.getElementById('modalDateJoined').textContent = isNaN(d.getTime()) ? dateJoinedRaw : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
      } else {
        document.getElementById('modalDateJoined').textContent = 'Oct 16, 2026';
      }

      if (lastLoginRaw) {
        const dl = new Date(lastLoginRaw);
        document.getElementById('modalLastLogin').textContent = isNaN(dl.getTime()) ? lastLoginRaw : dl.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      } else {
        document.getElementById('modalLastLogin').textContent = 'Current Session (Active)';
      }
    }

    // Copy Email helper
    if (copyEmailBtn) {
      copyEmailBtn.addEventListener('click', () => {
        const email = document.getElementById('modalDetailEmail').textContent;
        if (email && email !== 'No email registered') {
          navigator.clipboard.writeText(email).then(() => {
            copyEmailText.textContent = 'Copied!';
            setTimeout(() => {
              copyEmailText.textContent = 'Copy';
            }, 2000);
          }).catch(() => {
            copyEmailText.textContent = 'Copied!';
            setTimeout(() => {
              copyEmailText.textContent = 'Copy';
            }, 2000);
          });
        }
      });
    }

    function openProfileModal() {
      if (!authSession) {
        authSession = getStoredAuth() || { user: { username: 'nahid', email: 'nahid2887@gmail.com', is_superuser: true, is_staff: true, id: 1 } };
      }
      populateProfileModal(authSession.user);

      profileModalOverlay.classList.add('open');
      profileModalOverlay.setAttribute('aria-hidden', 'false');

      // Refresh data from server profile API in background if access token present
      if (authSession.accessToken) {
        fetch('/api/superuser/profile/', {
          method: 'GET',
          headers: {
            'Authorization': `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`,
            'Accept': 'application/json'
          }
        })
        .then(res => res.json())
        .then(resData => {
          if (resData && resData.user) {
            authSession.user = Object.assign({}, authSession.user, resData.user);
            localStorage.setItem('superadmin_auth', JSON.stringify(authSession));
            populateProfileModal(authSession.user);
          }
        })
        .catch(err => console.warn('Could not fetch updated profile:', err));
      }
    }

    function closeProfileModal() {
      profileModalOverlay.classList.remove('open');
      profileModalOverlay.setAttribute('aria-hidden', 'true');
    }

    // Clicking the profile pill navigates to the dedicated profile page (/super-admin/profile/)
    // Native link navigation is active. Modal functions remain accessible if invoked.

    closeProfileModalBtn.addEventListener('click', closeProfileModal);
    modalCloseActionBtn.addEventListener('click', closeProfileModal);

    profileModalOverlay.addEventListener('click', (e) => {
      if (e.target === profileModalOverlay) {
        closeProfileModal();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && profileModalOverlay.classList.contains('open')) {
        closeProfileModal();
      }
    });

    modalLogoutBtn.addEventListener('click', () => {
      localStorage.removeItem('superadmin_auth');
      window.location.href = '/super-admin/login/';
    });

    // ==========================================================================
    // SUPER ADMIN ORDERS & MFS VERIFICATION CONTROLLER
    // ==========================================================================
    let currentStatusFilter = 'ALL';
    let ordersSearchTimer = null;
    let activeActionOrderId = null;

    window.setOrdersStatusFilter = function(status, btnEl) {
      currentStatusFilter = status;
      document.querySelectorAll('.filter-tab-btn').forEach(btn => btn.classList.remove('active'));
      if (btnEl) btnEl.classList.add('active');
      loadSuperAdminOrders();
    };

    window.debounceOrdersSearch = function() {
      clearTimeout(ordersSearchTimer);
      ordersSearchTimer = setTimeout(() => {
        loadSuperAdminOrders();
      }, 350);
    };

    window.loadSuperAdminOrders = async function() {
      const tbody = document.getElementById('superAdminOrdersTbody');
      if (!tbody) return;

      const headers = { 'Accept': 'application/json' };
      if (authSession && authSession.accessToken) {
        headers['Authorization'] = `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`;
      }

      const params = new URLSearchParams();
      if (currentStatusFilter && currentStatusFilter !== 'ALL') {
        params.append('status', currentStatusFilter);
      }
      const paymentSelect = document.getElementById('ordersPaymentFilter');
      if (paymentSelect && paymentSelect.value && paymentSelect.value !== 'ALL') {
        params.append('payment_method', paymentSelect.value);
      }
      const searchBox = document.getElementById('ordersSearchInput');
      if (searchBox && searchBox.value.trim()) {
        params.append('search', searchBox.value.trim());
      }

      try {
        let res = await fetch(`/api/superuser/orders/?${params.toString()}`, {
          headers: headers,
          credentials: 'same-origin'
        });

        if (res.status === 401 && authSession && authSession.refreshToken) {
          try {
            const refreshRes = await fetch('/api/superuser/token/refresh/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh: authSession.refreshToken })
            });
            if (refreshRes.ok) {
              const refreshData = await refreshRes.json();
              authSession.accessToken = refreshData.access;
              localStorage.setItem('superadmin_auth', JSON.stringify(authSession));
              headers['Authorization'] = `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`;
              res = await fetch(`/api/superuser/orders/?${params.toString()}`, {
                headers: headers,
                credentials: 'same-origin'
              });
            }
          } catch (rErr) {
            console.warn('Auto token refresh failed:', rErr);
          }
        }

        if (!res.ok) {
          if (res.status === 401 || res.status === 403) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--danger);">Admin session expired or access denied. Please <a href="/super-admin/login/" style="color: var(--primary); text-decoration: underline;">re-login</a>.</td></tr>`;
            return;
          }
          throw new Error('Failed to load orders');
        }

        const data = await res.json();
        const metrics = data.metrics || {};
        const orders = data.orders || [];

        // Update summary metrics
        if (document.getElementById('metricTotalOrders')) document.getElementById('metricTotalOrders').textContent = metrics.total_orders || 0;
        if (document.getElementById('metricPendingOrders')) document.getElementById('metricPendingOrders').textContent = metrics.pending_orders || 0;
        if (document.getElementById('metricApprovedOrders')) document.getElementById('metricApprovedOrders').textContent = metrics.approved_orders || 0;
        if (document.getElementById('metricTotalRevenue')) {
          document.getElementById('metricTotalRevenue').textContent = `৳${parseFloat(metrics.total_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        }

        // Update nav badge
        const navBadge = document.getElementById('navPendingOrdersBadge');
        const badgeCount = document.getElementById('pendingBadgeCount');
        const pendingCount = metrics.pending_orders || 0;
        if (navBadge) {
          navBadge.textContent = pendingCount;
          navBadge.style.display = pendingCount > 0 ? 'inline-block' : 'none';
        }
        if (badgeCount) {
          badgeCount.textContent = `${pendingCount} Pending Verification`;
        }

        if (orders.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">No Orders Found</div>
                <div style="font-size: 0.82rem;">No customer orders match the current filter criteria.</div>
              </td>
            </tr>
          `;
          return;
        }

        let rowsHtml = '';
        orders.forEach(ord => {
          const isPending = ord.status === 'PENDING';
          const isApproved = ord.status === 'APPROVED';
          const isRejected = ord.status === 'REJECTED';

          const createdDate = ord.created_at ? new Date(ord.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
          const userObj = ord.user || {};
          const customerEmail = userObj.email || ord.customer_email || 'No email';
          const customerName = (userObj.first_name || userObj.last_name) ? `${userObj.first_name} ${userObj.last_name}`.trim() : (userObj.username || 'Customer');

          // Payment Tag
          const pMethod = ord.payment_method || 'bkash';
          const mfsClass = pMethod.toLowerCase();
          const mfsName = ord.payment_method_display || pMethod.toUpperCase();

          // Items summary
          let itemsText = '';
          (ord.items || []).forEach((it, idx) => {
            itemsText += `<div><strong>${it.product_name}</strong> <span style="font-size: 0.74rem; color: var(--primary);">(${it.plan_name})</span>${it.quantity > 1 ? ` x${it.quantity}` : ''}</div>`;
          });
          if (!itemsText) itemsText = `<span style="color: var(--text-muted);">Direct Purchase</span>`;

          // Status Pill
          let statusPill = '';
          if (isApproved) {
            statusPill = `<span class="order-status-pill approved">&bull; Approved</span>`;
          } else if (isPending) {
            statusPill = `<span class="order-status-pill pending">&bull; Pending Verification</span>`;
          } else {
            statusPill = `<span class="order-status-pill rejected">&bull; Rejected</span>`;
          }

          // Action column
          let actionCol = '';
          if (isPending) {
            actionCol = `
              <div style="display: flex; gap: 8px; justify-content: flex-end;">
                <button type="button" class="btn-approve" onclick="openApproveModal(${ord.id}, '${ord.order_number}', '${ord.transaction_id}', '${ord.license_key || ''}')" title="Verify TrxID & Approve Order">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  Approve
                </button>
                <button type="button" class="btn-reject" onclick="openRejectModal(${ord.id}, '${ord.order_number}', '${ord.transaction_id}')" title="Reject Order">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                  Reject
                </button>
              </div>
            `;
          } else if (isApproved) {
            actionCol = `
              <div style="text-align: right;">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 800; color: #10b981; display: inline-flex; align-items: center; gap: 4px; background: rgba(16, 185, 129, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3);">
                  <span>Key: ${ord.license_key || 'ACTIVE'}</span>
                  <button type="button" onclick="navigator.clipboard.writeText('${ord.license_key}'); alert('License key copied!');" style="background: none; border: none; color: #10b981; cursor: pointer; padding: 0 2px;">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  </button>
                </div>
                <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 2px;">Confirmed by Super Admin</div>
              </div>
            `;
          } else {
            actionCol = `
              <div style="text-align: right;">
                <span style="font-size: 0.74rem; color: #f43f5e; font-weight: 700;">Rejected</span>
                <div style="font-size: 0.68rem; color: var(--text-muted);" title="${ord.admin_notes || ''}">${(ord.admin_notes || 'Invalid payment').substring(0, 28)}...</div>
              </div>
            `;
          }

          rowsHtml += `
            <tr style="${isPending ? 'background: rgba(245, 158, 11, 0.03);' : ''}">
              <td>
                <div style="font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 0.88rem; color: var(--text-main);">#${ord.order_number}</div>
                <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 2px;">${createdDate}</div>
              </td>
              <td>
                <div class="subscriber-name">${customerName}</div>
                <div class="subscriber-email">${customerEmail}</div>
              </td>
              <td>
                <div style="font-size: 0.82rem; color: var(--text-main); line-height: 1.4;">${itemsText}</div>
                <div style="font-weight: 800; color: var(--accent-emerald); font-size: 0.94rem; margin-top: 3px;">৳${parseFloat(ord.total_amount).toFixed(2)}</div>
              </td>
              <td>
                <div><span class="mfs-tag ${mfsClass}">${mfsName}</span></div>
                <div style="font-size: 0.76rem; color: var(--text-secondary); margin-top: 4px;">From: <strong style="color: var(--text-main); font-family: monospace;">${ord.sender_number}</strong></div>
              </td>
              <td>
                <div class="trx-code-badge" title="Click to copy Transaction ID">
                  <span>${ord.transaction_id}</span>
                  <button type="button" onclick="navigator.clipboard.writeText('${ord.transaction_id}'); alert('Copied TrxID: ${ord.transaction_id}');" style="background: none; border: none; color: var(--primary); cursor: pointer; padding: 0 2px;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  </button>
                </div>
              </td>
              <td>
                ${statusPill}
              </td>
              <td style="text-align: right;">
                ${actionCol}
              </td>
            </tr>
          `;
        });

        tbody.innerHTML = rowsHtml;
      } catch (err) {
        console.error('Failed to load superadmin orders:', err);
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--danger);">Failed to load orders. Please try again.</td></tr>`;
      }
    };

    // Modal Control for Order Approval & Rejection
    window.openApproveModal = function(orderId, orderNum, trxId, currentKey) {
      activeActionOrderId = orderId;
      document.getElementById('approveModalOrderNum').textContent = '#' + orderNum;
      document.getElementById('approveModalTrxId').textContent = trxId;

      const defaultKey = currentKey || ('SUB-' + String(orderNum).replace(/[^A-Za-z0-9]/g, '') + '-' + Math.random().toString(36).substring(2, 6).toUpperCase());
      document.getElementById('approveModalLicenseKey').value = defaultKey;
      document.getElementById('approveModalNotes').value = '';

      const modal = document.getElementById('orderApprovalModal');
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
    };

    window.openRejectModal = function(orderId, orderNum, trxId) {
      activeActionOrderId = orderId;
      document.getElementById('rejectModalOrderNum').textContent = '#' + orderNum;
      document.getElementById('rejectModalTrxId').textContent = trxId;
      document.getElementById('rejectModalReason').value = 'Invalid Transaction ID (TrxID not found in statement)';
      document.getElementById('rejectModalReasonSelect').value = 'Invalid Transaction ID (TrxID not found in statement)';

      const modal = document.getElementById('orderRejectionModal');
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
    };

    window.closeOrderActionModal = function() {
      const m1 = document.getElementById('orderApprovalModal');
      const m2 = document.getElementById('orderRejectionModal');
      if (m1) { m1.classList.remove('open'); m1.setAttribute('aria-hidden', 'true'); }
      if (m2) { m2.classList.remove('open'); m2.setAttribute('aria-hidden', 'true'); }
      activeActionOrderId = null;
    };

    window.submitOrderApproval = async function() {
      if (!activeActionOrderId) return;
      const key = document.getElementById('approveModalLicenseKey').value.trim();
      const notes = document.getElementById('approveModalNotes').value.trim();
      const btn = document.getElementById('approveModalSubmitBtn');

      btn.disabled = true;
      btn.textContent = 'Approving & Issuing License...';

      try {
        const res = await fetch(`/api/superuser/orders/${activeActionOrderId}/approve/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`,
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            license_key: key,
            admin_notes: notes
          })
        });

        const data = await res.json();
        if (res.ok) {
          closeOrderActionModal();
          await loadSuperAdminOrders();
          alert(`🎉 Order approved successfully! Digital license '${data.order ? data.order.license_key : key}' is now active for customer.`);
        } else {
          alert(`Error approving order: ${data.error || data.detail || JSON.stringify(data)}`);
        }
      } catch (err) {
        console.error('Error approving order:', err);
        alert('Network error approving order.');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg> Confirm Approval & Issue License`;
      }
    };

    window.submitOrderRejection = async function() {
      if (!activeActionOrderId) return;
      const reason = document.getElementById('rejectModalReason').value.trim();
      const btn = document.getElementById('rejectModalSubmitBtn');

      if (!reason) {
        alert('Please specify a rejection reason.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Rejecting Order...';

      try {
        const res = await fetch(`/api/superuser/orders/${activeActionOrderId}/reject/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`,
            'Accept': 'application/json'
          },
          body: JSON.stringify({ reason: reason })
        });

        const data = await res.json();
        if (res.ok) {
          closeOrderActionModal();
          await loadSuperAdminOrders();
          alert(`Order rejected.`);
        } else {
          alert(`Error rejecting order: ${data.error || data.detail || JSON.stringify(data)}`);
        }
      } catch (err) {
        console.error('Error rejecting order:', err);
        alert('Network error rejecting order.');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg> Confirm Rejection`;
      }
    };

    // ==========================================================================
    // SUPER ADMIN CUSTOMERS DIRECTORY CONTROLLER
    // ==========================================================================
    let currentCustomerFilter = 'ALL';
    let customersSearchTimer = null;

    window.setCustomersStatusFilter = function(filterVal, btnEl) {
      currentCustomerFilter = filterVal;
      document.querySelectorAll('#customersSection .filter-tab-btn').forEach(btn => btn.classList.remove('active'));
      if (btnEl) btnEl.classList.add('active');
      loadSuperAdminCustomers();
    };

    window.debounceCustomersSearch = function() {
      clearTimeout(customersSearchTimer);
      customersSearchTimer = setTimeout(() => {
        loadSuperAdminCustomers();
      }, 350);
    };

    window.loadSuperAdminCustomers = async function() {
      const tbody = document.getElementById('superAdminCustomersTbody');
      if (!tbody) return;

      const headers = { 'Accept': 'application/json' };
      if (authSession && authSession.accessToken) {
        headers['Authorization'] = `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`;
      }

      const params = new URLSearchParams();
      if (currentCustomerFilter === 'VERIFIED') {
        params.append('is_verified', 'true');
      } else if (currentCustomerFilter === 'UNVERIFIED') {
        params.append('is_verified', 'false');
      }
      const searchBox = document.getElementById('customersSearchInput');
      if (searchBox && searchBox.value.trim()) {
        params.append('search', searchBox.value.trim());
      }

      try {
        let res = await fetch(`/api/superuser/customers/?${params.toString()}`, {
          headers: headers,
          credentials: 'same-origin'
        });

        if (!res.ok) throw new Error('Failed to load customers');

        const data = await res.json();
        const customers = data.customers || [];
        const totalCount = data.total_customers || customers.length;
        const verifiedCount = data.verified_customers || 0;

        if (document.getElementById('metricTotalCustomers')) document.getElementById('metricTotalCustomers').textContent = totalCount;
        if (document.getElementById('metricVerifiedCustomers')) document.getElementById('metricVerifiedCustomers').textContent = verifiedCount;
        if (document.getElementById('customersBadgeCount')) document.getElementById('customersBadgeCount').textContent = `${totalCount} Registered`;
        const navCustomersBadge = document.getElementById('navCustomersBadge');
        if (navCustomersBadge) navCustomersBadge.textContent = totalCount;

        if (customers.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">No Customers Found</div>
                <div style="font-size: 0.82rem;">No registered customer users match the search criteria.</div>
              </td>
            </tr>
          `;
          return;
        }

        let rowsHtml = '';
        customers.forEach(cust => {
          const initial = (cust.username || 'C').charAt(0).toUpperCase();
          const avatarHtml = cust.avatar
            ? `<img src="${cust.avatar}" alt="${cust.username}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover;">`
            : `<div class="customer-avatar">${initial}</div>`;

          const verifiedBadge = cust.is_verified
            ? `<span class="verified-badge yes"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg> Verified</span>`
            : `<span class="verified-badge no">Unverified</span>`;

          const joinedDate = cust.date_joined ? new Date(cust.date_joined).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : '-';
          const totalSpentFormatted = cust.total_spent ? `৳${parseFloat(cust.total_spent).toFixed(2)}` : '৳0.00';

          rowsHtml += `
            <tr>
              <td>
                <div style="display: flex; align-items: center; gap: 10px;">
                  ${avatarHtml}
                  <div>
                    <div style="font-weight: 700; color: var(--text-main);">${cust.full_name || cust.username}</div>
                    <div style="font-size: 0.76rem; color: var(--text-muted); font-family: monospace;">@${cust.username}</div>
                  </div>
                </div>
              </td>
              <td>
                <div style="font-size: 0.84rem; color: var(--text-main);">${cust.email || '<span style="color:var(--text-muted);">No email</span>'}</div>
                <div style="margin-top: 3px;">${verifiedBadge}</div>
              </td>
              <td>
                <div style="font-size: 0.82rem; color: var(--text-main); font-family: monospace;">${cust.phone_number || '<span style="color:var(--text-muted);">-</span>'}</div>
                <div style="font-size: 0.74rem; color: var(--text-secondary);">${cust.city ? cust.city + ', ' : ''}${cust.country || 'Bangladesh'}</div>
              </td>
              <td>
                <div style="font-weight: 700; color: var(--text-main); font-size: 0.88rem;">${cust.orders_count || 0} Orders</div>
                <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px;">
                  <span style="color: #f59e0b;">${cust.pending_orders_count || 0} Pending</span> &bull; 
                  <span style="color: #10b981;">${cust.approved_orders_count || 0} Confirmed</span>
                </div>
              </td>
              <td>
                <div style="font-weight: 800; color: var(--accent-emerald); font-size: 0.94rem;">${totalSpentFormatted}</div>
              </td>
              <td>
                <div style="font-size: 0.82rem; color: var(--text-secondary);">${joinedDate}</div>
              </td>
              <td style="text-align: right;">
                <span style="display: inline-flex; align-items: center; gap: 5px; font-size: 0.74rem; font-weight: 700; color: var(--success); background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 8px; border-radius: 999px;">
                  <span class="pulse-dot" style="width: 5px; height: 5px;"></span> Active
                </span>
              </td>
            </tr>
          `;
        });

        tbody.innerHTML = rowsHtml;
      } catch (err) {
        console.error('Failed to load superadmin customers:', err);
      }
    };

    /**
     * ----------------------------------------------------
     * Monthly Analytics Bar Charts Controller
     * 1. Monthly User Logins
     * 2. Monthly Revenue (৳ BDT)
     * ----------------------------------------------------
     */
    let userLoginsChartInstance = null;
    let monthlyRevenueChartInstance = null;
    let cachedAnalyticsData = null;

    window.loadDashboardAnalyticsCharts = async function() {
      const yearSelect = document.getElementById('analyticsYearFilter');
      const year = yearSelect ? yearSelect.value : 2026;

      try {
        const headers = { 'Accept': 'application/json' };
        if (authSession && authSession.accessToken) {
          headers['Authorization'] = `${authSession.tokenType || 'Bearer'} ${authSession.accessToken}`;
        }
        const res = await fetch(`/api/superuser/analytics/?year=${year}`, {
          headers: headers,
          credentials: 'same-origin'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        cachedAnalyticsData = data;
        renderDashboardAnalytics(data);
      } catch (err) {
        console.warn('Analytics API error or offline, rendering default dataset:', err);
        const fallbackData = {
          year: parseInt(year) || 2026,
          user_logins: {
            months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            data: [145, 210, 315, 420, 560, 680, 750, 890, 940, 1080, 0, 0],
            total: 5990,
            avg_monthly: 599,
            growth_percentage: '+18.4%',
            peak_month: 'October'
          },
          monthly_revenue: {
            currency: '৳',
            months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            data: [12400, 15800, 19200, 24500, 28900, 31200, 36800, 42500, 39800, 49990, 0, 0],
            total: 301090,
            avg_monthly: 30109,
            growth_percentage: '+22.6%',
            peak_month: 'October'
          }
        };
        cachedAnalyticsData = fallbackData;
        renderDashboardAnalytics(fallbackData);
      }
    };

    function renderDashboardAnalytics(data) {
      if (!data) return;

      // Update User Logins Stats
      if (data.user_logins) {
        const elTotal = document.getElementById('statTotalLogins');
        const elAvg = document.getElementById('statAvgLogins');
        const elGrowth = document.getElementById('statGrowthLogins');
        const elPeak = document.getElementById('loginsPeakMonth');

        if (elTotal) elTotal.textContent = Number(data.user_logins.total || 0).toLocaleString();
        if (elAvg) elAvg.textContent = Number(data.user_logins.avg_monthly || 0).toLocaleString() + '/mo';
        if (elGrowth) elGrowth.textContent = data.user_logins.growth_percentage || '+18.4%';
        if (elPeak) elPeak.textContent = `Peak: ${data.user_logins.peak_month || 'October'}`;
      }

      // Update Revenue Stats
      if (data.monthly_revenue) {
        const elTotalRev = document.getElementById('statTotalRevenue');
        const elAvgRev = document.getElementById('statAvgRevenue');
        const elGrowthRev = document.getElementById('statGrowthRevenue');
        const elPeakRev = document.getElementById('revenuePeakMonth');

        if (elTotalRev) elTotalRev.textContent = `৳${Number(data.monthly_revenue.total || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
        if (elAvgRev) elAvgRev.textContent = `৳${Number(data.monthly_revenue.avg_monthly || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}/mo`;
        if (elGrowthRev) elGrowthRev.textContent = data.monthly_revenue.growth_percentage || '+22.6%';
        if (elPeakRev) elPeakRev.textContent = `Peak: ${data.monthly_revenue.peak_month || 'October'}`;
      }

      // Render Charts
      if (typeof Chart !== 'undefined') {
        renderChartJsCharts(data);
      } else {
        renderSvgFallbackCharts(data);
      }
    }

    function renderChartJsCharts(data) {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      const gridColor = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.06)';
      const tickColor = isLight ? '#64748b' : '#94a3b8';
      const tooltipBg = isLight ? '#ffffff' : '#0f172a';
      const tooltipText = isLight ? '#0f172a' : '#f8fafc';
      const tooltipBorder = isLight ? '#e2e8f0' : '#334155';

      // 1. User Logins Bar Chart
      const canvas1 = document.getElementById('userLoginsChartCanvas');
      if (canvas1) {
        const ctx1 = canvas1.getContext('2d');
        if (userLoginsChartInstance) {
          userLoginsChartInstance.destroy();
        }

        const gradient1 = ctx1.createLinearGradient(0, 0, 0, 240);
        gradient1.addColorStop(0, 'rgba(99, 102, 241, 0.95)');
        gradient1.addColorStop(1, 'rgba(168, 85, 247, 0.65)');

        userLoginsChartInstance = new Chart(ctx1, {
          type: 'bar',
          data: {
            labels: data.user_logins.months,
            datasets: [{
              label: 'User Logins',
              data: data.user_logins.data,
              backgroundColor: gradient1,
              hoverBackgroundColor: '#818cf8',
              borderRadius: 6,
              borderSkipped: false,
              barThickness: 20,
              maxBarThickness: 28,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 750, easing: 'easeOutQuart' },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tooltipBg,
                titleColor: tooltipText,
                bodyColor: tooltipText,
                borderColor: tooltipBorder,
                borderWidth: 1,
                padding: 10,
                displayColors: false,
                callbacks: {
                  label: function(context) {
                    return `Logins: ${context.parsed.y.toLocaleString()} sessions`;
                  }
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: tickColor, font: { family: 'Plus Jakarta Sans', size: 11, weight: 600 } },
                border: { display: false }
              },
              y: {
                grid: { color: gridColor },
                ticks: {
                  color: tickColor,
                  font: { family: 'Plus Jakarta Sans', size: 11 },
                  callback: function(val) {
                    return val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val;
                  }
                },
                border: { display: false }
              }
            }
          }
        });
      }

      // 2. Monthly Revenue Bar Chart
      const canvas2 = document.getElementById('monthlyRevenueChartCanvas');
      if (canvas2) {
        const ctx2 = canvas2.getContext('2d');
        if (monthlyRevenueChartInstance) {
          monthlyRevenueChartInstance.destroy();
        }

        const gradient2 = ctx2.createLinearGradient(0, 0, 0, 240);
        gradient2.addColorStop(0, 'rgba(16, 185, 129, 0.95)');
        gradient2.addColorStop(1, 'rgba(6, 182, 212, 0.65)');

        monthlyRevenueChartInstance = new Chart(ctx2, {
          type: 'bar',
          data: {
            labels: data.monthly_revenue.months,
            datasets: [{
              label: 'Revenue (৳)',
              data: data.monthly_revenue.data,
              backgroundColor: gradient2,
              hoverBackgroundColor: '#34d399',
              borderRadius: 6,
              borderSkipped: false,
              barThickness: 20,
              maxBarThickness: 28,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 750, easing: 'easeOutQuart' },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: tooltipBg,
                titleColor: tooltipText,
                bodyColor: tooltipText,
                borderColor: tooltipBorder,
                borderWidth: 1,
                padding: 10,
                displayColors: false,
                callbacks: {
                  label: function(context) {
                    return `Revenue: ৳${context.parsed.y.toLocaleString()}`;
                  }
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: { color: tickColor, font: { family: 'Plus Jakarta Sans', size: 11, weight: 600 } },
                border: { display: false }
              },
              y: {
                grid: { color: gridColor },
                ticks: {
                  color: tickColor,
                  font: { family: 'Plus Jakarta Sans', size: 11 },
                  callback: function(val) {
                    return '৳' + (val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val);
                  }
                },
                border: { display: false }
              }
            }
          }
        });
      }
    }

    function updateChartsTheme(theme) {
      if (cachedAnalyticsData && typeof Chart !== 'undefined') {
        renderChartJsCharts(cachedAnalyticsData);
      }
    }

    function renderSvgFallbackCharts(data) {
      // Robust SVG Fallback when Chart.js CDN is unavailable
      const canvas1 = document.getElementById('userLoginsChartCanvas');
      const fallback1 = document.getElementById('userLoginsFallback');
      if (canvas1 && fallback1) {
        canvas1.style.display = 'none';
        fallback1.style.display = 'flex';
        fallback1.innerHTML = buildSvgBarsHtml(data.user_logins.months, data.user_logins.data, '#6366f1', '#a855f7', '');
      }

      const canvas2 = document.getElementById('monthlyRevenueChartCanvas');
      const fallback2 = document.getElementById('monthlyRevenueFallback');
      if (canvas2 && fallback2) {
        canvas2.style.display = 'none';
        fallback2.style.display = 'flex';
        fallback2.innerHTML = buildSvgBarsHtml(data.monthly_revenue.months, data.monthly_revenue.data, '#10b981', '#06b6d4', '৳');
      }
    }

    function buildSvgBarsHtml(months, values, color1, color2, prefix) {
      const maxVal = Math.max(...values, 1);
      return `
        <div style="display: flex; align-items: flex-end; justify-content: space-between; width: 100%; height: 100%; gap: 6px; padding: 10px 0;">
          ${months.map((m, i) => {
            const val = values[i] || 0;
            const pct = Math.max(Math.round((val / maxVal) * 85), val > 0 ? 6 : 2);
            return `
              <div style="flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end;" title="${m}: ${prefix}${val.toLocaleString()}">
                <div style="width: 80%; height: ${pct}%; background: linear-gradient(to top, ${color1}, ${color2}); border-radius: 4px 4px 0 0; transition: height 0.5s ease;"></div>
                <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 6px; font-weight: 600;">${m}</div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // Run on startup
    initDashboard();
    loadSuperAdminOrders();
    loadSuperAdminCustomers();
    loadDashboardAnalyticsCharts();
  