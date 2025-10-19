function initTabSwitcher(configs) {
    function switchSubTab(parentTab, activeSubTab) {
        const config = configs[parentTab];
        if (!config) return;

        Object.values(config.buttons).forEach(btn => 
            btn.classList.remove('border-b-2', 'border-heliotrope', 'text-heliotrope'));
        config.buttons[activeSubTab].classList.add('border-b-2', 'border-heliotrope', 'text-heliotrope');

        Object.values(config.tabs).forEach(tab => tab.classList.add('hidden'));
        config.tabs[activeSubTab].classList.remove('hidden');
    }

    Object.entries(configs).forEach(([parentTab, config]) => {
        Object.entries(config.buttons).forEach(([subTabName, button]) => {
            if (button) {
                button.addEventListener('click', () => switchSubTab(parentTab, subTabName))
            }
        });
    });
}