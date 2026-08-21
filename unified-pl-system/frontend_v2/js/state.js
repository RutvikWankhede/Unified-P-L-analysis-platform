/**
 * state.js - Centralized Global Filter Engine & State Management
 * 
 * Persists user state (URL Params + LocalStorage).
 * Changing any filter updates KPIs, Charts, Tables automatically.
 */

export const state = {
    filters: {
        date: 'May 13 - May 19, 2025',
        department: 'All Departments',
        region: 'Global Region',
        currency: 'INR (₹)',
        scenario: 'Actuals'
    },
    
    init() {
        this.loadFromURL();
        this.loadFromStorage();
        this.bindEvents();
        this.syncUI();
    },
    
    loadFromURL() {
        const params = new URLSearchParams(window.location.search);
        if (params.has('date')) this.filters.date = params.get('date');
        if (params.has('dept')) this.filters.department = params.get('dept');
        if (params.has('region')) this.filters.region = params.get('region');
        if (params.has('currency')) this.filters.currency = params.get('currency');
        if (params.has('scenario')) this.filters.scenario = params.get('scenario');
    },
    
    loadFromStorage() {
        const saved = localStorage.getItem('pl_global_filters');
        if (saved) {
            const parsed = JSON.parse(saved);
            this.filters = { ...this.filters, ...parsed };
        }
    },
    
    saveState() {
        // Save to URL
        const params = new URLSearchParams(window.location.search);
        params.set('date', this.filters.date);
        params.set('dept', this.filters.department);
        params.set('region', this.filters.region);
        params.set('currency', this.filters.currency);
        params.set('scenario', this.filters.scenario);
        window.history.replaceState({}, '', `${window.location.pathname}?${params}`);
        
        // Save to LocalStorage
        localStorage.setItem('pl_global_filters', JSON.stringify(this.filters));
        
        // Broadcast Event
        window.dispatchEvent(new CustomEvent('globalFiltersChanged', { detail: this.filters }));
    },
    
    updateFilter(key, value) {
        if (this.filters[key] !== value) {
            this.filters[key] = value;
            this.saveState();
            this.syncUI();
        }
    },
    
    bindEvents() {
        const filtersContainer = document.querySelector('[data-purpose="global-filters"]');
        if (!filtersContainer) return;
        
        //  dropdown clicks for now
        const filterPills = filtersContainer.querySelectorAll('.cursor-pointer');
        
        filterPills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                const text = pill.querySelector('span:nth-child(2)').textContent;
                
                if (text.includes('May')) {
                    const newDate = prompt("Enter Date Range (e.g. Jun 2025):", this.filters.date);
                    if (newDate) this.updateFilter('date', newDate);
                } else if (text.includes('Department')) {
                    const newDept = prompt("Enter Department (e.g. Finance, Sales):", this.filters.department);
                    if (newDept) this.updateFilter('department', newDept);
                } else if (text.includes('Region')) {
                    const newRegion = prompt("Enter Region:", this.filters.region);
                    if (newRegion) this.updateFilter('region', newRegion);
                } else if (text.includes('INR') || text.includes('USD')) {
                    const newCurr = prompt("Enter Currency (e.g. USD ($)):", this.filters.currency);
                    if (newCurr) this.updateFilter('currency', newCurr);
                } else if (text.includes('Scenario')) {
                    const newScenario = prompt("Enter Scenario (e.g. Forecast, Actuals):", this.filters.scenario);
                    if (newScenario) this.updateFilter('scenario', newScenario);
                }
            });
        });
        
        const resetBtn = filtersContainer.querySelector('button');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.filters = {
                    date: 'May 13 - May 19, 2025',
                    department: 'All Departments',
                    region: 'Global Region',
                    currency: 'INR (₹)',
                    scenario: 'Actuals'
                };
                this.saveState();
                this.syncUI();
            });
        }
    },
    
    syncUI() {
        const filtersContainer = document.querySelector('[data-purpose="global-filters"]');
        if (!filtersContainer) return;
        
        const filterPills = filtersContainer.querySelectorAll('.cursor-pointer');
        if (filterPills.length >= 5) {
            filterPills[0].querySelector('span:nth-child(2)').textContent = this.filters.date;
            filterPills[1].querySelector('span:nth-child(2)').textContent = this.filters.department;
            filterPills[2].querySelector('span:nth-child(2)').textContent = this.filters.region;
            filterPills[3].querySelector('span:nth-child(2)').textContent = this.filters.currency;
            filterPills[4].querySelector('span:nth-child(2)').textContent = `Scenario: ${this.filters.scenario}`;
        }
    }
};

window.addEventListener('DOMContentLoaded', () => {
    state.init();
});
