document.addEventListener('DOMContentLoaded', () => {
    const userQuestionInput = document.getElementById('user-question');
    const imageUploadInput = document.getElementById('image-upload');
    const imagePreviewBox = document.getElementById('image-preview-box');
    const imagePreviewContent = document.getElementById('image-preview-content');
    const removeImageBtn = document.getElementById('remove-image-btn');
    
    const submitQuestionBtn = document.getElementById('submit-question-btn');
    const regenerateAnswerBtn = document.getElementById('regenerate-answer-btn');
    const simplifyAnswerBtn = document.getElementById('simplify-answer-btn');
    
    const answerContentBox = document.getElementById('answer-content-box');
    const answerDisplayArea = document.getElementById('answer-display-area');
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorDisplay = document.getElementById('error-display');

    let currentSessionId = sessionStorage.getItem('bengaliChemSessionId');

    // Image Preview & Removal
    imageUploadInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreviewContent.src = e.target.result;
                imagePreviewBox.style.display = 'block';
            }
            reader.readAsDataURL(file);
        } else {
            imagePreviewContent.src = '#';
            imagePreviewBox.style.display = 'none';
        }
    });

    removeImageBtn.addEventListener('click', () => {
        imageUploadInput.value = ''; // Clear the file input
        imagePreviewContent.src = '#';
        imagePreviewBox.style.display = 'none';
    });

    function toggleLoading(isLoading) {
        loadingSpinner.style.display = isLoading ? 'flex' : 'none';
        submitQuestionBtn.disabled = isLoading;
        regenerateAnswerBtn.disabled = isLoading || !answerContentBox.innerHTML.trim();
        simplifyAnswerBtn.disabled = isLoading || !answerContentBox.innerHTML.trim();
        if (isLoading) {
            answerDisplayArea.style.display = 'none';
            errorDisplay.style.display = 'none';
        }
    }

    function displayErrorMessage(message) {
        errorDisplay.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        errorDisplay.style.display = 'block';
        answerDisplayArea.style.display = 'none';
    }
    
    function formatAnswerForDisplay(text) {
        let formattedText = text.replace(/\n/g, '<br>');
        formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // More robust list formatting
        formattedText = formattedText.replace(/^[\t ]*[\*\-][\t ]+(.*)/gm, '<li>$1</li>');
        const listRegex = /(<li>.*<\/li>)/s; 
        if (listRegex.test(formattedText)) {
            let tempFormattedText = formattedText;
            tempFormattedText = tempFormattedText.replace(/(<li>.*?<\/li>(?:<br>)*)+/g, (match) => `<ul>${match.replace(/<br>/g,'')}</ul>`);
            tempFormattedText = tempFormattedText.replace(/<\/ul>\s*<ul>/g, ''); // Clean up multiple wraps
            formattedText = tempFormattedText;
        }
        return formattedText;
    }

    async function handleRequest(actionType) {
        const questionText = userQuestionInput.value.trim();
        const imageFile = imageUploadInput.files[0];

        if (actionType === 'ask' && !questionText && !imageFile) {
            displayErrorMessage('অনুগ্রহ করে প্রশ্ন লিখুন অথবা ছবি আপলোড করুন।');
            return;
        }

        toggleLoading(true);

        const formData = new FormData();
        if (currentSessionId) {
            formData.append('session_id', currentSessionId);
        }
        if (questionText) {
            formData.append('question_text', questionText);
        }
        // Only append image if it's a new question and an image is selected
        if (imageFile && actionType === 'ask') {
            formData.append('image_file', imageFile);
        }
        formData.append('action', actionType);
        
        try {
            const response = await fetch('/ask_bengali_chem', { // Updated endpoint
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'একটি অজানা ত্রুটি ঘটেছে।' }));
                displayErrorMessage(`ত্রুটি ${response.status}: ${errorData.detail || 'Failed to get response.'}`);
                toggleLoading(false);
                return;
            }

            const data = await response.json();
            toggleLoading(false);

            if (data.session_id && data.session_id !== currentSessionId) {
                currentSessionId = data.session_id;
                sessionStorage.setItem('bengaliChemSessionId', currentSessionId);
            }

            answerContentBox.innerHTML = formatAnswerForDisplay(data.answer);
            answerDisplayArea.style.display = 'block';
            errorDisplay.style.display = 'none';

            regenerateAnswerBtn.disabled = false;
            simplifyAnswerBtn.disabled = false;
            
            // Optionally clear inputs for new 'ask' actions
            // if (actionType === 'ask') {
            //     userQuestionInput.value = '';
            //     imageUploadInput.value = '';
            //     imagePreviewContent.src = '#';
            //     imagePreviewBox.style.display = 'none';
            // }

        } catch (error) {
            toggleLoading(false);
            console.error('Fetch error:', error);
            displayErrorMessage('সার্ভারের সাথে সংযোগ করতে সমস্যা হচ্ছে। অনুগ্রহ করে আপনার ইন্টারনেট সংযোগ পরীক্ষা করুন।');
        }
    }

    submitQuestionBtn.addEventListener('click', () => handleRequest('ask'));
    regenerateAnswerBtn.addEventListener('click', () => handleRequest('regenerate'));
    simplifyAnswerBtn.addEventListener('click', () => handleRequest('simplify'));
    
    // Initial state for action buttons
    regenerateAnswerBtn.disabled = true;
    simplifyAnswerBtn.disabled = true;
}); 