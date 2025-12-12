import { CohereClient as CohereClientLib } from 'cohere-ai';

export class CohereClient {
  private client: CohereClientLib;

  constructor(apiKey: string) {
    this.client = new CohereClientLib({ token: apiKey });
  }

  async rerank(params: {
    query: string;
    documents: string[];
    top_n?: number;
    model?: string;
  }) {
    const response = await this.client.rerank({
      query: params.query,
      documents: params.documents,
      topN: params.top_n || 5,
      model: params.model as any || 'rerank-english-v3.0',
    });

    return response.results.map((r: any) => ({
      index: r.index,
      relevance_score: r.relevanceScore,
      document: { text: r.document?.text || '' },
    }));
  }

  async chat(params: {
    message: string;
    max_tokens?: number;
    temperature?: number;
  }): Promise<string> {
    const response = await this.client.chat({
      message: params.message,
      maxTokens: params.max_tokens || 100,
      temperature: params.temperature || 0.2,
    });

    return response.text;
  }

  async embed(params: {
    texts: string[];
    model?: string;
    input_type?: string;
  }): Promise<number[][]> {
    const response = await this.client.embed({
      texts: params.texts,
      model: params.model as any || 'embed-multilingual-v3.0',
      inputType: params.input_type as any || 'search_document',
    });

    // Handle different response types
    if (Array.isArray(response.embeddings)) {
      return response.embeddings;
    }
    // If it's an object with embeddings property, extract it
    return (response.embeddings as any).embeddings || [];
  }
}
