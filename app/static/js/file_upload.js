// file_upload.js - Place in app/static/js/ directory
document.addEventListener('DOMContentLoaded', function() {
    // Replace file inputs with custom styled buttons
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(function(input) {
        // Skip if already processed
        if (input.parentElement.classList.contains('custom-file-wrapper')) return;
        
        // Create a wrapper for our custom control
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-file-wrapper';
        
        // Create the button that will look like our other action buttons
        const customButton = document.createElement('button');
        customButton.type = 'button';
        customButton.className = 'action-btn edit-btn custom-file-button';
        customButton.textContent = 'Choose File';
        
        // Create a span to show the selected filename
        const fileNameDisplay = document.createElement('span');
        fileNameDisplay.className = 'file-name-display';
        fileNameDisplay.textContent = 'No file selected';
        
        // Hide the original input but keep it functional
        input.style.display = 'none';
        
        // When our custom button is clicked, trigger the real file input
        customButton.addEventListener('click', function() {
            input.click();
        });
        
        // When a file is selected, update the display
        input.addEventListener('change', function() {
            if (input.files.length > 0) {
                fileNameDisplay.textContent = input.files[0].name;
            } else {
                fileNameDisplay.textContent = 'No file selected';
            }
        });
        
        // Insert the new elements
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(customButton);
        wrapper.appendChild(fileNameDisplay);
        wrapper.appendChild(input);
    });
});