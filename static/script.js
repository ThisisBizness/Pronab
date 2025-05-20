document.addEventListener('DOMContentLoaded', () => {
    const userQuestionInput = document.getElementById('user-question');
    const submitButton = document.getElementById('submit-button');
    const regenerateButton = document.getElementById('regenerate-button');
    const simplifyButton = document.getElementById('simplify-button');
    const answerBox = document.getElementById('answer-box');
    const answerSection = document.getElementById('answer-section');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessageDiv = document.getElementById('error-message');

    let currentSessionId = sessionStorage.getItem('chemistryAppSessionId');
    let lastQuestion = ''; // To store the most recent question for regenerate/simplify

    function showLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.style.display = 'flex';
            submitButton.disabled = true;
            regenerateButton.disabled = true;
            simplifyButton.disabled = true;
            answerSection.style.display = 'none'; // Hide answer section while loading new
            errorMessageDiv.style.display = 'none';
        } else {
            loadingIndicator.style.display = 'none';
            submitButton.disabled = false;
            // Enable action buttons only if there's an answer
            if (answerBox.innerHTML.trim() !== "") {
                regenerateButton.disabled = false;
                simplifyButton.disabled = false;
            }
        }
    }

    function displayError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        answerSection.style.display = 'none';
    }

    function formatAnswer(text) {
        // Basic formatting: replace newlines with <br>
        // More sophisticated formatting (like markdown parsing) could be added here
        let formattedText = text.replace(/\n/g, '<br>');

        // Make bold text actually bold (handles **text**)
        formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Handle bullet points (simple * or - list items)
        formattedText = formattedText.replace(/^\s*[\*\-]\s+(.*)/gm, '<li>$1</li>');
        const listRegex = /(<li>.*<\/li>)/s; // Find if there are any list items
        if (listRegex.test(formattedText)) {
            formattedText = formattedText.replace(listRegex, '<ul>$1</ul>');
        }
        // Ensure <ul> only wraps actual list items by cleaning up potential multiple wraps
        formattedText = formattedText.replace(/<\/ul>\s*<ul>/g, '');


        return formattedText;
    }


    async function handleSubmit(actionType, questionText) {
        const question = questionText || userQuestionInput.value.trim();

        if (actionType === 'ask' && !question) {
            displayError('অনুগ্রহ করে একটি প্রশ্ন লিখুন। (Please enter a question.)');
            return;
        }

        showLoading(true);
        if (actionType === 'ask') {
            lastQuestion = question; // Store the new question
        }

        let requestBody = {
            session_id: currentSessionId,
            question: actionType === 'ask' ? question : (actionType === 'regenerate' ? 'regenerate_previous' : 'simplify_previous'), // Use stored question for follow-ups
            action: actionType
        };
        
        // For regenerate and simplify, ensure lastQuestion is used from client-side context if needed
        // The backend logic also tries to use its last_question/last_answer context
        if (actionType === 'regenerate' || actionType === 'simplify') {
             if (!lastQuestion && actionType === 'regenerate') {
                displayError('পুনরায় তৈরি করার জন্য কোনও পূর্ববর্তী প্রশ্ন নেই। (No previous question to regenerate.)');
                showLoading(false);
                return;
            }
             if (!answerBox.innerHTML.trim() && actionType === 'simplify') {
                displayError('সহজ করার জন্য কোনও পূর্ববর্তী উত্তর নেই। (No previous answer to simplify.)');
                showLoading(false);
                return;
            }
        }


        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            showLoading(false);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'একটি অজানা ত্রুটি ঘটেছে। (An unknown error occurred.)' }));
                displayError(`ত্রুটি ${response.status}: ${errorData.detail}`);
                return;
            }

            const data = await response.json();

            if (data.session_id && data.session_id !== currentSessionId) {
                currentSessionId = data.session_id;
                sessionStorage.setItem('chemistryAppSessionId', currentSessionId);
            }

            answerBox.innerHTML = formatAnswer(data.answer);
            answerSection.style.display = 'block';
            errorMessageDiv.style.display = 'none'; // Clear previous errors

            // Enable action buttons after getting an answer
            regenerateButton.disabled = false;
            simplifyButton.disabled = false;

            if (actionType === 'ask') {
                userQuestionInput.value = ''; // Clear input only for new questions
            }

        } catch (error) {
            showLoading(false);
            console.error('Fetch error:', error);
            displayError('সার্ভারের সাথে সংযোগ করতে সমস্যা হচ্ছে। (Problem connecting to the server.)');
        }
    }

    submitButton.addEventListener('click', () => handleSubmit('ask', userQuestionInput.value.trim()));
    regenerateButton.addEventListener('click', () => handleSubmit('regenerate', lastQuestion));
    simplifyButton.addEventListener('click', () => handleSubmit('simplify', lastQuestion)); // Or pass answer context if API supports

    userQuestionInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit('ask', userQuestionInput.value.trim());
        }
    });
    
    // Initially disable action buttons until an answer is displayed
    regenerateButton.disabled = true;
    simplifyButton.disabled = true;
}); 