import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Reply,
  CheckCircle,
  RotateCcw,
  Edit2,
  Trash2,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { collaborationService, CommentItem } from '../../services/collaborationService';
import { useAuth } from '../../context/AuthContext';

interface CommentsPanelProps {
  workspaceId: string;
  resourceType: 'dashboard' | 'report';
  resourceId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const CommentsPanel: React.FC<CommentsPanelProps> = ({
  workspaceId,
  resourceType,
  resourceId,
  isOpen,
  onClose,
}) => {
  const { user } = useAuth();
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchComments = async () => {
    try {
      setLoading(true);
      const items = await collaborationService.listComments(
        workspaceId,
        resourceType,
        resourceId
      );
      setComments(items);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchComments();
    }
  }, [isOpen, workspaceId, resourceType, resourceId]);

  const handlePostComment = async () => {
    if (!newComment.trim()) return;
    try {
      await collaborationService.createComment({
        workspaceId,
        resourceType,
        resourceId,
        content: newComment.trim(),
      });
      setNewComment('');
      await fetchComments();
    } catch (e: any) {
      alert(e.message || 'Failed to post comment');
    }
  };

  const handlePostReply = async (parentId: string) => {
    if (!replyText.trim()) return;
    try {
      await collaborationService.createComment({
        workspaceId,
        resourceType,
        resourceId,
        content: replyText.trim(),
        parentId,
      });
      setReplyText('');
      setReplyTo(null);
      await fetchComments();
    } catch (e: any) {
      alert(e.message || 'Failed to post reply');
    }
  };

  const handleUpdate = async (commentId: string) => {
    if (!editText.trim()) return;
    try {
      await collaborationService.updateComment(commentId, editText.trim());
      setEditingId(null);
      setEditText('');
      await fetchComments();
    } catch (e: any) {
      alert(e.message || 'Failed to update comment');
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm('Are you sure you want to delete this comment?')) return;
    try {
      await collaborationService.deleteComment(commentId);
      await fetchComments();
    } catch (e: any) {
      alert(e.message || 'Failed to delete comment');
    }
  };

