import React, { useState, useEffect, useRef } from 'react';
import './dashboard.css';
import { marked } from 'marked';

function Dashboard() {
    const [messages, setMessages] = useState([]);
    const [currentMessage, setCurrentMessage] = useState('');
    const messagesEndRef = useRef(null);
    const [conversationId, setConversationId] = useState(null);
    const [isTrayOpen, setIsTrayOpen] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false); // Unified state for processing
    
    const TYPING_SPEED = 20; // Adjust animation speed here (ms per character)

    // Toggle tray function
    const toggleTray = () => {
        setIsTrayOpen(prevState => !prevState);
    };

    // Effect to scroll to bottom
    useEffect(() => {
        //scrollToBottom();
    }, [messages]);

    // Effect to generate conversation ID
    useEffect(() => {
        if (!conversationId) {
            setConversationId(Date.now().toString());
        }
    }, [conversationId]);

    useEffect(() => {
        const lastAiMessageIndex = messages.length - 1;
        if (lastAiMessageIndex >= 0) {
            const lastMessage = messages[lastAiMessageIndex];
            
            if (lastMessage.sender === 'ai' && lastMessage.isAnimating) {
                if (lastMessage.rawText !== undefined && 
                    lastMessage.text.length < lastMessage.rawText.length) {
                    
                    let i = lastMessage.text.length;
                    const interval = setInterval(() => {
                        if (i < lastMessage.rawText.length) {
                            setMessages(prevMessages => {
                                const newMessages = [...prevMessages];
                                newMessages[lastAiMessageIndex] = {
                                    ...newMessages[lastAiMessageIndex],
                                    text: lastMessage.rawText.substring(0, i + 1)
                                };
                                return newMessages;
                            });
                            i++;
                        } else {
                            clearInterval(interval);
                            setMessages(prevMessages => {
                                const newMessages = [...prevMessages];
                                newMessages[lastAiMessageIndex] = {
                                    ...newMessages[lastAiMessageIndex],
                                    isAnimating: false
                                };
                                return newMessages;
                            });
                            setIsProcessing(false); // Enable input after animation completes
                        }
                        //scrollToBottom();
                    }, TYPING_SPEED);
                    
                    return () => clearInterval(interval);
                } else {
                    // Handle cases where no animation is needed
                    setMessages(prevMessages => {
                        const newMessages = [...prevMessages];
                        newMessages[lastAiMessageIndex] = {
                            ...newMessages[lastAiMessageIndex],
                            isAnimating: false
                        };
                        return newMessages;
                    });
                    setIsProcessing(false); // Enable input immediately
                    scrollToBottom();
                }
            }
        }
    }, [messages]);

    // Scroll to bottom function
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Input change handler
    const handleInputChange = (e) => {
        setCurrentMessage(e.target.value);
    };

    // Send message handler
    const handleSendMessage = async () => {
        if (isProcessing || currentMessage.trim() === '') return;
        
        setIsProcessing(true); // Block input immediately

        // Add user message
        const newUserMessage = { sender: 'user', text: currentMessage.trim() };
        setMessages(prev => [...prev, newUserMessage]);
        setCurrentMessage('');

        // Add typing indicator
        const typingIndicatorId = Date.now();
        setMessages(prev => [
            ...prev,
            { sender: 'ai', text: '...', isTypingIndicator: true, id: typingIndicatorId }
        ]);
        //scrollToBottom();

        try {
            // Fetch AI response
            const response = await fetch(`http://localhost:8000/chat/`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: newUserMessage.text,
                    conversation_id: conversationId,
                }),
            });

            if (!response.ok) throw new Error('API request failed');
            
            const data = await response.json();
            const fullAiResponse = data.response;

            // Remove typing indicator
            setMessages(prev => prev.filter(msg => !(msg.id === typingIndicatorId && msg.isTypingIndicator)));

            // Add AI message with animation
            setMessages(prev => [...prev, { 
                sender: 'ai', 
                text: '', 
                rawText: fullAiResponse, 
                isAnimating: true 
            }]);

            try
            {
                const response = await fetch(`http://localhost:3000/users/${conversationId}`, {
                    method: 'GET',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(messages)
                });

                const data = await response

                if(response.ok)
                {
                    console.log(data)
                }

                else
                {
                    console.error('Error fetching history:', data.error)
                }
            }
            catch(error)
            {
                console.error('Error fetching history:', error);
            }

            // Handle empty responses immediately
            if (fullAiResponse.length === 0) {
                setIsProcessing(false);
            }

        } catch (error) 
        {
            console.error('Error:', error);
            // Remove typing indicator on error
            setMessages(prev => prev.filter(msg => !(msg.id === typingIndicatorId && msg.isTypingIndicator)));
            // Add error message
            setMessages(prev => [...prev, { 
                sender: 'ai', 
                text: 'Error: Could not get response. Please try again.' 
            }]);
            setIsProcessing(false); // Enable input after error
        }
    };

    // Key press handler
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <div className="chat-container">
            <div className={`tray-container ${isTrayOpen ? 'open' : ''}`}>
                <div className="tray-content">
                    <h1>History</h1>
                </div>
            </div>
            
            <div className="chat-header">
                <img
                    src="tray.png" 
                    alt="Toggle Menu" 
                    className="tray-icon" 
                    onClick={toggleTray}
                    style={{ cursor: 'pointer' }}
                />
                <h1>Anime Recommender Chatbot</h1>
            </div>

            <div className="chat-messages">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`message-wrapper ${msg.sender === 'user' ? 'user-message' : ''}`}
                    >
                        <div className={`message ${msg.sender}`}>
                            {msg.sender === 'ai' ? (
                                <div className="ai-message-content">
                                    {msg.isTypingIndicator ? (
                                        <div className="typing-indicator">
                                            <span>.</span><span>.</span><span>.</span>
                                        </div>
                                    ) : (
                                        <div dangerouslySetInnerHTML={{ __html: marked.parse(msg.text) }} />
                                    )}
                                </div>
                            ) : (
                                msg.text
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-container">
                <textarea 
                    className="chat-input"
                    placeholder={isProcessing ? 'Please wait...' : 'Type your message...'}
                    value={currentMessage}
                    onChange={handleInputChange}
                    onKeyPress={handleKeyPress}
                    rows="1"
                    disabled={isProcessing}
                ></textarea>
                <button
                    disabled={isProcessing}
                    onClick={handleSendMessage}
                    className="send-button"
                >
                    Send
                </button>
            </div>
        </div>
    );
}

export default Dashboard;