// PoliTrack - Connected Dashboard Logic & Datasets

const API_BASE = "/api";

// Custom toast notification system
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    
    container.appendChild(toast);
    
    // Animate out and remove
    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

const ELECTION_LIMITS = {
    presidential: { label: "Presidential", limit2022: 5000000000 },
    gubernatorial: { label: "Gubernatorial", limit2022: 1000000000 },
    senatorial: { label: "Senatorial", limit2022: 100000000 },
    representative: { label: "House of Reps", limit2022: 70000000 },
    assembly: { label: "House of Assembly", limit2022: 30000000 }
};

let candidatesData = [];
let statesData = {};

// Format currency
function formatNaira(num) {
    if (num >= 1000000000) {
        return "₦" + (num / 1000000000).toFixed(2) + "B";
    }
    if (num >= 1000000) {
        return "₦" + (num / 1000000).toFixed(2) + "M";
    }
    return "₦" + num.toLocaleString();
}

// Fetch and load initial data from backend API
async function loadData() {
    try {
        const cRes = await fetch(`${API_BASE}/candidates`);
        candidatesData = await cRes.json();

        const sRes = await fetch(`${API_BASE}/states`);
        statesData = await sRes.json();

        initOverviewStats();
        populateCandidateDropdown();
        renderCandidates();
        initMapVisualization();
    } catch (err) {
        console.error("Failed to connect to backend. Falling back to local demo variables.", err);
    }
}

// Populates dropdown in Estimator tab
function populateCandidateDropdown() {
    const select = document.getElementById("est-cand-select");
    const discoverSelect = document.getElementById("discover-cand-select");
    if (!select) return;
    
    select.innerHTML = "";
    if (discoverSelect) discoverSelect.innerHTML = "";
    
    candidatesData.forEach(cand => {
        const opt = document.createElement("option");
        opt.value = cand.id;
        opt.textContent = `${cand.name} (${cand.party}) - ${cand.category}`;
        select.appendChild(opt.cloneNode(true));
        
        if (discoverSelect) {
            const optDisc = document.createElement("option");
            optDisc.value = cand.name;
            optDisc.textContent = `${cand.name} (${cand.party})`;
            discoverSelect.appendChild(optDisc);
        }
    });
    
    if (candidatesData.length > 0) {
        loadCandidateProfilePreset(candidatesData[0]);
    }
}

// Navigation/Tab switching logic
document.querySelectorAll(".nav-item").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach(btn => btn.classList.remove("active"));
        button.classList.add("active");

        document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.remove("active"));
        const tabId = "tab-" + button.getAttribute("data-tab");
        document.getElementById(tabId).classList.add("active");

        document.getElementById("page-title").innerText = button.innerText.trim();
        
        if (button.getAttribute("data-tab") === "overview") {
            document.getElementById("page-subtitle").innerText = "Track compliance and excessive campaign expenditures in Nigerian elections";
            loadData();
        } else if (button.getAttribute("data-tab") === "methodology") {
            document.getElementById("page-subtitle").innerText = "Methodological guidelines, pricing baselines, and audit compliance equations";
        }
    });
});

// Load candidate profile presets into the estimator based on category
function loadCandidateProfilePreset(candidate) {
    if (!candidate) return;
    
    const category = candidate.category;
    if (category === "presidential") {
        busInput.value = 300;
        suvInput.value = 50;
        delegatesInput.value = 15000;
        venueInput.value = 10000000;
        publicityInput.value = 25000000;
    } else if (category === "gubernatorial") {
        busInput.value = 120;
        suvInput.value = 25;
        delegatesInput.value = 6000;
        venueInput.value = 5000000;
        publicityInput.value = 12000000;
    } else { // senatorial
        busInput.value = 35;
        suvInput.value = 10;
        delegatesInput.value = 1800;
        venueInput.value = 1500000;
        publicityInput.value = 3000000;
    }

    if (candidate.state) {
        const locSelect = document.getElementById("est-location-select");
        if (locSelect && [...locSelect.options].some(o => o.value === candidate.state)) {
            locSelect.value = candidate.state;
        }
    }
    updateCalculator();
}

