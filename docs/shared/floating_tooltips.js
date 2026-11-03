// Position report tooltips inside the visible portion of an embedded page.
(() => {
    let active = null;
    let closeTimer;
    const selector = '.prob-wrapper, .sos-badge';
    function visibleBounds() {
        let top = 8, left = 8, right = innerWidth - 8, bottom = innerHeight - 8;
        try {
            let current = window, offsetX = 0, offsetY = 0;
            while (current !== current.parent) {
                const rect = current.frameElement.getBoundingClientRect();
                offsetX += rect.left;
                offsetY += rect.top;
                current = current.parent;
                top = Math.max(top, 8 - offsetY);
                left = Math.max(left, 8 - offsetX);
                right = Math.min(right, current.innerWidth - offsetX - 8);
                bottom = Math.min(bottom, current.innerHeight - offsetY - 8);
            }
        } catch (_) { /* Cross-origin embedding: clamp to this frame. */ }
        return {top, left, right, bottom};
    }
    function position() {
        if (!active) return;
        const {trigger, tip} = active;
        const bounds = visibleBounds();
        const anchor = trigger.getBoundingClientRect();
        tip.style.maxWidth = `${Math.max(0, Math.min(360, bounds.right - bounds.left))}px`;
        tip.style.maxHeight = `${Math.max(0, bounds.bottom - bounds.top)}px`;
        const box = tip.getBoundingClientRect();
        const above = anchor.top - box.height - 8;
        const below = anchor.bottom + 8;
        const top = above >= bounds.top ? above : below + box.height <= bounds.bottom ? below : bounds.top;
        tip.style.left = `${Math.max(bounds.left, Math.min(anchor.right - box.width, bounds.right - box.width))}px`;
        tip.style.top = `${Math.max(bounds.top, Math.min(top, bounds.bottom - box.height))}px`;
    }
    function close() {
        clearTimeout(closeTimer);
        if (!active) return;
        const {trigger, tip} = active;
        if (tip.hidePopover && tip.matches(':popover-open')) tip.hidePopover();
        tip.classList.remove('floating-report-tooltip');
        tip.removeAttribute('popover');
        trigger.append(tip);
        active = null;
    }
    function scheduleClose() { closeTimer = setTimeout(close, 120); }
    for (const trigger of document.querySelectorAll(selector)) {
        const tip = trigger.querySelector('.prob-tooltip, .sos-tooltip');
        if (!tip) continue;
        trigger.tabIndex = 0;
        tip.id = `report-tooltip-${document.querySelectorAll('[role="tooltip"]').length}`;
        tip.setAttribute('role', 'tooltip');
        trigger.setAttribute('aria-describedby', tip.id);
        function open() {
            clearTimeout(closeTimer);
            if (active?.trigger === trigger) return;
            close();
            active = {trigger, tip};
            tip.classList.add('floating-report-tooltip');
            document.body.append(tip);
            if (tip.showPopover) {
                tip.setAttribute('popover', 'manual');
                tip.showPopover();
            }
            position();
        }
        trigger.addEventListener('mouseenter', open);
        trigger.addEventListener('mouseleave', scheduleClose);
        trigger.addEventListener('focus', open);
        trigger.addEventListener('blur', scheduleClose);
        tip.addEventListener('mouseenter', () => clearTimeout(closeTimer));
        tip.addEventListener('mouseleave', scheduleClose);
    }
    const onKey = event => { if (event.key === 'Escape') close(); };
    addEventListener('keydown', onKey);
    addEventListener('scroll', event => {
        if (!active?.tip.contains(event.target)) close();
    }, true);
    addEventListener('resize', close);
    try {
        if (window.parent !== window) {
            window.parent.addEventListener('scroll', close, true);
            window.parent.addEventListener('keydown', onKey);
        }
    } catch (_) {}
})();
