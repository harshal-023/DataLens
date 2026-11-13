/**
 * API client service for DataLens Phase 6A: Unified AI Architecture (Gemini + Local Ollama + Hybrid Routing)
 */

import { apiClient } from './apiClient';

export interface AIProviderInfo {
  name: string;
  configured: boolean;
  operational: boolean;
  model: string;
  base_url?: string | null;
  execution_mode: string;
  error?: string | null;
}

export interface AIProvidersListResponse {
  active_routing_mode: string;
  providers: AIProviderInfo[];
  recommended_local_model: string;
}

export interface AIOllamaModelsResponse {
  is_online: boolean;
  base_url: string;
  models: string[];
  error?: string | null;
}

export interface AIRouteDecision {
  selected_provider: string;
  reason: string;
  routing_mode: string;
  cloud_permitted: boolean;
  dataset_sensitivity: string;
}

export interface AIPrivacyPolicy {
  id: string;
  workspace_id: string;
  routing_mode: string;
  cloud_ai_permitted: boolean;
  local_only_enforced: boolean;
  allow_sample_values: boolean;
  min_sensitivity_for_local_only: string;
  default_local_model: string;
  default_cloud_model: string;
}

export const aiService = {
  // Provider health & listing
  async getProviders(): Promise<AIProvidersListResponse> {
    return apiClient<AIProvidersListResponse>('/api/v1/ai/providers');
  },

  // Ollama local model discovery
  async getOllamaModels(): Promise<AIOllamaModelsResponse> {
    return apiClient<AIOllamaModelsResponse>('/api/v1/ai/ollama/models');
  },

  // Test routing decision
  async testRoute(params: {
    task_type: string;
    dataset_sensitivity?: string;
    cloud_permitted?: boolean;
  }): Promise<AIRouteDecision> {
    return apiClient<AIRouteDecision>('/api/v1/ai/route', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  // Workspace AI Privacy Policy
  async getPrivacyPolicy(workspaceId: string): Promise<AIPrivacyPolicy> {
    return apiClient<AIPrivacyPolicy>(`/api/v1/ai/privacy-policy?workspace_id=${workspaceId}`);
  },

  async updatePrivacyPolicy(workspaceId: string, policy: Partial<AIPrivacyPolicy>): Promise<AIPrivacyPolicy> {
    return apiClient<AIPrivacyPolicy>(`/api/v1/ai/privacy-policy?workspace_id=${workspaceId}`, {
      method: 'PUT',
      body: JSON.stringify(policy),
    });
  },
};

