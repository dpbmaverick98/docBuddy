import { Context } from 'hono';

export async function proxyToFastAPI(c: Context, fastAPIUrl: string): Promise<Response> {
  // Buffer raw request body to avoid middleware consumption
  const rawBody = await c.req.text();
  console.log('🔄 Raw request body received:', rawBody);

  let body: any = {};
  try {
    body = JSON.parse(rawBody);
    console.log('📦 Parsed request body:', body);
  } catch (e) {
    console.log('❌ Failed to parse request body as JSON:', e.message);
    // Invalid JSON, use empty object
  }

  // Set default project if not provided
  if (!body.project) {
    body.project = 'polymarket';
  }

  // Validate project
  const allowedProjects = process.env.ALLOWED_PROJECTS!.split(',');
  if (!allowedProjects.includes(body.project)) {
    return new Response(JSON.stringify({ error: 'Invalid project' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Lock model to k2
  body.model = 'hf-k2-openai';

  // Forward the request to FastAPI
  const url = `${fastAPIUrl}${c.req.path}`;
  const requestBody = JSON.stringify(body);
  console.log('📤 Forwarding request to FastAPI:', { url, method: c.req.method, body: requestBody });

  const forwardedHeaders = {
    'Content-Type': 'application/json',
      // Forward other headers except payment ones and content-related
      ...Object.fromEntries(
        Array.from(c.req.raw.headers.entries()).filter(
          ([key]) => !key.startsWith('PAYMENT-') && key !== 'content-length' && key.toLowerCase() !== 'content-type'
        )
      ),
  };

  console.log('📤 Forwarded headers:', forwardedHeaders);

  const response = await fetch(url, {
    method: c.req.method,
    headers: forwardedHeaders,
    body: requestBody,
  });

  console.log('📥 FastAPI response status:', response.status);

  // Settlement handled by x402 middleware

  return response;
}