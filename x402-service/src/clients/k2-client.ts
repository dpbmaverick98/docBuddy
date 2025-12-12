import OpenAI from 'openai';

export class K2Client {
  private client: OpenAI;

  constructor(apiKey: string) {
    this.client = new OpenAI({
      base_url: 'https://router.huggingface.co/v1',
      api_key: apiKey,
    });
  }

  async generate(params: {
    messages: Array<{ role: string; content: string }>;
    max_tokens: number;
    temperature: number;
  }): Promise<string> {
    const completion = await this.client.chat.completions.create({
      model: 'moonshotai/Kimi-K2-Instruct:novita',
      messages: params.messages,
      max_tokens: params.max_tokens,
      temperature: params.temperature,
    });

    return completion.choices[0]?.message?.content || '';
  }
}</contents>
</xai:function_call name="write">
<parameter name="file_path">/Users/dpbmaverick98/docsBuddy/docBuddy/x402-service/src/clients/cohere-client.ts