  const handleToggleResolve = async (comment: CommentItem) => {
    try {
      if (comment.is_resolved) {
        await collaborationService.reopenDiscussion(comment.id);
      } else {
        await collaborationService.resolveDiscussion(comment.id);
      }
      await fetchComments();
    } catch (e: any) {
      alert(e.message || 'Failed to update discussion status');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl z-50 flex flex-col border-l border-[#DCE5EB] animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#DCE5EB] bg-[#F8FAFC]">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-[#009F98]" />
          <h3 className="text-sm font-bold text-[#102C46]">Discussions & Comments</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-[#EDF7FA] text-[#009F98] font-bold">
            {comments.length}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-[#52616C] hover:text-[#102C46] hover:bg-[#EEF3F6]"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Comment List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading && comments.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#52616C]">Loading discussions...</div>
        ) : comments.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#52616C]">
            No discussions yet. Start a conversation below!
          </div>
        ) : (
          comments.map((comment) => (
            <div
              key={comment.id}
              className={`p-3 rounded-xl border transition-all ${
                comment.is_resolved
                  ? 'bg-[#F9FAFB] border-[#E5E7EB] opacity-75'
                  : 'bg-white border-[#DCE5EB] shadow-2xs'
              }`}
            >
              {/* Comment Header */}
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#009F98] text-white flex items-center justify-center text-[10px] font-bold">
                    {comment.author_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[#102C46]">
                      {comment.author_name}
                    </span>
                    <span className="text-[10px] text-[#8A9BA8] block">
                      {new Date(comment.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>

                {comment.is_resolved ? (
                  <span className="flex items-center gap-1 text-[10px] font-semibold text-[#16A34A] bg-[#DCFCE7] px-2 py-0.5 rounded-full">
                    <CheckCircle className="w-3 h-3" /> Resolved
                  </span>
                ) : (
                  <button
                    onClick={() => handleToggleResolve(comment)}
                    className="text-[10px] text-[#52616C] hover:text-[#009F98] flex items-center gap-1"
                    title="Mark thread resolved"
                  >
                    <CheckCircle className="w-3 h-3" /> Resolve
                  </button>
                )}
              </div>

              {/* Comment Content / Edit mode */}
              {editingId === comment.id ? (
                <div className="mt-2 space-y-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    rows={2}
                    className="w-full text-xs p-2 border border-[#009F98] rounded-lg focus:outline-none"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setEditingId(null)}
                      className="text-xs px-2 py-1 text-[#52616C] hover:bg-gray-100 rounded"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleUpdate(comment.id)}
                      className="text-xs px-3 py-1 bg-[#009F98] text-white rounded font-medium"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-[#2D3E4E] whitespace-pre-wrap mt-1 leading-relaxed">
                  {comment.content}
                </div>
              )}

              {/* Mentions badge */}
              {comment.mentions && comment.mentions.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {comment.mentions.map((m, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] bg-[#EDF7FA] text-[#009F98] px-1.5 py-0.5 rounded font-medium"
                    >
                      @{m}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-2 mt-2 border-t border-[#EEF3F6] text-[11px] text-[#52616C]">
                <button
                  onClick={() => {
                    setReplyTo(replyTo === comment.id ? null : comment.id);
                    setReplyText('');
                  }}
                  className="flex items-center gap-1 hover:text-[#009F98] font-medium"
                >
                  <Reply className="w-3 h-3" /> Reply
                </button>

                <div className="flex items-center gap-2">
                  {user?.id === comment.author_id && !comment.is_resolved && (
                    <button
                      onClick={() => {
                        setEditingId(comment.id);
                        setEditText(comment.content);
                      }}
                      className="hover:text-[#009F98]"
                      title="Edit"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                  )}
                  {user?.id === comment.author_id && (
                    <button
                      onClick={() => handleDelete(comment.id)}
                      className="hover:text-[#A63838]"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* Nested Replies */}
              {comment.replies && comment.replies.length > 0 && (
                <div className="mt-3 pl-3 border-l-2 border-[#DCE5EB] space-y-2">
                  {comment.replies.map((reply) => (
                    <div key={reply.id} className="bg-[#F8FAFC] p-2 rounded-lg text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-[#102C46]">
                          {reply.author_name}
                        </span>
                        <span className="text-[9px] text-[#8A9BA8]">
                          {new Date(reply.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                      <p className="text-[#2D3E4E]">{reply.content}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Reply Input Box */}
              {replyTo === comment.id && (
                <div className="mt-3 pt-2 border-t border-[#DCE5EB] space-y-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Write a reply... (use @name to mention)"
                    className="w-full text-xs p-2 border border-[#DCE5EB] rounded-lg focus:outline-none focus:border-[#009F98]"
                    onKeyDown={(e) => e.key === 'Enter' && handlePostReply(comment.id)}
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setReplyTo(null)}
                      className="text-xs px-2 py-1 text-[#52616C] hover:bg-gray-100 rounded"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handlePostReply(comment.id)}
                      className="text-xs px-3 py-1 bg-[#009F98] text-white rounded font-medium flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" /> Reply
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* New Root Comment Box */}
      <div className="p-3 border-t border-[#DCE5EB] bg-white">
        <div className="relative">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Add to discussion... (type @name to mention teammates)"
            rows={2}
            className="w-full text-xs p-2.5 border border-[#DCE5EB] rounded-xl focus:outline-none focus:border-[#009F98] resize-none pr-10"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handlePostComment();
              }
            }}
          />
          <button
            onClick={handlePostComment}
            disabled={!newComment.trim()}
            className="absolute right-2 bottom-3 p-1.5 bg-[#009F98] text-white rounded-lg hover:bg-[#008781] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