// Add change listener to candidate dropdown
document.getElementById("est-cand-select").addEventListener("change", (e) => {
    const candId = parseInt(e.target.value);
    const candidate = candidatesData.find(c => c.id === candId);
    loadCandidateProfilePreset(candidate);
});

// Overview stats render
function initOverviewStats() {
    if (candidatesData.length === 0) return;

    const totalSpend = candidatesData.reduce((acc, c) => acc + c.estimatedSpend, 0);
    const totalRallies = candidatesData.reduce((acc, c) => acc + c.ralliesHeld, 0);
    
    document.getElementById("stat-total-spending").innerText = formatNaira(totalSpend);
    document.getElementById("stat-tracked-candidates").innerText = candidatesData.length;
    document.getElementById("stat-tracked-rallies").innerText = totalRallies;
    
    // Average excess calculations
    let excessMultiplierSum = 0;
    candidatesData.forEach(cand => {
        const limitType = ELECTION_LIMITS[cand.category] ? cand.category : "presidential";
        const limit = ELECTION_LIMITS[limitType].limit2022;
        excessMultiplierSum += (cand.estimatedSpend / limit);
    });
    const avgExcess = (excessMultiplierSum / candidatesData.length).toFixed(1);
    document.getElementById("stat-average-excess").innerText = avgExcess + "x";

    // Progress Bars Render
    const barChartContainer = document.getElementById("bar-chart-container");
    barChartContainer.innerHTML = "";
    
    Object.keys(ELECTION_LIMITS).forEach(key => {
        const item = ELECTION_LIMITS[key];
        const cats = candidatesData.filter(c => c.category === key);
        const avgSpend = cats.length > 0 ? (cats.reduce((acc, c) => acc + c.estimatedSpend, 0) / cats.length) : (item.limit2022 * 0.1);
        
        const pctOfLimit = Math.min(100, (avgSpend / item.limit2022) * 100);
        const excessTimes = (avgSpend / item.limit2022).toFixed(1);

        const row = document.createElement("div");
        row.className = "bar-row";
        row.innerHTML = `
            <div class="bar-labels">
                <span class="category">${item.label} (Limit: ${formatNaira(item.limit2022)})</span>
                <span class="actual-spend">Avg Spend: ${formatNaira(avgSpend)} (${excessTimes}x limit)</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pctOfLimit}%"></div>
            </div>
            <div class="limit-marker-text">
                <span>0% Utilized</span>
                <span>Limit Breach threshold</span>
            </div>
        `;
        barChartContainer.appendChild(row);
    });

    // Recent Critical Excesses render
    const violationsList = document.getElementById("recent-violations-list");
    violationsList.innerHTML = "";
    
    [...candidatesData].sort((a,b) => b.estimatedSpend - a.estimatedSpend).slice(0, 4).forEach(cand => {
        const limitType = ELECTION_LIMITS[cand.category] ? cand.category : "presidential";
        const limit = ELECTION_LIMITS[limitType].limit2022;
        const excess = (cand.estimatedSpend / limit).toFixed(1);
        
        const listItem = document.createElement("div");
        listItem.className = "list-item";
        listItem.innerHTML = `
            <div class="list-item-meta">
                <span class="list-item-title">${cand.name} (${cand.party})</span>
                <span class="list-item-subtitle">${cand.category.toUpperCase()} Campaign</span>
            </div>
            <div class="list-item-value-wrapper">
                <div class="list-item-value">${formatNaira(cand.estimatedSpend)}</div>
                <span class="list-item-excess">${excess}x Legal Limit</span>
            </div>
        `;
        violationsList.appendChild(listItem);
    });
}

