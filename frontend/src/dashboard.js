import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { useNavigate } from 'react-router-dom';
import { marked } from 'marked';
import './dashboard.css';

function Dashboard() {
    const { user, logout, getAuthHeaders } = useAuth();
    const navigate = useNavigate();
    
    const [messages, setMessages] = useState([]);
    const [currentMessage, setCurrentMessage] = useState('');
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [isTrayOpen, setIsTrayOpen] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isLoadingConversations, setIsLoadingConversations] = useState(true);
    const [showNewChatModal, setShowNewChatModal] = useState(false);
    const [newChatTitle, setNewChatTitle] = useState('');
    
    const messagesEndRef = useRef(null);
    const TYPING_SPEED = 20;

    // Load conversations from API
    const loadConversations = useCallback(async () => {
        try {
            const response = await fetch('http://localhost:8000/conversations', {
                headers: getAuthHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                setConversations(data.conversations);
            } else {
                console.error('Failed to load conversations');
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
        } finally {
            setIsLoadingConversations(false);
        }
    }, [getAuthHeaders]);

    // Load conversations on component mount
    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    // Load a specific conversation
    const loadConversation = async (conversationId) => {
        try {
            const response = await fetch(`http://localhost:8000/conversations/${conversationId}`, {
                headers: getAuthHeaders()
            });
            
            if (response.ok) {
                const conversation = await response.json();
                setCurrentConversationId(conversationId);
                
                // Convert database messages to UI format
                const uiMessages = conversation.messages.map(msg => ({
                    sender: msg.role === 'user' ? 'user' : 'ai',
                    text: msg.content,
                    timestamp: msg.timestamp
                }));
                
                setMessages(uiMessages);
                setIsTrayOpen(false);
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
        }
    };

    // Create new conversation
    const createNewConversation = async () => {
        if (!newChatTitle.trim()) return;
        
        try {
            const response = await fetch('http://localhost:8000/conversations', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ title: newChatTitle })
            });
            
            if (response.ok) {
                const data = await response.json();
                setNewChatTitle('');
                setShowNewChatModal(false);
                setMessages([]);
                setCurrentConversationId(data.conversation_id);
                await loadConversations(); // Refresh conversation list
            }
        } catch (error) {
            console.error('Error creating conversation:', error);
        }
    };

    // Delete conversation
    const deleteConversation = async (conversationId) => {
        if (!window.confirm('Are you sure you want to delete this conversation?')) return;
        
        try {
            const response = await fetch(`http://localhost:8000/conversations/${conversationId}`, {
                method: 'DELETE',
                headers: getAuthHeaders()
            });
            
            if (response.ok) {
                if (currentConversationId === conversationId) {
                    setCurrentConversationId(null);
                    setMessages([]);
                }
                await loadConversations();
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
        }
    };

    // Handle logout
    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    // Toggle tray
    const toggleTray = () => {
        setIsTrayOpen(prevState => !prevState);
    };

    // Scroll to bottom
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Handle input change
    const handleInputChange = (e) => {
        setCurrentMessage(e.target.value);
    };

    // Send message
    const handleSendMessage = async () => {
        if (isProcessing || currentMessage.trim() === '') return;
        
        setIsProcessing(true);

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

        try {
            // Send message to API
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    message: newUserMessage.text,
                    conversation_id: currentConversationId
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

            // Update current conversation ID if it's a new conversation
            if (!currentConversationId) {
                setCurrentConversationId(data.conversation_id);
                await loadConversations(); // Refresh conversation list
            }

            // Handle empty responses immediately
            if (fullAiResponse.length === 0) {
                setIsProcessing(false);
            }

        } catch (error) {
            console.error('Error:', error);
            // Remove typing indicator on error
            setMessages(prev => prev.filter(msg => !(msg.id === typingIndicatorId && msg.isTypingIndicator)));
            // Add error message
            setMessages(prev => [...prev, { 
                sender: 'ai', 
                text: 'Error: Could not get response. Please try again.' 
            }]);
            setIsProcessing(false);
        }
    };

    // Handle key press
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Animation effect for AI messages
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
                            setIsProcessing(false);
                        }
                        scrollToBottom();
                    }, TYPING_SPEED);
                    
                    return () => clearInterval(interval);
                } else {
                    setMessages(prevMessages => {
                        const newMessages = [...prevMessages];
                        newMessages[lastAiMessageIndex] = {
                            ...newMessages[lastAiMessageIndex],
                            isAnimating: false
                        };
                        return newMessages;
                    });
                    setIsProcessing(false);
                    scrollToBottom();
                }
            }
        }
    }, [messages]);

    // Format date for conversation list
    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) return 'Today';
        if (diffDays === 2) return 'Yesterday';
        if (diffDays <= 7) return `${diffDays - 1} days ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="chat-container">
            {/* Sidebar/Tray */}
            <div className={`tray-container ${isTrayOpen ? 'open' : ''}`}>
                <div className="tray-content">
                    <div className="tray-header">
                        <h2>Chat History</h2>
                        <button 
                            className="new-chat-btn"
                            onClick={() => setShowNewChatModal(true)}
                        >
                            + New Chat
                        </button>
                    </div>
                    
                    <div className="conversations-list">
                        {isLoadingConversations ? (
                            <div className="loading-conversations">Loading...</div>
                        ) : conversations.length === 0 ? (
                            <div className="no-conversations">
                                <p>No conversations yet</p>
                                <p>Start a new chat to begin!</p>
                            </div>
                        ) : (
                            conversations.map((conv) => (
                                <div 
                                    key={conv.id} 
                                    className={`conversation-item ${currentConversationId === conv.id ? 'active' : ''}`}
                                    onClick={() => loadConversation(conv.id)}
                                >
                                    <div className="conversation-info">
                                        <h4>{conv.title}</h4>
                                        <span className="conversation-date">{formatDate(conv.updated_at)}</span>
                                    </div>
                                    <button 
                                        className="delete-conversation-btn"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            deleteConversation(conv.id);
                                        }}
                                    >
                                        ×
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
            
            {/* Main Chat Area */}
            <div className="chat-main">
                {/* Header */}
                <div className="chat-header">
                    <img
                        src="tray.png" 
                        alt="Toggle Menu" 
                        className="tray-icon" 
                        onClick={toggleTray}
                        style={{ cursor: 'pointer' }}
                    />
                    <h1><span className="bouncing-text">🌸 Anime Recommender Chatbot 🌸</span></h1>
                    <div className="user-info">
                        <span>Welcome, {user?.username}!</span>
                        <button onClick={handleLogout} className="logout-btn">Logout</button>
                    </div>
                </div>

                {/* Messages */}
                <div className="chat-messages">
                    {messages.length === 0 ? (
                        <div className="welcome-message">
                            <h2>🎌 Welcome to Anime Recommender!</h2>
                            <p>I'm here to help you discover amazing anime. Tell me what you like!</p>
                            <div className="suggestions">
                                <button 
                                    onClick={() => setCurrentMessage("I'm looking for action anime with great animation")}
                                    className="suggestion-btn"
                                >
                                    Action anime with great animation
                                </button>
                                <button 
                                    onClick={() => setCurrentMessage("Recommend me some romance anime")}
                                    className="suggestion-btn"
                                >
                                    Romance anime recommendations
                                </button>
                                <button 
                                    onClick={() => setCurrentMessage("What are some must-watch classics?")}
                                    className="suggestion-btn"
                                >
                                    Must-watch classics
                                </button>
                            </div>
                        </div>
                    ) : (
                        messages.map((msg, index) => (
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
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
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

            {/* New Chat Modal */}
            {showNewChatModal && (
                <div className="modal-overlay" onClick={() => setShowNewChatModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h3>Create New Chat</h3>
                        <input
                            type="text"
                            placeholder="Enter chat title..."
                            value={newChatTitle}
                            onChange={(e) => setNewChatTitle(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && createNewConversation()}
                        />
                        <div className="modal-buttons">
                            <button onClick={() => setShowNewChatModal(false)}>Cancel</button>
                            <button onClick={createNewConversation}>Create</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Dashboard;