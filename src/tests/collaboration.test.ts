import { describe, it, expect } from 'vitest';
import { CommentItem, NotificationItem } from '../services/collaborationService';

describe('Team Collaboration & Workspace Sharing Engine', () => {
  it('validates role hierarchy and permission capabilities', () => {
    const rolesOrder = ['viewer', 'editor', 'admin', 'owner'];
    const hasPermission = (userRole: string, requiredRole: string) => {
      const userIdx = rolesOrder.indexOf(userRole);
      const reqIdx = rolesOrder.indexOf(requiredRole);
      return userIdx >= reqIdx;
    };

    expect(hasPermission('owner', 'admin')).toBe(true);
    expect(hasPermission('admin', 'editor')).toBe(true);
    expect(hasPermission('editor', 'viewer')).toBe(true);
    expect(hasPermission('viewer', 'editor')).toBe(false);
    expect(hasPermission('editor', 'admin')).toBe(false);
  });

  it('constructs threaded comment replies correctly under parents', () => {
    const flatComments: CommentItem[] = [
      {
        id: 'c1',
        workspace_id: 'ws1',
        resource_type: 'dashboard',
        resource_id: 'd1',
        parent_id: null,
        author_id: 'u1',
        author_name: 'Alice',
        author_email: 'alice@test.com',
        content: 'Root comment 1',
        mentions: [],
        is_resolved: false,
        is_deleted: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        replies: [],
      },
      {
        id: 'c2',
        workspace_id: 'ws1',
        resource_type: 'dashboard',
        resource_id: 'd1',
        parent_id: 'c1',
        author_id: 'u2',
        author_name: 'Bob',
        author_email: 'bob@test.com',
        content: 'Reply to comment 1',
        mentions: [],
        is_resolved: false,
        is_deleted: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        replies: [],
      },
      {
        id: 'c3',
        workspace_id: 'ws1',
        resource_type: 'dashboard',
        resource_id: 'd1',
        parent_id: null,
        author_id: 'u3',
        author_name: 'Carol',
        author_email: 'carol@test.com',
        content: 'Root comment 2',
        mentions: [],
        is_resolved: false,
        is_deleted: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        replies: [],
      },
    ];

    const nestReplies = (items: CommentItem[]): CommentItem[] => {
      const map: Record<string, CommentItem> = {};
      const roots: CommentItem[] = [];

      items.forEach((item) => {
        map[item.id] = { ...item, replies: [] };
      });

      items.forEach((item) => {
        if (item.parent_id && map[item.parent_id]) {
          map[item.parent_id].replies.push(map[item.id]);
        } else {
          roots.push(map[item.id]);
        }
      });

      return roots;
    };

    const tree = nestReplies(flatComments);
    expect(tree).toHaveLength(2);
    expect(tree[0].id).toBe('c1');
    expect(tree[0].replies).toHaveLength(1);
    expect(tree[0].replies[0].id).toBe('c2');
    expect(tree[1].id).toBe('c3');
    expect(tree[1].replies).toHaveLength(0);
  });

  it('extracts unique @mentions from message content', () => {
    const extractMentions = (content: string): string[] => {
      const matches = content.match(/@([a-zA-Z0-9_.+-]+)/g);
      if (!matches) return [];
      return Array.from(new Set(matches.map((m) => m.substring(1).toLowerCase())));
    };

    const text = 'Hey @Alice and @bob, please review this chart! cc @alice again.';
    const mentions = extractMentions(text);
    expect(mentions).toEqual(['alice', 'bob']);
  });

  it('filters unread notifications and computes badge counts', () => {
    const notifications: NotificationItem[] = [
      {
        id: 'n1',
        workspace_id: 'ws1',
        recipient_id: 'u1',
        event_type: 'dashboard_shared',
        title: 'New Share',
        message: 'Shared a dashboard with you',
        data: {},
        is_read: false,
        created_at: new Date().toISOString(),
      },
      {
        id: 'n2',
        workspace_id: 'ws1',
        recipient_id: 'u1',
        event_type: 'comment_added',
        title: 'New Comment',
        message: 'Alice mentioned you in a comment',
        data: {},
        is_read: true,
        created_at: new Date().toISOString(),
      },
      {
        id: 'n3',
        workspace_id: 'ws1',
        recipient_id: 'u1',
        event_type: 'invitation_accepted',
        title: 'Member Joined',
        message: 'Bob accepted your invitation',
        data: {},
        is_read: false,
        created_at: new Date().toISOString(),
      },
    ];

    const unread = notifications.filter((n) => !n.is_read);
    expect(unread).toHaveLength(2);
    expect(unread.map((n) => n.id)).toEqual(['n1', 'n3']);
  });

  it('validates share link expiration timestamps', () => {
    const isExpired = (expiresAtStr: string | null | undefined): boolean => {
      if (!expiresAtStr) return false;
      return new Date(expiresAtStr).getTime() < Date.now();
    };

    const pastDate = new Date(Date.now() - 3600000).toISOString();
    const futureDate = new Date(Date.now() + 3600000 * 24).toISOString();

    expect(isExpired(pastDate)).toBe(true);
    expect(isExpired(futureDate)).toBe(false);
    expect(isExpired(null)).toBe(false);
  });
});