// RALLY EXPENSE ESTIMATOR FORMULAS
const busInput = document.getElementById("est-buses");
const busHireInput = document.getElementById("est-bus-hire");
const suvInput = document.getElementById("est-suvs");
const fuelLitersInput = document.getElementById("est-fuel-liters");
const fuelPriceInput = document.getElementById("est-fuel-price");
const delegatesInput = document.getElementById("est-delegates");
const allowanceInput = document.getElementById("est-allowance");
const venueInput = document.getElementById("est-venue");
const publicityInput = document.getElementById("est-publicity");

function updateCalculator() {
    const buses = parseInt(busInput.value);
    const busHire = parseInt(busHireInput.value);
    const suvs = parseInt(suvInput.value);
    const fuelLiters = parseInt(fuelLitersInput.value);
    const fuelPrice = parseInt(fuelPriceInput.value);
    const delegates = parseInt(delegatesInput.value);
    const allowance = parseInt(allowanceInput.value);
    const venueCost = parseInt(venueInput.value);
    const publicityCost = parseInt(publicityInput.value);

    document.getElementById("val-buses").innerText = buses.toLocaleString();
    document.getElementById("val-bus-hire").innerText = busHire.toLocaleString();
    document.getElementById("val-suvs").innerText = suvs.toLocaleString();
    document.getElementById("val-fuel-liters").innerText = fuelLiters.toLocaleString();
    document.getElementById("val-delegates").innerText = delegates.toLocaleString();
    document.getElementById("val-allowance").innerText = allowance.toLocaleString();

    const busCost = buses * busHire;
    const fuelCost = (buses + suvs) * fuelLiters * fuelPrice;
    const delegateCost = delegates * allowance;
    const venuePublicity = venueCost + publicityCost;
    const totalRallyCost = busCost + fuelCost + delegateCost + venuePublicity;

    document.getElementById("total-rally-cost").innerText = formatNaira(totalRallyCost);
    document.getElementById("br-bus-cost").innerText = formatNaira(busCost);
    document.getElementById("br-fuel-cost").innerText = formatNaira(fuelCost);
    document.getElementById("br-delegate-cost").innerText = formatNaira(delegateCost);
    document.getElementById("br-venue-publicity").innerText = formatNaira(venuePublicity);

    const presLimit = ELECTION_LIMITS.presidential.limit2022;
    const guberLimit = ELECTION_LIMITS.gubernatorial.limit2022;
    const senLimit = ELECTION_LIMITS.senatorial.limit2022;

    document.getElementById("comp-presidential").innerText = Math.floor(presLimit / totalRallyCost) + " Rallies Limit";
    document.getElementById("comp-gubernatorial").innerText = Math.floor(guberLimit / totalRallyCost) + " Rallies Limit";
    document.getElementById("comp-senatorial").innerText = Math.floor(senLimit / totalRallyCost) + " Rallies Limit";
}

[busInput, busHireInput, suvInput, fuelLitersInput, fuelPriceInput, delegatesInput, allowanceInput, venueInput, publicityInput].forEach(elem => {
    elem.addEventListener("input", updateCalculator);
    elem.addEventListener("change", updateCalculator);
});

