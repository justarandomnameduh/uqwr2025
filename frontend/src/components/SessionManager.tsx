import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Calendar } from 'lucide-react';
import { apiService } from '../services/api';

interface Session {
  id: string;
  name: string;
  model_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface SessionManagerProps {
  currentModelId: string | null;
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionCreate: (sessionId: string) => void;
  isConnected: boolean;
}

export const SessionManager: React.FC<SessionManagerProps> = ({
  currentModelId,
  currentSessionId,
  onSessionSelect,
  onSessionCreate,
  isConnected
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Load sessions on mount and when connected
  useEffect(() => {
    if (isConnected) {
      loadSessions();
    }
  }, [isConnected]);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      const response = await apiService.listSessions();
      setSessions(response.sessions);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSession = async () => {
    if (!newSessionName.trim()) {
      setError('Session name is required');
      return;
    }

    if (!currentModelId) {
      setError('Please select a model first');
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiService.createSession({
        name: newSessionName.trim(),
        model_id: currentModelId
      });

      // Add new session to the list
      setSessions(prev => [response.session, ...prev]);
      
      // Select the new session
      onSessionCreate(response.session.id);
      
      // Close modal and reset form
      setShowCreateModal(false);
      setNewSessionName('');
      setError(null);
    } catch (err: any) {
      console.error('Failed to create session:', err);
      setError(err.message || 'Failed to create session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, sessionName: string) => {
    if (!confirm(`Are you sure you want to delete session "${sessionName}"?`)) {
      return;
    }

    try {
      setIsLoading(true);
      await apiService.deleteSession(sessionId);
      
      // Remove session from list
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      // If this was the current session, clear selection
      if (currentSessionId === sessionId) {
        onSessionSelect('');
      }
      
      setError(null);
    } catch (err: any) {
      console.error('Failed to delete session:', err);
      setError(err.message || 'Failed to delete session');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const canCreateSession = currentModelId && isConnected && !isLoading;

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Chat Sessions</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          disabled={!canCreateSession}
          className={`
            flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
            ${canCreateSession
              ? 'bg-blue-500 hover:bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          <Plus className="w-4 h-4" />
          New Session
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {!currentModelId && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
          Please select a model before creating a session.
        </div>
      )}

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {isLoading ? (
          <div className="text-center py-4 text-gray-500">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-4 text-gray-500">
            No sessions yet. Create your first session to start chatting!
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`
                flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-colors
                ${currentSessionId === session.id
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                }
              `}
              onClick={() => onSessionSelect(session.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <span className="font-medium text-gray-900 truncate">
                    {session.name}
                  </span>
                </div>
                <div className="text-xs text-gray-500 space-y-1">
                  <div>Model: {session.model_id}</div>
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(session.updated_at)}
                  </div>
                  <div>{session.message_count} messages</div>
                </div>
              </div>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(session.id, session.name);
                }}
                disabled={isLoading}
                className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete session"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Create Session Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-full max-w-md mx-4">
            <h4 className="text-lg font-semibold mb-4">Create New Session</h4>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Session Name *
              </label>
              <input
                type="text"
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                placeholder="Enter session name..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateSession();
                  }
                }}
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model
              </label>
              <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-600">
                {currentModelId || 'No model selected'}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCreateSession}
                disabled={!newSessionName.trim() || !currentModelId || isLoading}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating...' : 'Create Session'}
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewSessionName('');
                  setError(null);
                }}
                disabled={isLoading}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
