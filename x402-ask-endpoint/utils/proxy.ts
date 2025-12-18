import { Context } from 'hono';

export async function proxyToFastAPI(c: Context, fastAPIUrl: string): Promise<Response> {
  // Extract project from URL path
  const project = c.req.param('project');
  console.log('📂 Project from path:', project);

  // Validate project
  const allowedProjects = process.env.ALLOWED_PROJECTS!.split(',');
  if (!allowedProjects.includes(project)) {
    console.log('❌ Invalid project:', project);
    return new Response(JSON.stringify({ error: 'Invalid project' }), {
      status: 404, // Not found for invalid paths
      headers: { 'Content-Type': 'application/json' },
    });
  }

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

  // Set project from path (overrides any in body)
  body.project = project;

  // Lock model to k2
  body.model = 'hf-k2-openai';

  // Forward the request to FastAPI (normalize path to /api/docsbuddy/ask)
  const url = `${fastAPIUrl}/api/docsbuddy/ask`;
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