// SAVE RALLY LOG TO BACKEND
document.getElementById("btn-save-rally").addEventListener("click", async () => {
    const btn = document.getElementById("btn-save-rally");
    btn.disabled = true;
    btn.innerText = "Saving Rally Record...";

    const payload = {
        candidate_id: parseInt(document.getElementById("est-cand-select").value),
        location: document.getElementById("est-location-select").value,
        buses: parseInt(busInput.value),
        bus_hire_cost: parseFloat(busHireInput.value),
        suvs: parseInt(suvInput.value),
        fuel_liters: parseFloat(fuelLitersInput.value),
        fuel_price: parseFloat(fuelPriceInput.value),
        delegates: parseInt(delegatesInput.value),
        allowance: parseFloat(allowanceInput.value),
        venue_cost: parseFloat(venueInput.value),
        publicity_cost: parseFloat(publicityInput.value)
    };

    try {
        const res = await fetch(`${API_BASE}/rallies`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast("Rally Log Saved & Candidate Expenditures Re-estimated!", "success");
            await loadData();
        } else {
            const err = await res.json();
            showToast("Error: " + err.detail, "error");
        }
    } catch (err) {
        showToast("Failed to submit rally log: " + err.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerText = "💾 Save Rally to Database";
    }
});

// NEWS ARTICLE SCRAAPER
document.getElementById("btn-scrape").addEventListener("click", async () => {
    const urlInput = document.getElementById("scrape-url");
    const statusMsg = document.getElementById("scrape-status-msg");
    const btn = document.getElementById("btn-scrape");

    if (!urlInput.value) {
        statusMsg.innerText = "Please provide a valid news URL first.";
        statusMsg.style.color = "var(--accent-danger)";
        return;
    }

    statusMsg.innerText = "Fetching article & parsing with AI heuristics...";
    statusMsg.style.color = "var(--accent-color)";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/scrape`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: urlInput.value })
        });
        
        if (res.ok) {
            const data = await res.json();
            statusMsg.innerText = `Success: Detected ${data.candidate || 'Unknown Candidate'} in ${data.state} state.`;
            statusMsg.style.color = "var(--accent-emerald)";

            // Update UI sliders and inputs based on scraped data
            busInput.value = data.buses;
            suvInput.value = data.suvs;
            delegatesInput.value = data.delegates;
            venueInput.value = data.venue_cost;
            publicityInput.value = data.publicity_cost;

            // Set locations & candidates if matched
            if (data.state) {
                const locSelect = document.getElementById("est-location-select");
                if ([...locSelect.options].some(o => o.value === data.state)) {
                    locSelect.value = data.state;
                }
            }

            if (data.candidate) {
                const candSelect = document.getElementById("est-cand-select");
                const matchOpt = [...candSelect.options].find(o => o.text.includes(data.candidate));
                if (matchOpt) candSelect.value = matchOpt.value;
            }

            updateCalculator();
        } else {
            const err = await res.json();
            statusMsg.innerText = "Error: " + err.detail;
            statusMsg.style.color = "var(--accent-danger)";
        }
    } catch (err) {
        statusMsg.innerText = "Failed: Backend not responding.";
        statusMsg.style.color = "var(--accent-danger)";
    } finally {
        btn.disabled = false;
    }
});

// TAVILY AUTO-DISCOVERY
document.getElementById("btn-discover").addEventListener("click", async () => {
    const candName = document.getElementById("discover-cand-select").value;
    const statusMsg = document.getElementById("discover-status-msg");
    const btn = document.getElementById("btn-discover");

    statusMsg.innerText = `Searching the web for recent ${candName} rallies...`;
    statusMsg.style.color = "var(--accent-color)";
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/discover`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candidate_name: candName })
        });

        if (res.ok) {
            const data = await res.json();
            const list = data.results;
            if (list.length > 0) {
                const firstMatch = list[0];
                statusMsg.innerText = `Found article: "${firstMatch.title}". Updated parameters below.`;
                statusMsg.style.color = "var(--accent-emerald)";

                // Update calculator inputs
                busInput.value = firstMatch.buses;
                suvInput.value = firstMatch.suvs;
                delegatesInput.value = firstMatch.delegates;
                venueInput.value = firstMatch.venue_cost;
                publicityInput.value = firstMatch.publicity_cost;

                // Update Scrape URL field to show reference link
                document.getElementById("scrape-url").value = firstMatch.source_url;

                // Sync location state if detected
                if (firstMatch.state) {
                    const locSelect = document.getElementById("est-location-select");
                    if ([...locSelect.options].some(o => o.value === firstMatch.state)) {
                        locSelect.value = firstMatch.state;
                    }
                }

                // Sync assign candidate dropdown
                const candSelect = document.getElementById("est-cand-select");
                const matchOpt = [...candSelect.options].find(o => o.text.includes(data.candidate));
                if (matchOpt) candSelect.value = matchOpt.value;

                updateCalculator();
            } else {
                statusMsg.innerText = "No rally parameters could be parsed from recent articles.";
                statusMsg.style.color = "var(--accent-warning)";
            }
        } else {
            const err = await res.json();
            statusMsg.innerText = "Search failed: " + err.detail;
            statusMsg.style.color = "var(--accent-danger)";
        }
    } catch (err) {
        statusMsg.innerText = "Error: Backend not responding.";
        statusMsg.style.color = "var(--accent-danger)";
    } finally {
        btn.disabled = false;
    }
});

