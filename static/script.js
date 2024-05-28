$(document).ready(function() {
    const sendBtn = $('#send-btn');
    const userInput = $('#user-input');
    const chatLog = $('#chat-log');
    const modal = $('#movieModal');
    const modalClose = $('.close');

    // Function to display user and bot messages
    function appendMessage(sender, message) {
        const messageElement = $('<div>').addClass(`${sender}-message`).html(message);
        chatLog.append(messageElement);
        chatLog.scrollTop(chatLog[0].scrollHeight);
    }

    // Function to handle sending user input
    function sendMessage() {
        const message = userInput.val().trim();
        if (message) {
            appendMessage('user', message);
            userInput.val('');
            $.ajax({
                type: "POST",
                url: "http://localhost:5000/get_recommendations",
                contentType: "application/json",
                data: JSON.stringify({ question: message }),
                success: function(response) {
                    displayResponse(response);
                },
                error: function(error) {
                    console.log("Error:", error);
                    alert("Something went wrong. Please try again.");
                }
            });
        } else {
            alert("Please enter a query.");
        }
    }

    // Function to display bot responses
    function displayResponse(response) {
        if (response.answer) {
            appendMessage('bot', response.answer);
        } else {
            appendMessage('bot', "No recommendations found. Try a different query.");
        }
    }

    // Send button click event
    sendBtn.click(function() {
        sendMessage();
    });

    // Handle Enter key press for sending messages
    userInput.keypress(function(e) {
        if (e.which === 13) {
            sendMessage();
        }
    });

    // Modal handling
    modalClose.click(function() {
        modal.hide();
    });

    $(window).click(function(event) {
        if ($(event.target).is(modal)) {
            modal.hide();
        }
    });
});
