import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  MoreVertical,
  Trash2,
  Edit2,
  Pin,
  Bot,
} from 'lucide-react';
import { ConversationSession } from '../../../types';

interface ConversationSidebarProps {
  conversations: ConversationSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleRename = (id: string, currentTitle: string) => {
    const updated = window.prompt('Rename conversation:', currentTitle);
    if (updated && updated.trim()) {
      onRenameSession(id, updated.trim());
    }
    setOpenMenuId(null);
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      onDeleteSession(id);
    }
    setOpenMenuId(null);
  };

  return (
    <div className="bg-white rounded-2xl border border-[#DCE5EB] p-4 shadow-subtle h-full flex flex-col justify-between select-none">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#EEF3F6]">
          <h3 className="text-sm font-bold text-[#102C46]">Conversations</h3>
          <button
            onClick={onNewChat}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#009F98] text-[#009F98] hover:bg-[#E0F5F3] text-xs font-semibold transition-all cursor-pointer shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Search */}
        {conversations.length > 0 && (
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#52616C] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-[#DCE5EB] bg-[#F5F8FA] focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#009F98] text-[#102C46] placeholder:text-[#52616C]"
            />
          </div>
        )}

        {/* Conversation List */}
        <div className="space-y-1 overflow-y-auto max-h-[460px] pr-1">
          {conversations.length === 0 ? (
            /* Empty State matching reference image */
            <div className="py-12 px-2 text-center flex flex-col items-center justify-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-[#EDF7FA] border border-[#BBDCE8] flex items-center justify-center text-[#009F98] shadow-2xs mb-1">
                <Bot className="w-6 h-6 text-[#009F98]" />
              </div>
              <h4 className="text-xs font-bold text-[#102C46]">No conversations yet</h4>
              <p className="text-[11px] text-[#52616C] max-w-[190px] leading-relaxed">
                Start a new chat to explore your data.
              </p>
            </div>
          ) : filteredConversations.length === 0 ? (
            <div className="py-6 text-center text-xs text-[#52616C]">
              No conversations found.
            </div>
          ) : (
            filteredConversations.map((conv) => {
              const isActive = conv.id === activeSessionId;
              const isMenuOpen = openMenuId === conv.id;

              return (
                <div
                  key={conv.id}
                  className={`group relative p-2.5 rounded-xl transition-all cursor-pointer flex items-center justify-between ${
                    isActive
                      ? 'bg-[#EDF7FA] text-[#102C46] font-semibold border border-[#009F98]/40 shadow-2xs'
                      : 'hover:bg-[#F5F8FA] text-[#52616C] border border-transparent'
                  }`}
                  onClick={() => onSelectSession(conv.id)}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-1">
                    <MessageSquare
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? 'text-[#009F98]' : 'text-[#52616C] group-hover:text-[#102C46]'
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="text-xs truncate font-medium">{conv.title}</p>
                      <p className="text-[10px] text-[#52616C] mt-0.5">{conv.updatedAt}</p>
                    </div>
                  </div>

                  {/* Actions Dropdown */}
                  <div className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => setOpenMenuId(isMenuOpen ? null : conv.id)}
                      className={`p-1 rounded-md text-[#52616C] hover:text-[#102C46] hover:bg-[#DCE5EB]/50 transition-opacity ${
                        isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                      }`}
                      title="Options"
                    >
                      <MoreVertical className="w-3.5 h-3.5" />
                    </button>

                    {isMenuOpen && (
                      <div className="absolute right-0 top-6 w-32 bg-white rounded-xl shadow-elevated border border-[#DCE5EB] py-1 z-30 text-xs">
                        <button
                          onClick={() => handleRename(conv.id, conv.title)}
                          className="w-full px-3 py-1.5 flex items-center gap-2 text-left text-[#102C46] hover:bg-[#F5F8FA]"
                        >
                          <Edit2 className="w-3 h-3 text-[#52616C]" />
                          <span>Rename</span>
                        </button>
                        <button
                          onClick={() => {
                            alert('Conversation pinned to top');
                            setOpenMenuId(null);
                          }}
                          className="w-full px-3 py-1.5 flex items-center gap-2 text-left text-[#102C46] hover:bg-[#F5F8FA]"
                        >
                          <Pin className="w-3 h-3 text-[#52616C]" />
                          <span>Pin</span>
                        </button>
                        <button
                          onClick={() => handleDelete(conv.id)}
                          className="w-full px-3 py-1.5 flex items-center gap-2 text-left text-[#A63838] hover:bg-[#FCE9E9]"
                        >
                          <Trash2 className="w-3 h-3 text-[#A63838]" />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