// CANDIDATE TRACKER FILTER & CARDS
function renderCandidates(filter = "all") {
    const gridContainer = document.getElementById("candidates-grid-container");
    if (!gridContainer) return;
    gridContainer.innerHTML = "";

    const filtered = filter === "all" ? candidatesData : candidatesData.filter(c => c.category === filter);
    
    filtered.forEach(cand => {
        const limit = ELECTION_LIMITS[cand.category] ? ELECTION_LIMITS[cand.category].limit2022 : 5000000000;
        const excessRatio = (cand.estimatedSpend / limit).toFixed(1);
        const isCompliant = cand.estimatedSpend <= limit;

        const card = document.createElement("div");
        card.className = `candidate-card glass ${isCompliant ? 'compliant' : 'breach'}`;
        card.innerHTML = `
            <span class="cand-party-tag">${cand.party}</span>
            <div class="cand-meta">
                <div class="cand-name">${cand.name}</div>
                <div class="cand-category">${cand.category} ${cand.state ? `(${cand.state} State)` : ""}</div>
            </div>
            <div class="cand-spending-bar">
                <div class="cand-spend-amount ${isCompliant ? 'compliant' : ''}">${formatNaira(cand.estimatedSpend)}</div>
                <div class="cand-limit-ref">Legal Cap: ${formatNaira(limit)} (${excessRatio}x spend)</div>
            </div>
        `;

        card.addEventListener("click", () => openCandidateModal(cand));
        gridContainer.appendChild(card);
    });
}

document.getElementById("filter-election-type").addEventListener("change", (e) => {
    renderCandidates(e.target.value);
});

// MODAL CANDIDATE DETAIL
const modal = document.getElementById("candidate-modal");
function openCandidateModal(cand) {
    const limit = ELECTION_LIMITS[cand.category] ? ELECTION_LIMITS[cand.category].limit2022 : 5000000000;
    const bodyContent = document.getElementById("modal-body-content");
    
    bodyContent.innerHTML = `
        <div class="modal-candidate-header">
            <h2>${cand.name} (${cand.party})</h2>
            <p>${cand.category.toUpperCase()} Candidate</p>
        </div>
        <div class="metric-group">
            <span class="label">Total Estimated Expenditure:</span>
            <span class="value font-outfit text-danger">${formatNaira(cand.estimatedSpend)}</span>
        </div>
        <div class="metric-group">
            <span class="label">Electoral Act 2022 Limit:</span>
            <span class="value font-outfit text-success">${formatNaira(limit)}</span>
        </div>
        <div class="metric-group">
            <span class="label">Campaign Rallies Conducted:</span>
            <span class="value font-outfit">${cand.ralliesHeld}</span>
        </div>
        
        <h3 class="margin-top-md">Expense Breakdown Estimates</h3>
        <table class="modal-table">
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Estimated Spend</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Bus Transport / Hires</td>
                    <td>${formatNaira(cand.breakdown.buses)}</td>
                </tr>
                <tr>
                    <td>Attendee Stipends & Mobilization</td>
                    <td>${formatNaira(cand.breakdown.delegates)}</td>
                </tr>
                <tr>
                    <td>Publicity, Billboards & Media Ads</td>
                    <td>${formatNaira(cand.breakdown.media)}</td>
                </tr>
                <tr>
                    <td>Fuel, Security & Site Logistics</td>
                    <td>${formatNaira(cand.breakdown.logistics)}</td>
                </tr>
            </tbody>
        </table>
    `;
    modal.classList.remove("hidden");
}

