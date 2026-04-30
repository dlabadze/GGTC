/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        
        console.log("🔍 ListRenderer setup called");
        console.log("Model:", this.props.list?.resModel);
        console.log("Context:", this.props.list?.context);
        
        // Check if this is an inventory.line list
        const isInventoryLine = this.props.list?.resModel === 'inventory.line';
        
        if (isInventoryLine) {
            console.log("✅ This is inventory.line - setting up arrows!");
            this.scrollAmount = 300;
            
            // Use onMounted hook
            this.onMounted(() => {
                console.log("🎯 onMounted called for inventory.line");
                setTimeout(() => {
                    console.log("⏰ setTimeout fired, calling setupScrollArrows");
                    this.setupScrollArrows();
                }, 200);
            });
            
            this.onWillUnmount(() => {
                this.cleanupScrollArrows();
            });
        } else {
            console.log("⏭️ Not inventory.line, skipping");
        }
    },

    setupScrollArrows() {
        console.log("🚀 setupScrollArrows called!");
        
        // Try multiple selectors to find the scrollable container
        let tableContainer = null;
        
        if (this.rootRef?.el) {
            console.log("Root element found:", this.rootRef.el);
            
            // Try different selectors
            tableContainer = this.rootRef.el.querySelector('.o_list_table_wrapper') ||
                           this.rootRef.el.querySelector('.o_list_view') ||
                           this.rootRef.el.closest('.o_list_renderer') ||
                           this.rootRef.el;
            
            console.log("Table container:", tableContainer);
        } else {
            console.log("❌ No rootRef.el found!");
            return;
        }
        
        if (!tableContainer) {
            console.log('❌ Table container not found');
            return;
        }

        // Check if already has arrows
        if (document.querySelector('.inventory-scroll-arrow')) {
            console.log('⚠️ Arrows already exist');
            return;
        }

        console.log('✅ Creating scroll arrows...');

        // Create left arrow
        const leftArrow = document.createElement('div');
        leftArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-left visible';
        leftArrow.innerHTML = '<i class="fa fa-chevron-left"></i>';
        leftArrow.style.cssText = `
            position: fixed;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        leftArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('⬅️ Left arrow clicked');
            tableContainer.scrollBy({ left: -300, behavior: 'smooth' });
        });
        
        // Create right arrow
        const rightArrow = document.createElement('div');
        rightArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-right visible';
        rightArrow.innerHTML = '<i class="fa fa-chevron-right"></i>';
        rightArrow.style.cssText = `
            position: fixed;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        rightArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('➡️ Right arrow clicked');
            tableContainer.scrollBy({ left: 300, behavior: 'smooth' });
        });

        // Append to body for visibility
        document.body.appendChild(leftArrow);
        document.body.appendChild(rightArrow);

        // Store references
        this.leftArrow = leftArrow;
        this.rightArrow = rightArrow;
        this.tableContainer = tableContainer;
        
        console.log('🎉 Arrows added to DOM!');
    },

    cleanupScrollArrows() {
        console.log("🧹 Cleaning up arrows");
        if (this.leftArrow) this.leftArrow.remove();
        if (this.rightArrow) this.rightArrow.remove();
    }
});

console.log("📦 Inventory Line Scroll Arrows module loaded");