/** @odoo-module **/
/**
 * Inventory Request – Horizontal Scroll Overlay Buttons
 * Fixed: buttons are placed in a sticky wrapper OUTSIDE the scrollable
 * container so they never move when the table scrolls.
 */

import { registry } from "@web/core/registry";

const SCROLL_SPEED = 7;
const INJECTED_ATTR = "data-inv-scroll-injected";
const HIDDEN_CLASS = "o-inv-scroll-hidden";

// ─── Button factory ───────────────────────────────────────────────────────────
function createBtn(direction) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("aria-label", direction === "left" ? "Scroll left" : "Scroll right");
    btn.className = `o_inv_req_scroll_btn o_scroll_${direction}`;
    return btn;
}

// ─── Continuous scroll while hovering ────────────────────────────────────────
function attachScroll(btn, scroller, delta) {
    let rafId = null;
    const tick = () => { scroller.scrollLeft += delta; rafId = requestAnimationFrame(tick); };
    const start = () => { if (!rafId) rafId = requestAnimationFrame(tick); };
    const stop = () => { if (rafId) { cancelAnimationFrame(rafId); rafId = null; } };

    btn.addEventListener("mouseenter", start);
    btn.addEventListener("mouseleave", stop);
    btn.addEventListener("mousedown", start);
    btn.addEventListener("mouseup", stop);
    btn.addEventListener("touchstart", start, { passive: true });
    btn.addEventListener("touchend", stop);
    btn.addEventListener("touchcancel", stop);
    return stop;
}

// ─── Show/hide based on scroll position ──────────────────────────────────────
function syncVisibility(scroller, lBtn, rBtn) {
    const sl = Math.round(scroller.scrollLeft);
    const maxSl = scroller.scrollWidth - scroller.clientWidth;
    lBtn.classList.toggle(HIDDEN_CLASS, sl <= 2);
    rBtn.classList.toggle(HIDDEN_CLASS, sl >= maxSl - 2);
}

// ─── Core injection ──────────────────────────────────────────────────────────
function injectIntoList(listEl) {
    if (listEl.getAttribute(INJECTED_ATTR)) return; // already done
    listEl.setAttribute(INJECTED_ATTR, "1");

    // Find the scrollable child (Odoo 18 wraps the table in an overflow-x div)
    let scroller = null;
    for (const child of listEl.children) {
        const ov = window.getComputedStyle(child).overflowX;
        if (ov === "auto" || ov === "scroll") { scroller = child; break; }
    }
    if (!scroller) scroller = listEl; // fallback

    // ── KEY FIX: wrap listEl in a relative container, put buttons in the
    //    wrapper (NOT inside the scroller) so they don't move on scroll. ──────
    const wrapper = document.createElement("div");
    wrapper.className = "o-inv-scroll-wrapper";

    // Insert wrapper before listEl, then move listEl inside it
    listEl.parentNode.insertBefore(wrapper, listEl);
    wrapper.appendChild(listEl);

    const lBtn = createBtn("left");
    const rBtn = createBtn("right");
    wrapper.appendChild(lBtn);  // sibling of listEl, not inside scroller
    wrapper.appendChild(rBtn);

    const stopL = attachScroll(lBtn, scroller, -SCROLL_SPEED);
    const stopR = attachScroll(rBtn, scroller, +SCROLL_SPEED);

    // ── Measure header height and push buttons below it ──────────────────────
    const updateHeaderOffset = () => {
        const thead = scroller.querySelector("thead");
        const headerH = thead ? thead.getBoundingClientRect().height : 0;
        wrapper.style.setProperty("--inv-scroll-header-h", headerH + "px");
    };

    const onScroll = () => { syncVisibility(scroller, lBtn, rBtn); };
    scroller.addEventListener("scroll", onScroll, { passive: true });

    let ro;
    if (window.ResizeObserver) {
        ro = new ResizeObserver(() => { updateHeaderOffset(); syncVisibility(scroller, lBtn, rBtn); });
        ro.observe(scroller);
        const tbl = scroller.querySelector("table");
        if (tbl) ro.observe(tbl);
        const thead = scroller.querySelector("thead");
        if (thead) ro.observe(thead);
    }

    updateHeaderOffset();
    syncVisibility(scroller, lBtn, rBtn);

    return () => {
        stopL(); stopR();
        scroller.removeEventListener("scroll", onScroll);
        ro && ro.disconnect();
        // Unwrap: move listEl back, remove wrapper
        wrapper.parentNode.insertBefore(listEl, wrapper);
        wrapper.remove();
        listEl.removeAttribute(INJECTED_ATTR);
    };
}

// ─── Service ──────────────────────────────────────────────────────────────────
const inventoryScrollService = {
    dependencies: [],
    start() {
        let cleanups = [];
        let debounceTimer = null;

        const tryInject = () => {
            const formView = document.querySelector(
                ".o_action_manager .o_form_view, .o_view_controller.o_form_view"
            );
            if (!formView) return;

            const listRenderers = formView.querySelectorAll(".o_list_renderer:not([data-inv-scroll-injected])");
            if (!listRenderers.length) return;

            listRenderers.forEach(lr => {
                const cleanup = injectIntoList(lr);
                if (cleanup) cleanups.push(cleanup);
            });
        };

        const scheduleInject = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(tryInject, 350);
        };

        const mo = new MutationObserver(scheduleInject);
        mo.observe(document.body, { childList: true, subtree: true });

        setTimeout(tryInject, 600);
        return {};
    },
};

registry.category("services").add("inventory_request_scroll_btns", inventoryScrollService);
