document.addEventListener('DOMContentLoaded', function() {
    
    const PRICE_TICKET = 23;
    const PRICE_NO_TICKET = 27;
    
    const form = document.querySelector('form');
    const priceContainer = document.getElementById('price-container');
    const priceDisplay = document.getElementById('total-price');
    const discountBadge = document.getElementById('discount-badge');
    const detailsDisplay = document.getElementById('price-details');

    function calculateTotal() {
        
        let currentTotal = 0;
        let currentSelection = []; 
        let allEventIds = new Set(); 
        let participationCounts = {}; 

        // Hilfsfunktion
        function addParticipation(eventId, isNewSelection, price = 0, source = "unknown") {
            if (!eventId) {
                return;
            }
            
            allEventIds.add(eventId);
            participationCounts[eventId] = (participationCounts[eventId] || 0) + 1;

            if (isNewSelection) {
                currentTotal += price;
                currentSelection.push(price);
            } else {
            }
        }

        // 1. BEREITS GEBUCHTE (LOCKED) ITEMS
        const lockedItems = document.querySelectorAll('.touch-friendly-locked');
        
        lockedItems.forEach((el, index) => {
            // Wir prüfen explizit auf das Attribut
            const eId = el.getAttribute('data-event-id');
            if(!eId) {
            }
            addParticipation(eId, false, 0, "locked-item");
        });

        // 2. NEUE TICKETS
        const ticketInputs = document.querySelectorAll('input[name^="group_"]');
        ticketInputs.forEach(input => {
            const parts = input.name.split('_');
            const eId = parts.length > 1 ? parts[1] : null;
            
            // Event ID registrieren (auch wenn nicht gewählt)
            if(eId) allEventIds.add(eId); 

            if (input.checked) {
                addParticipation(eId, true, PRICE_TICKET, "ticket-checkbox");
            }
        });

        // 3. NEUE OHNE TICKET
        const noTicketInputs = document.querySelectorAll('input[name="no_ticket_events_dynamic"]');
        noTicketInputs.forEach(input => {
            const eId = input.value;
            if(eId) allEventIds.add(eId);

            if (input.checked) {
                addParticipation(eId, true, PRICE_NO_TICKET, "no-ticket-checkbox");
            }
        });

        // --- ZWISCHENSTAND LOGGEN ---
        
        // --- RABATT LOGIK ---
        let participatedInAll = true;
        let doubleParticipatedInAll = true;
        const totalEventsCount = allEventIds.size;

        if (totalEventsCount === 0) {
            participatedInAll = false;
            doubleParticipatedInAll = false;
        } else {
            for (let id of allEventIds) {
                const count = participationCounts[id] || 0;
                if (count < 1) {
                    participatedInAll = false;
                }
                if (count < 2) {
                    doubleParticipatedInAll = false;
                    // Nur loggen, wenn wir überhaupt Chance auf Doppelrabatt hätten
                    //
                }
            }
        }


        let discountAmount = 0;
        let discountText = "";

        currentSelection.sort((a, b) => a - b);

        if (currentSelection.length > 0) {
            if (doubleParticipatedInAll) {
                let itemsToDiscount = Math.min(currentSelection.length, 2);
                for(let i=0; i<itemsToDiscount; i++) {
                    discountAmount += currentSelection[i];
                }
                discountText = "Doppel-Bonus: 2 Plätze gratis!";

            } else if (participatedInAll) {
                discountAmount = currentSelection[0];
                discountText = "Serien-Bonus: 1x gratis!";
            } else {
            }
        }

        const finalPrice = currentTotal - discountAmount;

        // --- ANZEIGE UPDATEN ---
        if (currentSelection.length > 0) {
            priceContainer.style.display = 'block';
            priceDisplay.textContent = finalPrice;
            
            if (discountAmount > 0) {
                discountBadge.style.display = 'inline-block';
                discountBadge.textContent = discountText;
                const lockedCount = lockedItems.length;
                const lockedText = lockedCount > 0 ? ` (+${lockedCount} bereits gebucht)` : '';
                detailsDisplay.textContent = `Regulär: ${currentTotal} € - Rabatt: ${discountAmount} € ${lockedText}`;
            } else {
                discountBadge.style.display = 'none';
                detailsDisplay.textContent = `${currentSelection.length} Positionen gewählt`;
            }
        } else {
            priceContainer.style.display = 'none';
        }
    }

    let isDirty = false;
    let isSubmitting = false;

    // 1. Checkbox-Listener (Das ist die wichtigste Stelle!)
    const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');

    allCheckboxes.forEach(box => {
        box.addEventListener('change', function() {
            // HIER explizit auf dirty setzen!
            isDirty = true;

            setTimeout(calculateTotal, 10);
        });
    });

    // 2. Fallback: Label-Listener
    const allLabels = document.querySelectorAll('.form-check-label');
    allLabels.forEach(label => {
        label.addEventListener('click', function() {
            // Auch hier sicherheitshalber setzen
            isDirty = true;
            setTimeout(calculateTotal, 50);
        });
    });

    // Initialer Aufruf (setzt isDirty NICHT, da reiner Programmaufruf)
    calculateTotal();


    // === RESTLICHE LOGIK FÜR DAS VERLASSEN ===

    // 1. Wir suchen den Submit-Button (Crispy Forms nennt ihn meist 'submit')
    const submitBtn = document.querySelector('input[type="submit"]');

    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            isSubmitting = true;

            // (Optional) Debugging
        });
    }

    // 2. Fallback: Formular-Event (falls man Enter drückt)
    form.addEventListener('submit', function() {
        isSubmitting = true;
    });

    // Browser Warnung (Tab schließen / Zurück Button)
    window.addEventListener('beforeunload', function (e) {
        if (isDirty && !isSubmitting) {
            e.preventDefault();
            e.returnValue = ''; // Standard für moderne Browser
        }
    });

    // Button Warnung (Dein Abbrechen-Button)
    const cancelBtn = document.getElementById('btn-cancel');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function(e) {
            // Nur warnen, wenn wirklich was geändert wurde
            if (isDirty && !confirm("Ungespeicherte Änderungen verwerfen?")) {
                e.preventDefault();
            }
        });
    }

    setTimeout(calculateTotal, 500);
});