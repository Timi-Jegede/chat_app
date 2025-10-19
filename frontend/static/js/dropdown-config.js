function initDropDownConfig(dropDownConfigs) {
    function toggleDropDown(dropDownType) {
        Object.entries(dropDownConfigs).forEach(([key, config]) => {
            const isActive = key === dropDownType;
            Object.values(config.type).forEach(elements => {
                if (elements.length !== undefined) {
                    elements.forEach(element => {
                        if (isActive) {
                            element.classList.toggle('hidden');
                        } else {
                            element.classList.add('hidden');
                        }
                    });
                } else {
                    if (isActive) {
                        elements.classList.toggle('hidden');
                    } else {
                        elements.classList.add('hidden');
                    }
                }
            });
        });
    }

    Object.entries(dropDownConfigs).forEach(([dropDown, config]) => {
        // console.log('Setting up dropdown:', dropDown, config);
        Object.values(config.button).forEach((buttons) => {
            if (buttons.length !== undefined) {
                // console.log('Multiple buttons found:', buttons.length);
                buttons.forEach(button => {
                    if (button) {
                        button.addEventListener('click', () => toggleDropDown(dropDown));
                    } else {
                        // console.warn('Button element is null for:', dropDown);
                    }
                });
            } else {
                // console.log('Single button found:', buttons);
                if (buttons) {
                    buttons.addEventListener('click', () => toggleDropDown(dropDown));
                } else {
                    // console.warn('Button element is null for:', dropDown);
                }
            }
        });
    });

    // Hide dropdowns when clicking outside
    document.addEventListener('click', (event) => {
        const isClickInsideDropdown = Object.values(dropDownConfigs).some(config => 
            Object.values(config.type).some(dropdown => dropdown && dropdown.contains(event.target)) ||
            Object.values(config.button).some(button => button && button.contains(event.target))
        );
        
        if (!isClickInsideDropdown) {
            Object.values(dropDownConfigs).forEach(config => {
                Object.values(config.type).forEach(dropdown => {
                    if (dropdown) {
                        dropdown.classList.add('hidden');
                    }
                });
            });
        }
    });
}




