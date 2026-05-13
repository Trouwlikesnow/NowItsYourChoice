export interface Env {
  FEISHU_APP_ID: string;
  FEISHU_APP_SECRET: string;
  FEISHU_VERIFICATION_TOKEN: string;
  FEISHU_BASE_APP_TOKEN: string;
  TABLE_ID_TRADES: string;
  LLM_API_BASE: string;
  LLM_API_KEY: string;
  LLM_MODEL: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    try {
      const body = await request.json() as Record<string, unknown>;

      // Feishu challenge verification
      if (body.challenge) {
        return Response.json({ challenge: body.challenge });
      }

      // TODO: implement in next tasks
      return new Response("OK", { status: 200 });
    } catch (e) {
      console.error("Worker error:", e);
      return new Response("OK", { status: 200 });
    }
  },
};
