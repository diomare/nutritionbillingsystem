document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Handle client type selection in the invoice form
    const clientTypeRadios = document.querySelectorAll('input[name="client_type"]');
    if (clientTypeRadios.length > 0) {
        clientTypeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                toggleClientSelection(this.value);
            });
        });
        
        // Initialize the view based on the current selection
        const selectedClientType = document.querySelector('input[name="client_type"]:checked')?.value || 'private';
        toggleClientSelection(selectedClientType);
    }
    
    // Initialize the invoice items section if on invoice page
    const invoiceItemsContainer = document.getElementById('invoice-items-container');
    if (invoiceItemsContainer) {
        if (invoiceItemsContainer.children.length === 0) {
            addInvoiceItem();
        }
        
        // Add event listener to the "Add Item" button
        const addItemButton = document.getElementById('add-item-button');
        if (addItemButton) {
            addItemButton.addEventListener('click', addInvoiceItem);
        }
    }
    
    // Initialize any DataTables
    if (typeof $.fn.DataTable !== 'undefined') {
        $('.data-table').DataTable({
            "language": {
                "lengthMenu": "Mostra _MENU_ record per pagina",
                "zeroRecords": "Nessun risultato trovato",
                "info": "Pagina _PAGE_ di _PAGES_",
                "infoEmpty": "Nessun record disponibile",
                "infoFiltered": "(filtrato da _MAX_ record totali)",
                "search": "Cerca:",
                "paginate": {
                    "first": "Primo",
                    "last": "Ultimo",
                    "next": "Successivo",
                    "previous": "Precedente"
                }
            },
            "responsive": true
        });
    }
    
    // Initialize date picker elements
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            // Set default value to today for empty date inputs
            const today = new Date().toISOString().split('T')[0];
            input.value = today;
        }
    });
    
    // Set up dynamic calculation for invoice totals
    setupInvoiceCalculations();
});

/**
 * Toggle the display of client selection based on client type
 */
function toggleClientSelection(clientType) {
    const privateClientSection = document.getElementById('private-client-section');
    const businessClientSection = document.getElementById('business-client-section');
    
    if (privateClientSection && businessClientSection) {
        if (clientType === 'private') {
            privateClientSection.style.display = 'block';
            businessClientSection.style.display = 'none';
        } else {
            privateClientSection.style.display = 'none';
            businessClientSection.style.display = 'block';
        }
    }
}

/**
 * Add a new invoice item row to the form
 */
function addInvoiceItem() {
    const container = document.getElementById('invoice-items-container');
    const itemIndex = container.children.length;
    
    const itemRow = document.createElement('div');
    itemRow.className = 'row invoice-item mb-3';
    itemRow.dataset.itemIndex = itemIndex;
    
    itemRow.innerHTML = `
        <div class="col-md-5">
            <input type="text" class="form-control" name="item_description[]" placeholder="Descrizione" required>
        </div>
        <div class="col-md-1">
            <input type="number" class="form-control item-quantity" name="item_quantity[]" value="1" min="1" required>
        </div>
        <div class="col-md-2">
            <div class="input-group">
                <span class="input-group-text">€</span>
                <input type="number" class="form-control item-price" name="item_unit_price[]" step="0.01" min="0" value="0.00" required>
            </div>
        </div>
        <div class="col-md-1">
            <div class="input-group">
                <input type="number" class="form-control item-vat" name="item_vat_rate[]" value="22" min="0" max="100" required>
                <span class="input-group-text">%</span>
            </div>
        </div>
        <div class="col-md-2">
            <div class="input-group">
                <span class="input-group-text">€</span>
                <input type="text" class="form-control item-total" value="0.00" readonly>
            </div>
        </div>
        <div class="col-md-1">
            <button type="button" class="btn btn-danger remove-item" onclick="removeInvoiceItem(this)">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        <div class="col-md-12 mt-1">
            <input type="text" class="form-control" name="item_exemption_reason[]" placeholder="Motivo esenzione IVA (opzionale)">
        </div>
    `;
    
    container.appendChild(itemRow);
    
    // Add event listeners to new inputs
    const newRow = container.lastElementChild;
    
    const quantityInput = newRow.querySelector('.item-quantity');
    const priceInput = newRow.querySelector('.item-price');
    const vatInput = newRow.querySelector('.item-vat');
    
    quantityInput.addEventListener('input', updateInvoiceTotals);
    priceInput.addEventListener('input', updateInvoiceTotals);
    vatInput.addEventListener('input', updateInvoiceTotals);
    
    updateInvoiceTotals();
}

/**
 * Remove an invoice item row from the form
 */
function removeInvoiceItem(button) {
    const container = document.getElementById('invoice-items-container');
    
    if (container.children.length > 1) {
        const row = button.closest('.invoice-item');
        row.remove();
        updateInvoiceTotals();
    } else {
        alert("È necessario almeno un elemento nella fattura.");
    }
}

/**
 * Set up event listeners for invoice calculations
 */
function setupInvoiceCalculations() {
    // Add event listeners to existing item inputs
    document.querySelectorAll('.item-quantity, .item-price, .item-vat').forEach(input => {
        input.addEventListener('input', updateInvoiceTotals);
    });
    
    // Initial calculation
    updateInvoiceTotals();
}

/**
 * Update all totals in the invoice form
 */
function updateInvoiceTotals() {
    let subtotal = 0;
    let totalVat = 0;
    
    // Calculate total for each item
    document.querySelectorAll('.invoice-item').forEach(item => {
        const quantity = parseFloat(item.querySelector('.item-quantity').value) || 0;
        const price = parseFloat(item.querySelector('.item-price').value) || 0;
        const vatRate = parseFloat(item.querySelector('.item-vat').value) || 0;
        
        const itemTotal = quantity * price;
        const itemVat = itemTotal * (vatRate / 100);
        
        item.querySelector('.item-total').value = itemTotal.toFixed(2);
        
        subtotal += itemTotal;
        totalVat += itemVat;
    });
    
    const total = subtotal + totalVat;
    
    // Update summary values if they exist
    const subtotalElement = document.getElementById('invoice-subtotal');
    const vatElement = document.getElementById('invoice-vat');
    const totalElement = document.getElementById('invoice-total');
    
    if (subtotalElement) subtotalElement.textContent = subtotal.toFixed(2);
    if (vatElement) vatElement.textContent = totalVat.toFixed(2);
    if (totalElement) totalElement.textContent = total.toFixed(2);
}
