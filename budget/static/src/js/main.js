// Budget Visual Report JavaScript
(function() {
    'use strict';
    
    let budgetPieChart = null;
    let comparisonBarChart = null;
    let currentReportData = null;
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeBudgetReport();
    });
    
    function initializeBudgetReport() {
        // Wait for Chart.js to load
        if (typeof Chart === 'undefined') {
            setTimeout(initializeBudgetReport, 100);
            return;
        }
        
        const elements = {
            purchasePlanSelect: document.getElementById('purchase_plan_select'),
            budgetCpvSelect: document.getElementById('budget_cpv_select'),
            generateButton: document.getElementById('generate_report'),
            exportButton: document.getElementById('export_report'),
            resultsSection: document.getElementById('results_section'),
            loadingDiv: document.getElementById('loading')
        };
        
        // Check if elements exist
        if (!elements.purchasePlanSelect) {
            console.error('Budget report elements not found');
            return;
        }
        
        bindEvents(elements);
    }
    
    function bindEvents(elements) {
        // Purchase plan selection
        elements.purchasePlanSelect.addEventListener('change', function() {
            handlePurchasePlanChange(elements);
        });
        
        // Budget CPV selection
        elements.budgetCpvSelect.addEventListener('change', function() {
            handleBudgetCpvChange(elements);
        });
        
        // Generate report
        elements.generateButton.addEventListener('click', function() {
            generateReport(elements);
        });
        
        // Export report
        elements.exportButton.addEventListener('click', function() {
            exportReport(elements);
        });
    }
    
    function handlePurchasePlanChange(elements) {
        const planId = elements.purchasePlanSelect.value;
        elements.budgetCpvSelect.innerHTML = '<option value="">იტვირთება...</option>';
        elements.budgetCpvSelect.disabled = true;
        elements.generateButton.disabled = true;
        elements.resultsSection.classList.add('hidden');
        
        if (planId) {
            loadBudgetCpvs(planId, elements);
        } else {
            elements.budgetCpvSelect.innerHTML = '<option value="">ჯერ აირჩიეთ შესყიდვების გეგმა...</option>';
        }
    }
    
    function loadBudgetCpvs(planId, elements) {
        makeRequest('/budget/get_budget_cpvs', {
            purchase_plan_id: planId
        })
        .then(function(data) {
            elements.budgetCpvSelect.innerHTML = '<option value="">აირჩიეთ ბიუჯეტ CPV...</option>';
            
            if (data && data.length > 0) {
                data.forEach(function(cpv) {
                    const option = document.createElement('option');
                    option.value = cpv.id;
                    option.textContent = cpv.code + ' - ' + cpv.name;
                    elements.budgetCpvSelect.appendChild(option);
                });
                elements.budgetCpvSelect.disabled = false;
            } else {
                elements.budgetCpvSelect.innerHTML = '<option value="">CPV არ მოიძებნა...</option>';
            }
        })
        .catch(function(error) {
            console.error('Error loading CPVs:', error);
            elements.budgetCpvSelect.innerHTML = '<option value="">შეცდომა CPV-ების ჩატვირთვისას</option>';
        });
    }
    
    function handleBudgetCpvChange(elements) {
        const hasValue = !!elements.budgetCpvSelect.value;
        elements.generateButton.disabled = !hasValue;
        elements.exportButton.disabled = !hasValue || !currentReportData;
        elements.resultsSection.classList.add('hidden');
    }
    
    function generateReport(elements) {
        const planId = elements.purchasePlanSelect.value;
        const cpvId = elements.budgetCpvSelect.value;
        
        if (!planId || !cpvId) {
            showAlert('გთხოვთ, აირჩიოთ შესყიდვების გეგმა და ბიუჯეტ CPV');
            return;
        }
        
        elements.loadingDiv.classList.remove('hidden');
        elements.resultsSection.classList.add('hidden');
        
        loadChartData(planId, cpvId, elements);
    }
    
    function loadChartData(planId, cpvId, elements) {
        makeRequest('/budget/get_chart_data', {
            purchase_plan_id: planId,
            budget_cpv_id: cpvId
        })
        .then(function(data) {
            elements.loadingDiv.classList.add('hidden');
            
            if (data && Object.keys(data).length > 0) {
                currentReportData = data;
                renderCharts(data);
                renderSummaryCards(data.summary);
                renderDataTable(planId, cpvId);
                elements.resultsSection.classList.remove('hidden');
                elements.exportButton.disabled = false;
            } else {
                showAlert('მონაცემები ვერ მოიძებნა არჩეული პარამეტრებისთვის');
                currentReportData = null;
                elements.exportButton.disabled = true;
            }
        })
        .catch(function(error) {
            console.error('Error loading chart data:', error);
            elements.loadingDiv.classList.add('hidden');
            showAlert('შეცდომა მონაცემების ჩატვირთვისას');
        });
    }
    
    function renderCharts(chartData) {
        // Destroy existing charts
        if (budgetPieChart) {
            budgetPieChart.destroy();
        }
        if (comparisonBarChart) {
            comparisonBarChart.destroy();
        }
        
        // Create pie chart
        const pieCtx = document.getElementById('budget_pie_chart');
        if (pieCtx) {
            budgetPieChart = new Chart(pieCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: chartData.budget_amounts.labels,
                    datasets: [{
                        data: chartData.budget_amounts.data,
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                        ],
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    size: 12,
                                    weight: '500'
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: 'rgba(255,255,255,0.2)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return context.label + ': ' + value.toLocaleString() + ' (' + percentage + '%)';
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Create bar chart
        const barCtx = document.getElementById('comparison_bar_chart');
        if (barCtx) {
            comparisonBarChart = new Chart(barCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: chartData.amounts_comparison.labels,
                    datasets: [
                        {
                            label: 'ბიუჯეტის თანხა',
                            data: chartData.amounts_comparison.budget_amounts,
                            backgroundColor: 'rgba(54, 162, 235, 0.8)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        },
                        {
                            label: 'გამოყენებული თანხა',
                            data: chartData.amounts_comparison.amounts,
                            backgroundColor: 'rgba(255, 99, 132, 0.8)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        },
                        {
                            label: 'დარჩენილი რესურსი',
                            data: chartData.amounts_comparison.pu_re_am,
                            backgroundColor: 'rgba(75, 192, 192, 0.8)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    size: 12,
                                    weight: '500'
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: 'rgba(255,255,255,0.2)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        }
    }
    
    function renderSummaryCards(summary) {
        const container = document.getElementById('summary_cards');
        if (!container) return;
        
        const cards = [
            {
                icon: 'fas fa-wallet',
                title: 'ბიუჯეტის საერთო თანხა',
                value: summary.total_budget_amount,
                color: '#667eea'
            },
            {
                icon: 'fas fa-credit-card',
                title: 'გამოყენებული თანხა',
                value: summary.total_amount,
                color: '#764ba2'
            },
            {
                icon: 'fas fa-piggy-bank',
                title: 'დარჩენილი რესურსი',
                value: summary.total_pu_re_am,
                color: '#56ab2f'
            },
            {
                icon: 'fas fa-list-ol',
                title: 'ხაზების რაოდენობა',
                value: summary.lines_count,
                color: '#f093fb'
            }
        ];
        
        container.innerHTML = cards.map(function(card) {
            return '<div class="summary-card" style="background: linear-gradient(135deg, ' + card.color + ', ' + card.color + '66);">' +
                '<i class="' + card.icon + '"></i>' +
                '<h3>' + card.title + '</h3>' +
                '<div class="value">' + (typeof card.value === 'number' ? card.value.toLocaleString() : card.value) + '</div>' +
            '</div>';
        }).join('');
    }
    
    function renderDataTable(planId, cpvId) {
        makeRequest('/budget/get_cpv_lines_data', {
            purchase_plan_id: planId,
            budget_cpv_id: cpvId
        })
        .then(function(data) {
            const tableBody = document.querySelector('#data_table tbody');
            if (!tableBody) return;
            
            if (data && data.length > 0) {
                tableBody.innerHTML = data.map(function(line) {
                    return '<tr>' +
                        '<td>' + (line.selected_plan_name || 'N/A') + '</td>' +
                        '<td>' + ((line.budget_amount || 0).toLocaleString()) + '</td>' +
                        '<td>' + ((line.amount || 0).toLocaleString()) + '</td>' +
                        '<td>' + ((line.pu_re_am || 0).toLocaleString()) + '</td>' +
                        '<td>' + (line.cpv_code || 'N/A') + '</td>' +
                        '<td>' + (line.budget_line_name || 'N/A') + '</td>' +
                    '</tr>';
                }).join('');
            } else {
                tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px;">მონაცემები არ მოიძებნა</td></tr>';
            }
        })
        .catch(function(error) {
            console.error('Error loading table data:', error);
        });
    }
    
    function exportReport(elements) {
        if (!currentReportData) {
            showAlert('ჯერ გენერირეთ ანგარიში');
            return;
        }
        
        const planId = elements.purchasePlanSelect.value;
        const cpvId = elements.budgetCpvSelect.value;
        
        makeRequest('/budget/get_cpv_lines_data', {
            purchase_plan_id: planId,
            budget_cpv_id: cpvId
        })
        .then(function(data) {
            if (data && data.length > 0) {
                const csvContent = generateCSVContent(data);
                downloadCSV(csvContent, 'budget_report_' + new Date().toISOString().split('T')[0] + '.csv');
            } else {
                showAlert('ექსპორტისთვის მონაცემები არ მოიძებნა');
            }
        })
        .catch(function(error) {
            console.error('Error exporting data:', error);
            showAlert('შეცდომა ექსპორტისას');
        });
    }
    
    function generateCSVContent(data) {
        const headers = [
            'გეგმის დასახელება',
            'ბიუჯეტის თანხა', 
            'გამოყენებული თანხა',
            'დარჩენილი რესურსი',
            'CPV კოდი',
            'ბიუჯეტის ხაზი'
        ];
        
        const csvRows = [headers.join(',')];
        
        data.forEach(function(line) {
            const row = [
                '"' + (line.selected_plan_name || 'N/A') + '"',
                line.budget_amount || 0,
                line.amount || 0,
                line.pu_re_am || 0,
                '"' + (line.cpv_code || 'N/A') + '"',
                '"' + (line.budget_line_name || 'N/A') + '"'
            ];
            csvRows.push(row.join(','));
        });
        
        return csvRows.join('\n');
    }
    
    function downloadCSV(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    }
    
    function makeRequest(url, params) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Date.now()
            })
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(function(data) {
            if (data.error) {
                throw new Error(data.error.message || 'Server error');
            }
            return data.result;
        });
    }
    
    function showAlert(message) {
        // Create a beautiful custom alert
        const alertDiv = document.createElement('div');
        alertDiv.style.cssText = [
            'position: fixed',
            'top: 50%',
            'left: 50%',
            'transform: translate(-50%, -50%)',
            'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'color: white',
            'padding: 30px 40px',
            'border-radius: 15px',
            'box-shadow: 0 10px 40px rgba(0,0,0,0.3)',
            'z-index: 10000',
            'text-align: center',
            'font-size: 1.1rem',
            'font-weight: 500',
            'max-width: 400px',
            'backdrop-filter: blur(10px)'
        ].join(';');
        
        const iconHtml = '<i class="fas fa-info-circle" style="font-size: 2rem; margin-bottom: 15px; display: block;"></i>';
        const messageHtml = message;
        const buttonHtml = [
            '<div style="margin-top: 20px;">',
            '<button onclick="this.parentElement.parentElement.remove()" ',
            'style="background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.3); ',
            'color: white; padding: 10px 20px; border-radius: 8px; cursor: pointer; ',
            'font-weight: 500; transition: all 0.3s ease;">',
            'გასაგებია</button></div>'
        ].join('');
        
        alertDiv.innerHTML = iconHtml + messageHtml + buttonHtml;
        
        document.body.appendChild(alertDiv);
        
        // Auto remove after 5 seconds
        setTimeout(function() {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    // Global error handler
    window.addEventListener('error', function(e) {
        console.error('JavaScript error:', e.error);
    });
    
    // Export functions to global scope for debugging if needed
    window.BudgetReportDebug = {
        currentReportData: function() { return currentReportData; },
        budgetPieChart: function() { return budgetPieChart; },
        comparisonBarChart: function() { return comparisonBarChart; }
    };
    
})();