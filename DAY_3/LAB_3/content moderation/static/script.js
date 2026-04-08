function switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    document.getElementById(`nav-${tabId}`).classList.add('active');
    
    if (tabId === 'dashboard') {
        fetchQueue();
    } else if (tabId === 'all') {
        fetchAllContent();
    }
}

async function submitContent() {
    const text = document.getElementById('content-input').value;
    if (!text) return;
    
    const btn = document.getElementById('submit-btn');
    const loader = document.getElementById('submit-loader');
    const resultDiv = document.getElementById('submit-result');
    
    loader.classList.remove('loader-hidden');
    btn.disabled = true;
    
    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: text})
        });
        const data = await response.json();
        
        resultDiv.className = 'result-message show';
        
        if (data.status === 'PUBLISHED' || data.status === 'AUTO_APPROVED') {
            resultDiv.classList.add('result-success');
            resultDiv.innerHTML = `✅ Successfully published! (ID: ${data.id})`;
        } else if (data.status === 'HUMAN_REVIEW') {
            resultDiv.classList.add('result-warning');
            resultDiv.innerHTML = `⚠️ Flagged for review! Reason: ${data.reason}`;
        } else {
            resultDiv.classList.add('result-success');
            resultDiv.innerHTML = `Status: ${data.status}`;
        }
        
        document.getElementById('content-input').value = '';
    } catch (e) {
        resultDiv.className = 'result-message show result-danger';
        resultDiv.innerHTML = `❌ Error submitting content.`;
    } finally {
        loader.classList.add('loader-hidden');
        btn.disabled = false;
    }
}

async function fetchQueue() {
    const container = document.getElementById('queue-container');
    container.innerHTML = '<div class="loader">Loading queue...</div>';
    
    try {
        const res = await fetch('/moderation-queue');
        const items = await res.json();
        
        if (items.length === 0) {
            container.innerHTML = '<div class="text-muted" style="color: var(--text-muted); padding: 20px;">Queue is empty. Great job!</div>';
            return;
        }
        
        container.innerHTML = '';
        items.forEach(item => {
            const el = document.createElement('div');
            el.className = 'queue-item';
            el.innerHTML = `
                <div class="reason">⚠️ ${item.moderation_reason}</div>
                <div class="text-content">"${item.text}"</div>
                <div class="queue-actions">
                    <button class="btn-approve" onclick="reviewContent('${item.id}', 'approve')">Approve</button>
                    <button class="btn-reject" onclick="reviewContent('${item.id}', 'reject')">Reject</button>
                </div>
            `;
            container.appendChild(el);
        });
    } catch (e) {
        container.innerHTML = '<div class="text-danger" style="color:red">Error loading queue.</div>';
    }
}

async function reviewContent(id, action) {
    try {
        await fetch(`/${action}/${id}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({note: ""})
        });
        fetchQueue(); // refresh
    } catch (e) {
        alert("Error reviewing content.");
    }
}

async function fetchAllContent() {
    const tbody = document.getElementById('all-content-body');
    tbody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
    
    try {
        const res = await fetch('/all');
        const items = await res.json();
        
        tbody.innerHTML = '';
        items.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><small>${item.id.split('-')[0]}</small></td>
                <td>${item.text.substring(0, 50)}${item.text.length > 50 ? '...' : ''}</td>
                <td><span class="status-badge status-${item.status}">${item.status}</span></td>
                <td><small>${item.moderation_reason || '-'}</small></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-danger" style="color:red">Error loading content.</td></tr>';
    }
}