document.getElementById("modal-close").addEventListener("click", () => {
    modal.classList.add("hidden");
});

// NIGERIA STATE HEATMAP
function initMapVisualization() {
    const statesGroup = document.getElementById("states-group");
    if (!statesGroup) return;
    statesGroup.innerHTML = "";

    const positions = [
        { name: "Lagos", cx: 180, cy: 450, r: 45 },
        { name: "Kano", cx: 400, cy: 150, r: 55 },
        { name: "Rivers", cx: 420, cy: 500, r: 42 },
        { name: "Kaduna", cx: 380, cy: 260, r: 48 },
        { name: "Oyo", cx: 160, cy: 360, r: 40 },
        { name: "Enugu", cx: 440, cy: 410, r: 38 },
        { name: "Anambra", cx: 360, cy: 420, r: 38 },
        { name: "FCT", cx: 370, cy: 340, r: 45 }
    ];

    positions.forEach(pos => {
        const stateData = statesData[pos.name] || { rallies: 0, spend: 0, limit: 1000000000, color: "#10b981", candidates: [] };
        
        const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", pos.cx);
        circle.setAttribute("cy", pos.cy);
        circle.setAttribute("r", pos.r);
        circle.setAttribute("class", "map-state");
        circle.setAttribute("style", `fill: ${stateData.color}25; stroke: ${stateData.color}; stroke-width: 1.5;`);
        
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", pos.cx);
        text.setAttribute("y", pos.cy + 5);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("fill", "#fff");
        text.setAttribute("style", "font-family: Outfit; font-size: 13px; font-weight: bold; pointer-events: none;");
        text.textContent = pos.name;

        group.appendChild(circle);
        group.appendChild(text);

        circle.addEventListener("click", () => {
            document.querySelectorAll(".map-state").forEach(c => c.classList.remove("active-state"));
            circle.classList.add("active-state");

            document.getElementById("state-detail-fallback").classList.add("hidden");
            const content = document.getElementById("state-detail-content");
            content.classList.remove("hidden");

            document.getElementById("map-state-title").innerText = `${pos.name} State Campaign Summary`;
            document.getElementById("state-rallies").innerText = stateData.rallies;
            document.getElementById("state-total-spend").innerText = formatNaira(stateData.spend);
            document.getElementById("state-limit").innerText = formatNaira(stateData.limit);
            
            const ratio = (stateData.spend / stateData.limit).toFixed(1);
            document.getElementById("state-excess-ratio").innerText = ratio + "x Above Limit";

            const utilization = Math.min(100, (stateData.spend / stateData.limit) * 100);
            document.getElementById("state-utilization-pct").innerText = Math.round(utilization) + "%";
            document.getElementById("state-bar-fill").style.width = utilization + "%";

            const listUl = document.getElementById("state-candidates-ul");
            listUl.innerHTML = "";
            stateData.candidates.forEach(c => {
                const li = document.createElement("li");
                li.innerHTML = `<span>${c}</span> <strong class="text-danger">Exceeds Cap</strong>`;
                listUl.appendChild(li);
            });
        });

        statesGroup.appendChild(group);
    });
}

// Initial fetch
window.addEventListener("DOMContentLoaded", () => {
    loadData();
    updateCalculator();

    // Mobile sidebar navigation toggles
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menu-toggle");
    const sidebarClose = document.getElementById("sidebar-close");

    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", () => {
            sidebar.classList.add("active");
        });
    }

    if (sidebarClose && sidebar) {
        sidebarClose.addEventListener("click", () => {
            sidebar.classList.remove("active");
        });
    }

    // Auto-close sidebar on menu link clicks on mobile viewports
    document.querySelectorAll(".nav-item").forEach(button => {
        button.addEventListener("click", () => {
            if (sidebar && window.innerWidth <= 768) {
                sidebar.classList.remove("active");
            }
        });
    });
});
