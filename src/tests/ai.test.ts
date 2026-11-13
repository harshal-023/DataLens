import { describe, expect, it, vi } from 'vitest';
import { aiService } from '../services/aiService';

// Mock apiClient
vi.mock('../services/apiClient', () => ({
  apiClient: vi.fn(async (url: string, options?: any) => {
    if (url.includes('/api/v1/ai/providers')) {
      return {
        active_routing_mode: 'HYBRID',
        recommended_local_model: 'gemma3:4b',
        providers: [
          {
            name: 'gemini',
            configured: true,
            operational: true,
            model: 'gemini-3.5-flash',
            execution_mode: 'cloud_inference',
          },
          {
            name: 'ollama',
            configured: true,
            operational: false,
            model: 'gemma3:4b',
            base_url: 'http://localhost:11434',
            execution_mode: 'local_inference',
            error: 'Ollama endpoint standby',
          },
          {
            name: 'deterministic',
            configured: true,
            operational: true,
            model: 'heuristic-rules-v1',
            execution_mode: 'offline_rules',
          },
        ],
      };
    }

    if (url.includes('/api/v1/ai/ollama/models')) {
      return {
        is_online: false,
        base_url: 'http://localhost:11434',
        models: ['gemma3:4b', 'llama3.2:latest'],
      };
    }

    if (url.includes('/api/v1/ai/route') && options?.method === 'POST') {
      const body = JSON.parse(options.body);
      const isSensitive = body.dataset_sensitivity === 'RESTRICTED';
      return {
        selected_provider: isSensitive ? 'ollama' : 'gemini',
        reason: isSensitive
          ? 'Dataset sensitivity requires local processing'
          : 'Hybrid task routed to Gemini',
        routing_mode: 'HYBRID',
        cloud_permitted: !isSensitive,
        dataset_sensitivity: body.dataset_sensitivity,
      };
    }

    if (url.includes('/api/v1/ai/privacy-policy')) {
      return {
        id: 'policy-1',
        workspace_id: 'ws-123',
        routing_mode: 'HYBRID',
        cloud_ai_permitted: true,
        local_only_enforced: false,
        allow_sample_values: false,
        min_sensitivity_for_local_only: 'CONFIDENTIAL',
        default_local_model: 'gemma3:4b',
        default_cloud_model: 'gemini-3.5-flash',
      };
    }

    return { success: true };
  }),
}));

describe('Phase 6A Unified AI Architecture Client', () => {
  it('retrieves active AI providers and routing mode', async () => {
    const res = await aiService.getProviders();
    expect(res.active_routing_mode).toBe('HYBRID');
    expect(res.providers.length).toBe(3);
    const names = res.providers.map((p) => p.name);
    expect(names).toContain('gemini');
    expect(names).toContain('ollama');
    expect(names).toContain('deterministic');
  });

  it('queries local Ollama models list', async () => {
    const res = await aiService.getOllamaModels();
    expect(res.base_url).toBe('http://localhost:11434');
    expect(res.models).toContain('gemma3:4b');
  });

  it('tests privacy-preserving routing decision for sensitive data', async () => {
    const res = await aiService.testRoute({
      task_type: 'BUSINESS_REASONING',
      dataset_sensitivity: 'RESTRICTED',
      cloud_permitted: true,
    });
    // Restricted dataset must be routed locally, never to cloud
    expect(res.selected_provider).toBe('ollama');
    expect(res.cloud_permitted).toBe(false);
  });

  it('fetches workspace AI privacy policy', async () => {
    const policy = await aiService.getPrivacyPolicy('ws-123');
    expect(policy.routing_mode).toBe('HYBRID');
    expect(policy.min_sensitivity_for_local_only).toBe('CONFIDENTIAL');
    expect(policy.allow_sample_values).toBe(false);
  });
});

