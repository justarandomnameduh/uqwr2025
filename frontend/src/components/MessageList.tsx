import React from 'react';
import { Bot, User, Loader2 } from 'lucide-react';
import type { Message } from '../types';
import { MarkdownText } from '../utils/markdown';
import { apiService } from '../services/api';

interface MessageListProps {
  messages: Message[];
  isGenerating: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  isGenerating, 
  messagesEndRef 
}) => {
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-gray-50">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full p-8">
          <div className="text-center max-w-md">
            <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">
              Welcome to VLM Chat
            </h3>
            <p className="text-gray-500">
              Start a conversation by typing a message or uploading images. 
              You can also upload audio files for transcription.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-6 space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-4 ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type === 'assistant' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                </div>
              )}
              
              <div
                className={`message-bubble ${
                  msg.type === 'user' ? 'message-user' : 'message-assistant'
                }`}
              >
                {/* Message Content */}
                <div className="mb-2">
                  {msg.type === 'assistant' ? (
                    <MarkdownText>{msg.content}</MarkdownText>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}
                </div>
                
                {/* Images */}
                {msg.images && msg.images.length > 0 && (
                  <div className="grid grid-cols-2 gap-2 mt-3">
                    {msg.images.map((imagePath, index) => (
                      <img
                        key={index}
                        src={apiService.getFileUrl(imagePath)}
                        alt={`Uploaded image ${index + 1}`}
                        className="rounded-lg max-w-full h-auto border border-gray-200"
                      />
                    ))}
                  </div>
                )}
                
                {/* Timestamp */}
                <div className={`text-xs mt-2 ${
                  msg.type === 'user' ? 'text-blue-200' : 'text-gray-400'
                }`}>
                  {formatTime(msg.timestamp)}
                </div>
              </div>
              
              {msg.type === 'user' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                  </div>
                </div>
              )}
            </div>
          ))}
          
          {/* Loading indicator for AI response */}
          {isGenerating && (
            <div className="flex gap-4 justify-start">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              </div>
              
              <div className="message-bubble message-assistant">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                  {/* <div className="typing-indicator">
                    <span className="text-gray-400">•</span>
                    <span className="text-gray-400">•</span>
                    <span className="text-gray-400">•</span>
                  </div> */}
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}; 