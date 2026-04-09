/**
 * Driver Drowsiness Detection System 
 * Flask Backend Integration script.js
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // UI Elements
    const toggleDetectionBtn = document.getElementById('toggleDetectionBtn');
    const videoFeed = document.getElementById('videoFeed');
    const videoPlaceholder = document.getElementById('videoPlaceholder');
    
    const driverStatusWrapper = document.getElementById('driverStatusWrapper');
    const driverStatusText = document.getElementById('driverStatusText');
    const statusIcon = document.getElementById('statusIcon');
    const systemBadge = document.getElementById('systemBadge');
    const dynamicSystemStatus = document.getElementById('dynamicSystemStatus');
    
    // Metrics Elements
    const alertnessScoreEl = document.getElementById('alertnessScore');
    const metricEar = document.getElementById('metricEar');
    const metricMar = document.getElementById('metricMar');
    const metricDuration = document.getElementById('metricDuration');
    
    // Summary Elements
    const sessionTimeEl = document.getElementById('sessionTime');
    const totalAlertsEl = document.getElementById('totalAlerts');
    const maxDrowsyEl = document.getElementById('maxDrowsy');
    
    // Log & System
    const logContainer = document.getElementById('logContainer');
    const clearLogBtn = document.getElementById('clearLogBtn');
    const fpsCount = document.getElementById('fpsCount');
    const pingCount = document.getElementById('pingCount');
    const currYear = document.getElementById('currYear');
    const alarmAudio = document.getElementById('alarmAudio');
    
    currYear.textContent = new Date().getFullYear();

    // State
    let isDetecting = false;
    let pollInterval = null;
    let uptimeInterval = null;
    let alarmPlaying = false;
    
    // Session State
    let sessionStartTime = null;
    let totalAlerts = 0;
    let maxDrowsyDuration = 0.0;
    let currentStatusState = 'IDLE';
    let lastReason = '';

    // Routes
    const FLASK_VIDEO_ROUTE = "/video_feed";

    // Toggle Detection System
    toggleDetectionBtn.addEventListener('click', async () => {
        if (!isDetecting) {
            try {
                alarmAudio.play().then(() => alarmAudio.pause()).catch(e => console.log("Audio unlock:", e));

                const response = await fetch('/start_detection', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    isDetecting = true;
                    
                    // Reset Session
                    sessionStartTime = Date.now();
                    totalAlerts = 0;
                    maxDrowsyDuration = 0.0;
                    totalAlertsEl.textContent = '0';
                    maxDrowsyEl.textContent = '0.0s';
                    sessionTimeEl.textContent = '00:00';
                    currentStatusState = 'ACTIVE';

                    // UI Boot
                    toggleDetectionBtn.innerHTML = '<i class="bi bi-stop-circle me-2 fs-5"></i> <span class="fw-bold tracking-wider text-uppercase">Halt System</span>';
                    toggleDetectionBtn.classList.remove('btn-start');
                    toggleDetectionBtn.classList.add('active-state');
                    
                    systemBadge.textContent = 'REC';
                    systemBadge.className = 'badge bg-outline-success blinking-dot';
                    dynamicSystemStatus.textContent = "Connecting to ML pipeline...";
                    
                    videoPlaceholder.classList.add('d-none');
                    videoFeed.src = FLASK_VIDEO_ROUTE + "?t=" + new Date().getTime(); 
                    videoFeed.style.display = 'block';
                    
                    addLog('SYSTEM: Initializing telemetry and starting active monitoring.', 'log-info');
                    
                    pollInterval = setInterval(fetchStatus, 1000);
                    uptimeInterval = setInterval(updateUptime, 1000);
                }
            } catch (err) {
                addLog('ERROR: Could not establish connection to detection server.', 'log-alert');
            }

        } else {
            try {
                await fetch('/stop_detection', { method: 'POST' });
                
                isDetecting = false;
                clearInterval(pollInterval);
                clearInterval(uptimeInterval);
                stopAlarm();
                
                toggleDetectionBtn.innerHTML = '<i class="bi bi-power me-2 fs-5"></i> <span class="fw-bold tracking-wider text-uppercase">Initialize System</span>';
                toggleDetectionBtn.classList.remove('active-state');
                toggleDetectionBtn.classList.add('btn-start');
                
                systemBadge.textContent = 'DISCONNECTED';
                systemBadge.className = 'badge bg-outline-info';
                dynamicSystemStatus.textContent = "System awaiting initialization...";
                
                videoFeed.style.display = 'none';
                videoFeed.src = "";
                videoPlaceholder.classList.remove('d-none');
                
                // Keep the final summary intact but reset metrics
                metricEar.textContent = "0.00";
                metricMar.textContent = "0.00";
                metricDuration.textContent = "0.0s";
                alertnessScoreEl.textContent = "--";
                
                setStatus('IDLE');
                addLog(`SYSTEM: Stream halted. Session Length: ${sessionTimeEl.textContent}.`, 'log-system text-muted');

            } catch(e) {
                console.error(e);
            }
        }
    });

    async function fetchStatus() {
        if (!isDetecting) return;
        const startTime = Date.now();
        try {
            const res = await fetch('/status');
            const data = await res.json();
            const latency = Date.now() - startTime;
            
            fpsCount.textContent = data.fps || 0;
            pingCount.textContent = latency;
            
            // Update Explainability Metrics
            metricEar.textContent = data.ear.toFixed(2);
            metricMar.textContent = data.mar.toFixed(2);
            metricDuration.textContent = data.drowsy_duration.toFixed(1) + 's';
            
            // Check max drowsy duration
            if (data.drowsy_duration > maxDrowsyDuration) {
                maxDrowsyDuration = data.drowsy_duration;
                maxDrowsyEl.textContent = maxDrowsyDuration.toFixed(1) + 's';
            }
            
            // Color code metrics visually
            metricEar.className = data.ear < 0.25 ? 'fs-5 fw-bold text-danger' : 'fs-5 fw-bold text-success';
            metricMar.className = data.mar > 0.5 ? 'fs-5 fw-bold text-warning' : 'fs-5 fw-bold text-success';
            
            // Update Alertness Score
            alertnessScoreEl.textContent = Math.round(data.score);
            let scoreColor = 'text-success';
            if (data.score <= 70) scoreColor = 'text-warning';
            if (data.score <= 40) scoreColor = 'text-danger';
            alertnessScoreEl.className = `display-4 fw-bold font-monospace ${scoreColor}`;

            // Handle Dynamic Status Reason
            if (data.reason && data.reason !== lastReason) {
                 dynamicSystemStatus.textContent = data.reason;
                 lastReason = data.reason;
            }

            handleStatusChange(data.status, data.reason);
            
        } catch (err) {
            console.error("Failed to fetch status:", err);
        }
    }

    function handleStatusChange(status, reason) {
        if (status !== currentStatusState) {
            // Check varied transition messages
            if (status === 'CRITICAL') {
                totalAlerts++;
                totalAlertsEl.textContent = totalAlerts;
                addLog(`CRITICAL: ${getVariedLogMessage('critical', reason)}`, 'log-alert');
                playAlarm();
            } else if (status === 'WARNING') {
                addLog(`WARNING: ${getVariedLogMessage('warning', reason)}`, 'log-warn');
                stopAlarm();
            } else if (status === 'ACTIVE') {
                 if (currentStatusState === 'CRITICAL' || currentStatusState === 'WARNING') {
                     addLog(`NEURAL: ${getVariedLogMessage('active', reason)}`, 'log-success');
                 }
                 stopAlarm();
            }
            setStatus(status);
            currentStatusState = status;
        }
    }
    
    // Varied logging utility
    function getVariedLogMessage(type, explicitReason) {
        if (explicitReason && explicitReason !== "Driver behavior nominal") {
            return explicitReason; // Prioritize explicitly passed ML insights
        }
        
        const logs = {
            'critical': ['Threshold breached. Immediate attention required.', 'Sustained eye closure detected.', 'Severe fatigue level.'],
            'warning': ['Drowsiness indicators elevating.', 'Unstable behavior recognized.', 'Alertness metrics dropping.'],
            'active': ['State stabilized. Face mesh nominal.', 'Tracking active. Behavior normal.', 'Alertness recovered.']
        };
        const arr = logs[type];
        return arr[Math.floor(Math.random() * arr.length)];
    }

    function updateUptime() {
        if (!isDetecting || !sessionStartTime) return;
        const diff = Math.floor((Date.now() - sessionStartTime) / 1000);
        const m = Math.floor(diff / 60).toString().padStart(2, '0');
        const s = (diff % 60).toString().padStart(2, '0');
        sessionTimeEl.textContent = `${m}:${s}`;
    }

    // Audio Control
    function playAlarm() {
        if (!alarmPlaying) {
            alarmPlaying = true;
            alarmAudio.play().catch(e => console.error("Audio block:", e));
        }
    }

    function stopAlarm() {
        if (alarmPlaying) {
            alarmPlaying = false;
            alarmAudio.pause();
            alarmAudio.currentTime = 0;
        }
    }

    clearLogBtn.addEventListener('click', () => {
        logContainer.innerHTML = '';
        addLog('SYSTEM: Logs cleared by user.', 'log-system text-muted');
    });

    function addLog(message, cssClass = '') {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        const entry = document.createElement('div');
        entry.className = `log-entry ${cssClass}`;
        entry.innerHTML = `<span class="text-secondary">[${time}]</span> ${message}`;
        
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    function setStatus(status) {
        driverStatusWrapper.classList.remove('idle', 'active', 'warning', 'critical');
        statusIcon.className = 'status-icon bi';
        
        if (status === 'IDLE') {
            driverStatusWrapper.classList.add('idle');
            driverStatusText.textContent = 'IDLE';
            driverStatusText.className = 'fw-bold m-0 tracking-wider text-secondary mt-1';
            statusIcon.classList.add('bi-shield-check', 'inactive');
        } 
        else if (status === 'ACTIVE') {
            driverStatusWrapper.classList.add('active');
            driverStatusText.textContent = 'ACTIVE';
            driverStatusText.className = 'fw-bold m-0 tracking-wider text-success mt-1';
            statusIcon.classList.add('bi-shield-fill-check');
        } 
        else if (status === 'WARNING') {
            driverStatusWrapper.classList.add('warning');
            driverStatusText.textContent = 'WARNING';
            driverStatusText.className = 'fw-bold m-0 tracking-wider text-warning mt-1';
            statusIcon.classList.add('bi-exclamation-triangle');
        }
        else if (status === 'CRITICAL') {
            driverStatusWrapper.classList.add('critical');
            driverStatusText.textContent = 'CRITICAL';
            driverStatusText.className = 'fw-bold m-0 tracking-wider text-danger mt-1';
            statusIcon.classList.add('bi-exclamation-octagon-fill');
        }
    }
});
