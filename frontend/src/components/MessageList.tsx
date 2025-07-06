import React from 'react';
import { Message } from '../types';
import { apiService } from '../services/api';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
  apiService: typeof apiService;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  isGenerating, 
  apiService,
  messagesEndRef 
}) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="messages-container">
      {messages.length === 0 ? (
        <div className="welcome-screen">
          <div className="welcome-content">
            {/* <div className="welcome-icon">🤖</div> */}
            <p className="welcome-text">
              Start a conversation by typing a message or uploading images. 
            </p>
          </div>
        </div>
      ) : (
        <div>
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.type === 'user' ? 'message-user' : 'message-assistant'}`}>
              <div className="message-content">
                <div className={`message-avatar ${msg.type === 'user' ? 'message-avatar-user' : 'message-avatar-assistant'}`}>
                  {msg.type === 'user' ? 'U' : 'A'}
                </div>
                <div>
                  <div className={`message-bubble ${msg.type === 'user' ? 'message-bubble-user' : 'message-bubble-assistant'}`}>
                    {msg.images && msg.images.length > 0 && (
                      <div style={{ marginBottom: '0.75rem', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                        {msg.images.map((imagePath, index) => (
                          <div key={index} style={{ position: 'relative' }}>
                            <img
                              src={apiService.getFileUrl(imagePath)}
                              alt={`Attachment ${index + 1}`}
                              style={{ width: '100%', height: '6rem', objectFit: 'cover', borderRadius: '0.25rem', border: '1px solid #e5e7eb' }}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="message-text">{msg.content}</div>
                  </div>
                  <div className="message-timestamp">
                    {formatTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isGenerating && (
            <div className="message message-assistant">
              <div className="message-content">
                <div className="message-avatar message-avatar-assistant">🤖</div>
                <div className="message-bubble message-bubble-assistant">
                  <div className="typing-indicator">
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                    <div className="typing-dot"></div>
                  </div>
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>AI is thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList; 