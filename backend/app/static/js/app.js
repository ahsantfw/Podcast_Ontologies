// Global app JavaScript

// Workspace management
function getWorkspaceId() {
    return localStorage.getItem('workspace_id') || 'default';
}

function setWorkspaceId(workspaceId) {
    localStorage.setItem('workspace_id', workspaceId);
    if (document.getElementById('current-workspace')) {
        document.getElementById('current-workspace').textContent = workspaceId;
    }
}

function createWorkspace() {
    const name = prompt('Enter workspace name (optional):');
    
    fetch('/api/v1/workspaces', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: name || null })
    })
    .then(response => response.json())
    .then(data => {
        setWorkspaceId(data.workspace_id);
        alert(`Workspace created: ${data.workspace_id}`);
        // Reload page to refresh workspace selector
        if (document.getElementById('workspace-select')) {
            location.reload();
        }
    })
    .catch(error => {
        alert(`Failed to create workspace: ${error.message}`);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const workspaceId = getWorkspaceId();
    if (document.getElementById('current-workspace')) {
        document.getElementById('current-workspace').textContent = workspaceId;
    }
    
    // Update workspace select if exists
    if (document.getElementById('workspace-select')) {
        const select = document.getElementById('workspace-select');
        if (Array.from(select.options).find(opt => opt.value === workspaceId)) {
            select.value = workspaceId;
        }
    }
});

