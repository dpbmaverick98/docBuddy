import OpenAI from 'openai';

export class K2Client {
  private client: OpenAI;

  constructor(apiKey: string) {
    this.client = new OpenAI({
      baseURL: 'https://router.huggingface.co/v1',
      apiKey: apiKey,
    });
  }

  async generate(params: {
    messages: Array<{ role: string; content: string }>;
    max_tokens: number;
    temperature: number;
  }): Promise<string> {
    const completion = await this.client.chat.completions.create({
      model: 'moonshotai/Kimi-K2-Instruct:novita',
      messages: params.messages as any, // Type assertion for compatibility
      max_tokens: params.max_tokens,
      temperature: params.temperature,
    });

    return completion.choices[0]?.message?.content || '';
  }
}
